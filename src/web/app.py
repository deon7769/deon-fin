from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import threading
import time as _time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from ..agent import AnalystError, Categorizer, FinancialAnalyst, build_financial_context
from ..agent.buckets import apply_buckets_to_database
from ..agent.budget import summarize_5030, summarize_executivo, summarize_wishlist
from ..agent.context import income_value, spending_value
from ..agent.simulator import simular_amortizacao, simular_compra
from ..agent.cards import card_monthly_breakdown
from ..agent import maintenance as mnt
from ..config import settings
from ..importers import sync_pluggy_item
from ..pluggy import PluggyAPIError, PluggyClient
from ..storage import Database
from .dependencies import get_db, get_pluggy
from .errors import error_response, install_error_handlers
from .repositories import profile_repo, transactions_repo
from .routers import buckets, budget, painel, profile, tags, transactions

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))
log = logging.getLogger(__name__)
DEFAULT_DASHBOARD_MONTHS = 12
DEFAULT_SYNC_DAYS = 365


# ---------------------------------------------------------------- pydantic
class ConnectTokenRequest(BaseModel):
    client_user_id: str | None = None
    item_id: str | None = None  # se passado, gera token de update


class ItemCallbackRequest(BaseModel):
    item_id: str
    connector_id: int | None = None
    connector_name: str | None = None
    status: str | None = None
    client_user_id: str | None = None


class SyncRequest(BaseModel):
    days: int = DEFAULT_SYNC_DAYS


class AnalyzeRequest(BaseModel):
    kind: str = "all"  # all | budget | waste | goals


class MaintenanceRequest(BaseModel):
    family_profile: dict[str, Any] | None = None
    overrides: dict[str, Any] | None = None


class SimularRequest(BaseModel):
    preco: float
    entrada: float = 0.0
    prazo_meses: int = 48
    juros_aa: float = 18.0
    sobra_mensal: float = 0.0
    rendimento_aa: float = 0.0
    taxa_adm_consorcio: float = 18.0


class AmortizacaoRequest(BaseModel):
    saldo: float
    juros_aa: float
    parcela: float
    aporte_extra: float = 0.0


def _months_cutoff(today: date, months: int) -> date:
    idx = (today.year * 12 + (today.month - 1)) - (months - 1)
    cy, cm = divmod(idx, 12)
    return date(cy, cm + 1, 1)


def _normalized_days(days: int | None) -> int:
    if not days or days <= 0:
        return DEFAULT_SYNC_DAYS
    return min(days, 5 * 365)


def _metadata(row: Any) -> dict[str, Any]:
    raw = row["metadata_json"] if "metadata_json" in row.keys() else None
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


_ACCOUNT_TYPE_LABELS = {
    "BANK": "Conta",
    "CHECKING": "Conta",
    "CHECKING_ACCOUNT": "Conta",
    "SAVINGS": "Poupança",
    "SAVINGS_ACCOUNT": "Poupança",
    "CREDIT": "Cartão",
    "CREDIT_CARD": "Cartão",
}

_BANK_CODE_NAMES = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "077": "Banco Inter",
    "104": "Caixa",
    "208": "BTG Pactual",
    "237": "Bradesco",
    "260": "Nubank",
    "323": "Mercado Pago",
    "341": "Itaú",
}

_GENERIC_ACCOUNT_NAMES = {
    "conta",
    "conta corrente",
    "conta poupança",
    "poupança",
    "checking account",
    "savings account",
}


def _bank_code_from_account(row: Any, meta: dict[str, Any]) -> str | None:
    transfer = (meta.get("bankData") or {}).get("transferNumber") or row["institution"] or ""
    digits = "".join(ch for ch in str(transfer).split("/", 1)[0] if ch.isdigit())
    if len(digits) >= 3:
        return digits[:3]
    return None


def _bank_name_from_account(row: Any, meta: dict[str, Any]) -> str | None:
    code = _bank_code_from_account(row, meta)
    return _BANK_CODE_NAMES.get(code or "")


def _is_generic_account_name(value: str | None) -> bool:
    if not value:
        return True
    normalized = " ".join(value.lower().strip().split())
    return normalized in _GENERIC_ACCOUNT_NAMES


def _is_probably_person_name(value: str | None) -> bool:
    if not value:
        return False
    cleaned = str(value).strip()
    if any(ch.isdigit() for ch in cleaned):
        return False
    words = cleaned.split()
    return len(words) >= 2 and cleaned.upper() == cleaned


def _display_brand(value: str | None) -> str | None:
    if not value:
        return None
    return str(value).replace("_", " ").strip().title()


def _account_type_label(row: Any, meta: dict[str, Any]) -> str:
    raw = (row["type"] or meta.get("subtype") or "").upper()
    return _ACCOUNT_TYPE_LABELS.get(raw, "Conta")


def _account_label(row: Any, meta: dict[str, Any], item_bank_name: str | None = None) -> str:
    type_label = _account_type_label(row, meta)
    bank_name = _bank_name_from_account(row, meta) or item_bank_name
    raw_name = meta.get("marketingName") or row["name"] or row["institution"]
    label = raw_name or row["id"].replace("pluggy:", "")

    if type_label in {"Conta", "Poupança"} and bank_name and _is_generic_account_name(raw_name):
        label = f"{bank_name} - {raw_name or type_label}"
    elif type_label == "Cartão" and bank_name and (
        _is_probably_person_name(raw_name) or _is_generic_account_name(raw_name)
    ):
        brand = _display_brand((meta.get("creditData") or {}).get("brand"))
        number = meta.get("number")
        parts = [bank_name]
        if brand:
            parts.append(brand)
        if number:
            parts.append(f"final {number}")
        label = " ".join(parts)

    return f"{type_label}: {label}"


def _accounts_by_pluggy_item(db: Database) -> dict[str, list[tuple[Any, dict[str, Any]]]]:
    grouped: dict[str, list[tuple[Any, dict[str, Any]]]] = {}
    for account in db.list_accounts():
        if account["source"] != "pluggy":
            continue
        meta = _metadata(account)
        item_id = meta.get("itemId")
        if not item_id:
            continue
        grouped.setdefault(item_id, []).append((account, meta))
    return grouped


def _item_display_name(
    item: dict[str, Any],
    accounts: list[tuple[Any, dict[str, Any]]],
) -> str:
    bank = next(
        (
            account for account, meta in accounts
            if _account_type_label(account, meta) in {"Conta", "Poupança"}
        ),
        None,
    )
    first = bank or (accounts[0][0] if accounts else None)
    if bank:
        bank_meta = next(meta for account, meta in accounts if account["id"] == bank["id"])
        bank_name = _bank_name_from_account(bank, bank_meta)
        if bank_name and _is_generic_account_name(bank["name"]):
            return bank_name
    return (
        (first["name"] if first else None)
        or (first["institution"] if first else None)
        or item.get("connector_name")
        or item["id"][:8]
    )


# ---------------------------------------------------------------- background
def _fill_missing_reference_months(db: Database) -> int:
    profile = profile_repo.get_profile(db)
    start_day = int(profile["financial_month_start_day"] or 1)
    return transactions_repo.fill_missing_reference_months(db, start_day)


def _background_sync(item_id: str, days: int) -> None:
    """Roda em thread pool do FastAPI (BackgroundTasks) — não bloqueia request."""
    db = Database(settings.database_path)
    pc = PluggyClient(settings.client_id, settings.client_secret)
    try:
        since = date.today() - timedelta(days=days)
        sync_pluggy_item(pc, db, item_id, since=since)
        Categorizer().apply_to_database(db)
        apply_buckets_to_database(db)
        _fill_missing_reference_months(db)
        db.upsert_pluggy_item(item_id, mark_synced=True)
    finally:
        pc.close()
        db.close()


# ---------------------------------------------------------------- auto-sync
# Estado compartilhado da rotina de sincronização automática do Pluggy.
_sync_state: dict[str, Any] = {
    "running": False,
    "last_started": None,
    "last_finished": None,
    "last_result": None,   # ex.: "3 itens sincronizados" ou erro
    "scheduler_on": False,
}
_sync_lock = threading.Lock()


def _sync_all_items(days: int) -> str:
    """Sincroniza TODOS os itens Pluggy conhecidos. Retorna um resumo."""
    with _sync_lock:
        if _sync_state["running"]:
            return "já em andamento"
        _sync_state["running"] = True
        _sync_state["last_started"] = datetime.now().isoformat(timespec="seconds")
    ok = err = 0
    errors: list[str] = []
    db = Database(settings.database_path)
    pc = PluggyClient(settings.client_id, settings.client_secret)
    try:
        since = date.today() - timedelta(days=days)
        items = list(db.list_pluggy_items())
        for it in items:
            try:
                sync_pluggy_item(pc, db, it["id"], since=since)
                db.upsert_pluggy_item(it["id"], mark_synced=True)
                ok += 1
            except Exception as e:
                err += 1
                msg = f"{it['id'][:8]}…: {e}"
                errors.append(msg)
                log.exception("sync falhou para item %s", it["id"])
        Categorizer().apply_to_database(db)
        apply_buckets_to_database(db)
        _fill_missing_reference_months(db)
        result = f"{ok} conta(s) sincronizada(s)" + (f", {err} com erro" if err else "")
        if errors:
            result += " — " + "; ".join(errors[:3])
            if len(errors) > 3:
                result += f" (+{len(errors) - 3})"
    except Exception as e:
        result = f"falha: {e}"
    finally:
        pc.close()
        db.close()
        with _sync_lock:
            _sync_state["running"] = False
            _sync_state["last_finished"] = datetime.now().isoformat(timespec="seconds")
            _sync_state["last_result"] = result
    return result


def _start_auto_sync() -> None:
    """Sync na inicialização + agendador periódico (thread daemon). Idempotente."""
    with _sync_lock:
        if _sync_state["scheduler_on"]:
            return
        _sync_state["scheduler_on"] = True

    def loop() -> None:
        if settings.auto_sync_on_start:
            _sync_all_items(settings.auto_sync_days)
        interval = settings.auto_sync_minutes * 60
        while interval > 0:
            _time.sleep(interval)
            _sync_all_items(settings.auto_sync_days)

    threading.Thread(target=loop, name="pluggy-auto-sync", daemon=True).start()


# ---------------------------------------------------------------- factory
def create_app() -> FastAPI:
    app = FastAPI(title="Financas — Pluggy Connect MVP", version="0.1.0")
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
    app.include_router(buckets.router)
    app.include_router(budget.router)
    app.include_router(painel.router)
    app.include_router(tags.router)
    app.include_router(profile.router)
    app.include_router(transactions.router)

    @app.middleware("http")
    async def _basic_auth(request: Request, call_next):
        """Protege tudo com Basic Auth quando APP_PASSWORD está definido."""
        pw = settings.app_password
        if pw and request.url.path != "/api/health":
            header = request.headers.get("authorization", "")
            ok = False
            if header.startswith("Basic "):
                try:
                    user, _, passwd = base64.b64decode(header[6:]).decode().partition(":")
                    ok = secrets.compare_digest(user, settings.app_user) and \
                        secrets.compare_digest(passwd, pw)
                except Exception:
                    ok = False
            if not ok:
                response = error_response(
                    401,
                    "unauthorized",
                    "Autenticação necessária",
                )
                response.headers["WWW-Authenticate"] = 'Basic realm="Raio-X Financeiro"'
                return response
        return await call_next(request)

    @app.on_event("startup")
    def _on_startup() -> None:
        # Não roda sob pytest (evita chamadas de rede ao Pluggy nos testes).
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return
        # Sincroniza o Pluggy ao abrir o app + agenda re-sync periódico.
        if settings.auto_sync_on_start or settings.auto_sync_minutes > 0:
            _start_auto_sync()

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {"sandbox": settings.use_sandbox},
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/connect-token")
    def create_connect_token(
        body: ConnectTokenRequest,
        pc: PluggyClient = Depends(get_pluggy),
    ) -> dict[str, str]:
        try:
            token = pc.create_connect_token(
                client_user_id=body.client_user_id,
                item_id=body.item_id,
            )
        except PluggyAPIError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {"accessToken": token}

    @app.post("/api/items")
    def register_item(
        body: ItemCallbackRequest,
        bg: BackgroundTasks,
        db: Database = Depends(get_db),
    ) -> dict[str, Any]:
        """Chamado pelo frontend após o widget reportar sucesso."""
        db.upsert_pluggy_item(
            body.item_id,
            connector_id=body.connector_id,
            connector_name=body.connector_name,
            status=body.status,
            client_user_id=body.client_user_id,
        )
        bg.add_task(_background_sync, body.item_id, DEFAULT_SYNC_DAYS)
        return {"item_id": body.item_id, "sync_scheduled": True}

    @app.get("/api/items")
    def list_items(db: Database = Depends(get_db)) -> list[dict[str, Any]]:
        accounts_by_item = _accounts_by_pluggy_item(db)
        rows: list[dict[str, Any]] = []
        for r in db.list_pluggy_items():
            item = dict(r)
            accounts = accounts_by_item.get(item["id"], [])
            display_name = _item_display_name(item, accounts)
            item["display_name"] = display_name
            item["account_labels"] = [
                _account_label(account, meta, display_name) for account, meta in accounts
            ]
            rows.append(item)
        return rows

    @app.get("/api/sync-status")
    def sync_status() -> dict[str, Any]:
        return {
            **_sync_state,
            "auto_sync_minutes": settings.auto_sync_minutes,
        }

    @app.post("/api/sync-all")
    def sync_all(
        bg: BackgroundTasks,
        body: SyncRequest | None = Body(default=None),
    ) -> dict[str, Any]:
        """Dispara um sync de todas as contas agora (em background)."""
        days = _normalized_days(body.days if body else None)
        if _sync_state["running"]:
            return {"scheduled": False, "detail": "já em andamento", "days": days}
        bg.add_task(_sync_all_items, days)
        return {"scheduled": True, "days": days}

    @app.post("/api/items/{item_id}/sync")
    def sync_item(
        item_id: str,
        body: SyncRequest,
        bg: BackgroundTasks,
        db: Database = Depends(get_db),
    ) -> dict[str, Any]:
        if not db.get_pluggy_item(item_id):
            raise HTTPException(status_code=404, detail="item desconhecido localmente")
        days = _normalized_days(body.days)
        bg.add_task(_background_sync, item_id, days)
        return {"item_id": item_id, "sync_scheduled": True, "days": days}

    @app.delete("/api/items/{item_id}")
    def remove_item(
        item_id: str,
        db: Database = Depends(get_db),
        pc: PluggyClient = Depends(get_pluggy),
    ) -> dict[str, Any]:
        try:
            pc.delete_item(item_id)
        except PluggyAPIError as e:
            # Se já não existe no Pluggy, segue removendo localmente
            if e.status != 404:
                raise HTTPException(status_code=502, detail=str(e))
        db.delete_pluggy_item(item_id)
        return {"item_id": item_id, "deleted": True}

    @app.get("/api/summary")
    def summary(
        days: int | None = 30,
        months: int | None = None,
        db: Database = Depends(get_db),
    ) -> dict[str, Any]:
        period_months = months if months and months > 0 else None
        if period_months:
            since = _months_cutoff(date.today(), period_months)
        else:
            since = date.today() - timedelta(days=days or 30)
        rows = db.list_transactions(since=since, limit=10_000)
        account_types = {row["id"]: row["type"] for row in db.list_accounts()}

        spend_by_cat: dict[str, float] = {}
        inflow = 0.0
        for r in rows:
            amount = float(r["amount"])
            account_type = account_types.get(r["account_id"])
            category = r["category"] or "(sem categoria)"

            inflow += income_value(amount, account_type, category)

            spent = spending_value(amount, account_type, category)
            if spent:
                spend_by_cat[category] = spend_by_cat.get(category, 0.0) + spent

        by_category = [
            {"category": category, "amount": -total}
            for category, total in sorted(
                (
                    (category, round(total, 2))
                    for category, total in spend_by_cat.items()
                ),
                key=lambda kv: kv[1],
                reverse=True,
            )
            if total > 0
        ]
        outflow = round(sum(row["amount"] for row in by_category), 2)

        return {
            "days": None if period_months else days,
            "period_months": period_months,
            "since": since.isoformat(),
            "transactions": len(rows),
            "inflow": round(inflow, 2),
            "outflow": outflow,
            "net": round(inflow + outflow, 2),
            "by_category": by_category,
        }

    @app.get("/api/dashboard")
    def dashboard(meses: int | None = None, db: Database = Depends(get_db)) -> dict[str, Any]:
        """Agregados prontos para os gráficos (reaproveita o context.py).

        Lê o perfil familiar e os de/para (tradução + recorrências) do disco a
        cada request, então edições na Manutenção valem sem reiniciar.
        `meses` (3/6/12) filtra o período do realizado; ausente = 12 meses.
        """
        period_months = meses if meses and meses > 0 else DEFAULT_DASHBOARD_MONTHS
        profile = mnt.load_family_profile()
        overrides = mnt.load_overrides()
        cat_map = overrides["categorias_pt"]

        # Renda dinâmica: soma das receitas do perfil; senão, MONTHLY_INCOME.
        income = mnt.income_from_profile(profile) or settings.monthly_income

        ctx = build_financial_context(
            db,
            monthly_income=income,
            goals=settings.financial_goals,
            period_months=period_months,
            family_profile=profile,
        ).to_dict()

        periodo_income = ctx["media_renda_mensal"]
        dashboard_income = periodo_income if periodo_income > 0 else income
        fluxo = [{"mes": mes, **vals} for mes, vals in ctx["fluxo_mensal"].items()]
        futuros = ctx["compromissos_futuros"]

        def _tr(name: str) -> str:
            return mnt.translate_category(name, cat_map)

        gasto_cat = [
            {**c, "categoria": _tr(c["categoria"]), "categoria_en": c["categoria"]}
            for c in ctx["gasto_por_categoria"][:12]
        ]
        recorrencias = mnt.apply_recurrence_overrides(
            ctx["recorrencias_provaveis"], overrides["recorrencias"]
        )[:10]

        sobra_mensal = (dashboard_income or 0) - ctx["media_gasto_mensal"]
        wishlist = summarize_wishlist((profile or {}).get("wishlist", []), sobra_mensal)

        # KPIs executivos (Fase 1+7) + frase-resumo
        pf = ctx.get("perfil_familiar") or {}
        provisoes_mensal = pf.get("provisoes_total_mensal", 0.0)
        executivo = summarize_executivo(ctx, dashboard_income, provisoes_mensal)
        patrimonio_liq = pf.get("patrimonio_consolidado", {}).get("patrimonio_liquido")
        _MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        _hoje = date.fromisoformat(ctx["hoje"])
        gasto_total = executivo["fixas"] + executivo["variaveis"]
        frase = (
            f"Em {_MESES[_hoje.month]} de {_hoje.year}, a família gerou "
            f"R$ {executivo['renda']:,.0f} em receitas, gastou R$ {gasto_total:,.0f} "
            f"(R$ {executivo['fixas']:,.0f} fixas + R$ {executivo['variaveis']:,.0f} variáveis), "
            f"com saldo operacional de R$ {executivo['saldo_operacional']:,.0f}"
        )
        if patrimonio_liq is not None:
            frase += f" e patrimônio líquido estimado em R$ {patrimonio_liq:,.0f}"
        frase = frase.replace(",", ".") + "."
        executivo["frase"] = frase

        return {
            "kpis": {
                "renda_media": ctx["media_renda_mensal"],
                "renda_informada": income,
                "gasto_medio": ctx["media_gasto_mensal"],
                "saldo_medio": round(periodo_income - ctx["media_gasto_mensal"], 2),
                "investido_total": ctx["investido_total"],
                "compromissos_futuros": futuros["total"],
                "custo_financeiro": ctx["custo_financeiro"]["total"],
                "pagamentos_cartao": ctx["pagamentos_cartao_total"],
                "meses_cobertos": ctx["meses_cobertos"],
                "periodo_meses": period_months,
            },
            "fluxo_mensal": fluxo,
            "gasto_por_categoria": gasto_cat,
            "budget_5030": summarize_5030(ctx, dashboard_income),
            "recorrencias": recorrencias,
            "compromissos_futuros": {
                "total": futuros["total"],
                "por_categoria": [
                    {"categoria": _tr(k), "total": v}
                    for k, v in futuros["por_categoria"].items()
                ][:8],
                "por_mes": [
                    {"mes": k, "total": v}
                    for k, v in futuros.get("por_mes", {}).items()
                ],
            },
            "custo_financeiro": {
                "total": ctx["custo_financeiro"]["total"],
                "por_categoria": {
                    _tr(k): v for k, v in ctx["custo_financeiro"]["por_categoria"].items()
                },
            },
            "contas": ctx["contas"],
            "perfil_familiar": ctx.get("perfil_familiar"),
            "wishlist": wishlist,
            "executivo": executivo,
        }

    @app.get("/api/cartao")
    def cartao(db: Database = Depends(get_db)) -> dict[str, Any]:
        """Visão de cartões mês a mês (realizado + parcelas futuras) + insights."""
        cat_map = mnt.load_overrides()["categorias_pt"]
        income = mnt.income_from_profile(mnt.load_family_profile()) or settings.monthly_income
        return card_monthly_breakdown(db, cat_map=cat_map, income=income)

    # ---------------------------------------------------------- manutenção
    @app.get("/api/maintenance")
    def get_maintenance() -> dict[str, Any]:
        """Dados editáveis: perfil familiar + de/para (tradução e recorrências)."""
        return {
            "family_profile": mnt.load_family_profile() or {},
            "overrides": mnt.load_overrides(),
        }

    @app.post("/api/maintenance")
    def save_maintenance(body: MaintenanceRequest) -> dict[str, Any]:
        if body.family_profile is not None:
            mnt.save_family_profile(body.family_profile)
        if body.overrides is not None:
            mnt.save_overrides(body.overrides)
        return {"saved": True}

    @app.post("/api/simular")
    def simular(body: SimularRequest) -> dict[str, Any]:
        """Simula uma compra (carro/imóvel): financiar (Price/SAC) × juntar à vista."""
        return simular_compra(
            preco=body.preco,
            entrada=body.entrada,
            prazo_meses=body.prazo_meses,
            juros_aa=body.juros_aa,
            sobra_mensal=body.sobra_mensal,
            rendimento_aa=body.rendimento_aa,
            taxa_adm_consorcio=body.taxa_adm_consorcio,
        )

    @app.post("/api/amortizacao")
    def amortizacao(body: AmortizacaoRequest) -> dict[str, Any]:
        """Simula quitar um financiamento com aporte extra (juros economizados)."""
        return simular_amortizacao(
            saldo=body.saldo,
            juros_aa=body.juros_aa,
            parcela=body.parcela,
            aporte_extra=body.aporte_extra,
        )

    @app.post("/api/analyze")
    def analyze(
        body: AnalyzeRequest,
        db: Database = Depends(get_db),
    ) -> StreamingResponse:
        """Gera a análise financeira por IA em streaming (texto Markdown)."""
        try:
            analyst = FinancialAnalyst.from_settings(settings)
        except AnalystError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Contexto montado já aqui (db ainda aberto); streaming usa só o dict.
        profile = mnt.load_family_profile()
        income = mnt.income_from_profile(profile) or settings.monthly_income
        ctx = build_financial_context(
            db,
            monthly_income=income,
            goals=settings.financial_goals,
            family_profile=profile,
        ).to_dict()

        def generate():
            try:
                for chunk in analyst.stream(body.kind, ctx):
                    yield chunk
            except AnalystError as e:
                yield f"\n\n**Erro:** {e}"

        return StreamingResponse(
            generate(),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app


app = create_app()
