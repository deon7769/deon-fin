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
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from ..agent import AnalystError, Categorizer, FinancialAnalyst, build_financial_context
from ..agent.buckets import CATEGORY_BUCKET_MAP, apply_buckets_to_database
from ..agent.budget import summarize_5030, summarize_executivo, summarize_wishlist
from ..agent.context import (
    CREDIT_TYPES,
    FINANCIAL_COST_CATEGORIES,
    INTERNAL_TRANSFER_MATCH_CATEGORIES,
    INVESTMENT_CATEGORIES,
    PIX_TRANSFER_SPENDING_CATEGORIES,
    account_owner_aliases,
    income_value,
    internal_transfer_credit_ids,
    internal_transfer_row_ids,
    is_card_payment_like,
    is_own_account_transfer_like,
    spending_value,
)
from ..agent.tags import apply_tags_to_database
from ..agent.simulator import simular_amortizacao, simular_compra
from ..agent.cards import card_monthly_breakdown
from ..agent import maintenance as mnt
from ..auth.sessions import SESSION_COOKIE_NAME, AuthSession, current_session
from ..config import settings
from ..importers import sync_pluggy_item
from ..pluggy import PluggyAPIError, PluggyClient
from ..storage import Database
from ..storage.postgres import connect_postgres
from .dependencies import get_db, get_pluggy
from .errors import error_response, install_error_handlers
from .repositories import profile_repo, system_totals_repo, transactions_repo
from .routers import auth, accounts, buckets, budget, invoices, maintenance, painel, portfolio, profile, savings, simulations, tags, transactions

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


def _web_dist_dir() -> Path:
    return Path(os.environ.get("WEB_DIST_DIR", "web_dist"))


def _legacy_ui_enabled() -> bool:
    value = os.environ.get("LEGACY_UI", "")
    return value.lower() in {"1", "true", "yes"}


def _session_auth_enabled() -> bool:
    return bool(getattr(settings, "session_auth_enabled", False))


def _session_public_api_path(path: str) -> bool:
    return path == "/api/health" or path.startswith("/api/auth/")


def _session_public_path(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    if _session_public_api_path(path):
        return True
    if path in {"/login", "/login/", "/favicon.ico", "/world.geo.json"}:
        return True
    return path.startswith("/_next/") or path.startswith("/static/")


def _session_response_for_missing_auth(path: str, method: str) -> Response:
    if path.startswith("/api/") or method not in {"GET", "HEAD"}:
        return error_response(
            401,
            "session_required",
            "Sessão necessária",
        )
    return RedirectResponse("/login", status_code=303)


def _session_requires_origin_check(method: str) -> bool:
    return method.upper() not in {"GET", "HEAD", "OPTIONS", "TRACE"}


def _normalized_origin(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return None
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _request_base_origin(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",", 1)[0].strip()
    scheme = forwarded_proto or request.url.scheme
    host = forwarded_host or request.headers.get("host") or request.url.netloc
    return f"{scheme.lower()}://{host.lower()}"


def _session_allowed_origins(request: Request) -> set[str]:
    origins = {_request_base_origin(request)}
    for configured in getattr(settings, "cors_origins", []) or []:
        if configured == "*":
            continue
        origin = _normalized_origin(configured)
        if origin:
            origins.add(origin)
    return origins


def _session_origin_allowed(request: Request) -> bool:
    origin = _normalized_origin(request.headers.get("origin"))
    if origin:
        return origin in _session_allowed_origins(request)

    referer = _normalized_origin(request.headers.get("referer"))
    if referer:
        return referer in _session_allowed_origins(request)

    return False


def _session_from_request(request: Request) -> AuthSession | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    pepper = getattr(settings, "auth_pepper", None)
    if not pepper:
        raise RuntimeError("AUTH_PEPPER is required for session authentication")

    with connect_postgres(settings.database_url) as conn:
        return current_session(conn, token, pepper=pepper)


def _next_index_exists() -> bool:
    return (_web_dist_dir() / "index.html").is_file()


def _safe_web_dist_path(full_path: str) -> Path | None:
    web_dist = _web_dist_dir().resolve()
    candidate = (web_dist / full_path).resolve()
    try:
        candidate.relative_to(web_dist)
    except ValueError:
        return None
    return candidate


def _html_file_response(path: Path) -> FileResponse:
    response = FileResponse(path, media_type="text/html")
    response.headers["Cache-Control"] = "no-cache"
    return response


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


def _render_legacy_index(request: Request) -> Response:
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {"sandbox": settings.use_sandbox},
    )


def _category_translation_audit(db: Database, cat_map: dict[str, str]) -> dict[str, Any]:
    translated_keys = {
        str(key).lower().strip()
        for key, value in cat_map.items()
        if str(key).strip() and str(value).strip()
    }
    rows = db._conn.execute(
        """
        SELECT lower(trim(category)) AS key,
               min(trim(category)) AS category,
               count(*) AS tx_count,
               round(sum(abs(amount)), 2) AS total_abs
          FROM transactions
         WHERE category IS NOT NULL
           AND trim(category) <> ''
         GROUP BY lower(trim(category))
         ORDER BY count(*) DESC, sum(abs(amount)) DESC, lower(trim(category))
        """
    ).fetchall()
    missing: list[dict[str, Any]] = []
    translated = 0
    for row in rows:
        if row["key"] in translated_keys:
            translated += 1
            continue
        missing.append(
            {
                "category": row["category"],
                "tx_count": int(row["tx_count"]),
                "total_abs": float(row["total_abs"] or 0.0),
            }
        )

    return {
        "total_categories": len(rows),
        "translated": translated,
        "missing": missing[:25],
    }


_CLASSIFICATION_SOURCES = ("manual", "rule", "auto")
_BLOCKED_CLASSIFICATION_CATEGORY_KEYS = {
    key for key, bucket_key in CATEGORY_BUCKET_MAP.items() if bucket_key is None
}
_PIX_TRANSFER_SPENDING_CATEGORY_KEYS = {
    value.strip().lower() for value in PIX_TRANSFER_SPENDING_CATEGORIES
}
_INTERNAL_TRANSFER_CATEGORY_KEYS = {
    value.strip().lower() for value in INTERNAL_TRANSFER_MATCH_CATEGORIES
}
_INVESTMENT_CATEGORY_KEYS = {value.strip().lower() for value in INVESTMENT_CATEGORIES}
_FINANCIAL_COST_CATEGORY_KEYS = {
    value.strip().lower() for value in FINANCIAL_COST_CATEGORIES
}


def _classification_source_counts(rows: list[Any], column: str) -> dict[str, int]:
    counts = {source: 0 for source in _CLASSIFICATION_SOURCES}
    counts["none"] = 0
    for row in rows:
        source = str(row[column] or "").strip().lower()
        if source in counts and row[column.replace("_source", "_id")] is not None:
            counts[source] += 1
        else:
            counts["none"] += 1
    return counts


def _classification_issue_row(row: Any, cat_map: dict[str, str]) -> dict[str, Any]:
    category = row["category"]
    return {
        "id": row["id"],
        "date": str(row["posted_at"])[:10],
        "description": row["description"],
        "account_name": row["account_name"] or row["institution"] or row["account_id"],
        "category": category,
        "category_label": mnt.translate_category(category or "(sem categoria)", cat_map),
        "amount_abs": round(abs(float(row["amount"] or 0.0)), 2),
    }


def _classification_policy_reason(
    row: Any,
    owner_names: list[str] | tuple[str, ...],
    *,
    bucket_policy: bool,
    internal_transfer_ids: set[Any] | None = None,
) -> tuple[str, str]:
    amount = float(row["amount"] or 0.0)
    category = row["category"]
    category_key = str(category or "").strip().lower()
    account_type = row["account_type"]
    description = row["description"]
    raw_description = row["raw_description"]
    row_id = row["id"]
    is_known_internal_transfer = internal_transfer_ids is not None and row_id in internal_transfer_ids

    if is_card_payment_like(
        amount,
        account_type,
        category,
        description=description,
        raw_description=raw_description,
    ):
        return "card_payment", "Pagamento de fatura"
    if is_known_internal_transfer or is_own_account_transfer_like(
        amount,
        account_type,
        category,
        description=description,
        raw_description=raw_description,
        owner_names=owner_names,
    ):
        return "internal_transfer", "Transferência interna"
    if category_key in _INVESTMENT_CATEGORY_KEYS:
        return "investment", "Investimento/aporte"
    if bucket_policy and category_key in _FINANCIAL_COST_CATEGORY_KEYS:
        return "financial_cost", "Custo financeiro sem pote"
    if bucket_policy and category_key in _BLOCKED_CLASSIFICATION_CATEGORY_KEYS:
        return "blocked_bucket", "Categoria sem pote por política"
    if amount > 0 and (account_type or "").upper() not in CREDIT_TYPES:
        return "income", "Receita/entrada"
    return "non_spending", "Movimento sem consumo"


def _classification_policy_row(
    row: Any,
    cat_map: dict[str, str],
    owner_names: list[str] | tuple[str, ...],
    *,
    bucket_policy: bool,
    internal_transfer_ids: set[Any] | None = None,
) -> dict[str, Any]:
    reason, reason_label = _classification_policy_reason(
        row,
        owner_names,
        bucket_policy=bucket_policy,
        internal_transfer_ids=internal_transfer_ids,
    )
    return {
        **_classification_issue_row(row, cat_map),
        "reason": reason,
        "reason_label": reason_label,
    }


def _classification_health(db: Database, cat_map: dict[str, str]) -> dict[str, Any]:
    owner_names = account_owner_aliases(db.list_accounts())
    rows = db._conn.execute(
        """
        SELECT t.id, t.posted_at, t.description, t.raw_description, t.category, t.amount,
               t.tag_id, t.tag_source, t.bucket_id, t.bucket_source,
               t.account_id, a.name AS account_name, a.institution, a.type AS account_type
          FROM transactions t
          LEFT JOIN accounts a ON a.id = t.account_id
         ORDER BY abs(t.amount) DESC, t.posted_at DESC, t.id DESC
        """
    ).fetchall()

    total = len(rows)
    tagged = sum(1 for row in rows if row["tag_id"] is not None)
    bucketed = sum(1 for row in rows if row["bucket_id"] is not None)
    internal_transfer_ids = internal_transfer_row_ids(rows, owner_names=owner_names)

    spending_rows = [
        row
        for row in rows
        if spending_value(
            float(row["amount"] or 0.0),
            row["account_type"],
            row["category"],
            description=row["description"],
            raw_description=row["raw_description"],
            owner_names=owner_names,
            external_transfer_spending=row["id"] not in internal_transfer_ids,
        )
        > 0
    ]
    bucket_actionable_rows = [
        row
        for row in spending_rows
        if str(row["category"] or "").strip().lower()
        not in _BLOCKED_CLASSIFICATION_CATEGORY_KEYS
        or (
            row["id"] not in internal_transfer_ids
            and str(row["category"] or "").strip().lower()
            in _PIX_TRANSFER_SPENDING_CATEGORY_KEYS
        )
    ]
    missing_tag = [row for row in spending_rows if row["tag_id"] is None]
    missing_bucket = [row for row in bucket_actionable_rows if row["bucket_id"] is None]
    spending_row_ids = {row["id"] for row in spending_rows}
    bucket_actionable_row_ids = {row["id"] for row in bucket_actionable_rows}
    ignored_tag_policy = [
        row
        for row in rows
        if row["tag_id"] is None
        and row["id"] not in spending_row_ids
    ]
    ignored_bucket_policy = [
        row
        for row in rows
        if row["bucket_id"] is None
        and row["id"] not in bucket_actionable_row_ids
    ]

    return {
        "total_transactions": total,
        "tagged": tagged,
        "untagged": total - tagged,
        "bucketed": bucketed,
        "unbucketed": total - bucketed,
        "tag_sources": _classification_source_counts(rows, "tag_source"),
        "bucket_sources": _classification_source_counts(rows, "bucket_source"),
        "missing_tag_review_count": len(missing_tag),
        "missing_bucket_review_count": len(missing_bucket),
        "ignored_tag_policy_count": len(ignored_tag_policy),
        "ignored_bucket_policy_count": len(ignored_bucket_policy),
        "missing_tag": [_classification_issue_row(row, cat_map) for row in missing_tag[:10]],
        "missing_bucket": [_classification_issue_row(row, cat_map) for row in missing_bucket[:10]],
        "ignored_tag_policy": [
            _classification_policy_row(
                row,
                cat_map,
                owner_names,
                bucket_policy=False,
                internal_transfer_ids=internal_transfer_ids,
            )
            for row in ignored_tag_policy[:10]
        ],
        "ignored_bucket_policy": [
            _classification_policy_row(
                row,
                cat_map,
                owner_names,
                bucket_policy=True,
                internal_transfer_ids=internal_transfer_ids,
            )
            for row in ignored_bucket_policy[:10]
        ],
    }


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
        apply_tags_to_database(db)
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
        apply_tags_to_database(db)
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
    next_assets = _web_dist_dir() / "_next"
    if next_assets.exists():
        app.mount("/_next", StaticFiles(directory=str(next_assets)), name="next-assets")
    app.include_router(auth.router)
    app.include_router(accounts.router)
    app.include_router(buckets.router)
    app.include_router(budget.router)
    app.include_router(invoices.router)
    app.include_router(maintenance.router)
    app.include_router(painel.router)
    app.include_router(portfolio.router)
    app.include_router(savings.router)
    app.include_router(tags.router)
    app.include_router(profile.router)
    app.include_router(transactions.router)
    app.include_router(simulations.router)

    @app.middleware("http")
    async def _basic_auth(request: Request, call_next):
        """Protege tudo com Basic Auth quando APP_PASSWORD está definido."""
        if _session_auth_enabled():
            if not _session_public_path(request.url.path, request.method):
                try:
                    auth_session = _session_from_request(request)
                except Exception:
                    log.exception("Session authentication failed before route handling")
                    return error_response(
                        503,
                        "session_auth_unavailable",
                        "Autenticação por sessão indisponível",
                    )

                if auth_session is None:
                    return _session_response_for_missing_auth(request.url.path, request.method)
                request.state.auth_session = auth_session

            if _session_requires_origin_check(request.method) and not _session_origin_allowed(request):
                return error_response(
                    403,
                    "invalid_origin",
                    "Origem da requisição inválida",
                )
            return await call_next(request)

        pw = settings.app_password
        if pw and request.url.path != "/api/health" and not request.url.path.startswith("/api/auth/"):
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

    @app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
    def index(request: Request) -> Response:
        if _legacy_ui_enabled() or not _next_index_exists():
            return _render_legacy_index(request)
        return _html_file_response(_web_dist_dir() / "index.html")

    @app.api_route("/legacy", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)
    def legacy(request: Request) -> Response:
        return _render_legacy_index(request)

    @app.api_route("/simulador", methods=["GET", "HEAD"], include_in_schema=False)
    def simulador_redirect() -> RedirectResponse:
        return RedirectResponse("/simulacoes")

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
        rows = db._conn.execute(
            f"""
            SELECT t.id,
                   t.account_id,
                   t.posted_at,
                   t.amount,
                   t.description,
                   t.raw_description,
                   t.category,
                   a.type AS account_type
              FROM transactions t
              LEFT JOIN accounts a ON a.id = t.account_id
              {system_totals_repo.account_transaction_policy_join("t", "summary_total_settings")}
             WHERE t.posted_at >= ?
               AND COALESCE(t.hidden, 0) = 0
               AND {system_totals_repo.account_transaction_policy_where("summary_total_settings")}
             ORDER BY t.posted_at DESC, t.id
             LIMIT 10000
            """,
            (since.isoformat(),),
        ).fetchall()
        rows = system_totals_repo.filter_rows_by_movement_policy(db, rows)
        accounts = db.list_accounts()
        owner_names = account_owner_aliases(accounts)
        internal_transfer_income_ids = internal_transfer_credit_ids(rows)
        internal_transfer_ids = internal_transfer_row_ids(
            rows,
            owner_names=owner_names,
        )

        spend_by_cat: dict[str, float] = {}
        inflow = 0.0
        for r in rows:
            amount = float(r["amount"])
            account_type = r["account_type"]
            category = r["category"] or "(sem categoria)"

            inflow += income_value(
                amount,
                account_type,
                category,
                external_transfer_income=r["id"] not in internal_transfer_income_ids,
            )

            spent = spending_value(
                amount,
                account_type,
                category,
                description=r["description"],
                raw_description=r["raw_description"],
                owner_names=owner_names,
                external_transfer_spending=r["id"] not in internal_transfer_ids,
            )
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
    def get_maintenance(db: Database = Depends(get_db)) -> dict[str, Any]:
        """Dados editáveis: perfil familiar + de/para (tradução e recorrências)."""
        overrides = mnt.load_overrides()
        return {
            "family_profile": mnt.load_family_profile() or {},
            "overrides": overrides,
            "category_audit": _category_translation_audit(db, overrides.get("categorias_pt") or {}),
            "classification_health": _classification_health(db, overrides.get("categorias_pt") or {}),
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

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def spa_fallback(full_path: str) -> Response:
        prefix = full_path.split("/", 1)[0]
        if prefix in {"api", "static", "_next"}:
            raise HTTPException(status_code=404)

        if not _next_index_exists():
            raise HTTPException(status_code=404)

        candidate = _safe_web_dist_path(full_path)
        if candidate and candidate.is_file():
            if candidate.suffix.lower() == ".html":
                return _html_file_response(candidate)
            return FileResponse(candidate)

        if candidate and candidate.is_dir():
            route_index = candidate / "index.html"
            if route_index.is_file():
                return _html_file_response(route_index)

        return _html_file_response(_web_dist_dir() / "index.html")

    return app


app = create_app()
