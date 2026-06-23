"""Monta um resumo financeiro agregado para enviar à IA.

Em vez de mandar centenas de transações cruas (caro em tokens e arriscado para a
privacidade), este módulo condensa tudo em: fluxo mensal, gasto por categoria,
recorrências (prováveis assinaturas) e indicadores de dívida. Só agregados —
nenhuma transação individual com nome de pessoa sai daqui.

Convenção de sinais (importante): em conta BANCÁRIA, débito é negativo e crédito
positivo; em CARTÃO DE CRÉDITO, a compra entra positiva e estorno/pagamento
negativo. O gasto real ("regime de competência") soma compras do cartão +
débitos da conta, excluindo transferências internas e o pagamento da fatura (que
apenas liquida o cartão e seria contado em dobro).
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from statistics import mean, pstdev
from typing import Any, Iterable

from ..storage import Database
from .anonymize import anonymize

CREDIT_TYPES = {"CREDIT", "CREDIT_CARD"}

# Custo financeiro real (juros, tarifas) — é o que a auditoria quer cortar.
FINANCIAL_COST_CATEGORIES = {
    "Interests charged",
    "Credit card fees",
    "Loans and financing",
    "Tax on financial operations",
    "Bank fees",
    "Tarifas Bancárias",
}

# Movimentações que NÃO são consumo (transferências internas / liquidação / aporte).
NON_SPENDING_CATEGORIES = {
    "Transfer - PIX",
    "Transfer - Internal",
    "Transfers",
    "Same person transfer",
    "Transferência - PIX",
    "Transferência - TED/DOC",
    "Transferências",
    "Transferências - PIX",
    "Transferências - TED/DOC",
    "Transferência entre contas",
    "Transferência interna",
    "Transfer - Bank Slip",
    "Credit card payment",
    "Payment",
    "Pagamento de fatura",
    "Investments",
    "Investimentos",
}

PIX_TRANSFER_INCOME_CATEGORIES = {"transfer - pix", "transferência - pix"}

INTERNAL_TRANSFER_MATCH_CATEGORIES = {
    "same person transfer",
    "transfer - bank slip",
    "transfer - internal",
    "transfer - pix",
    "transferência - pix",
    "transferência - ted/doc",
    "transferência entre contas",
    "transferência interna",
    "transferências",
    "transferências - pix",
    "transferências - ted/doc",
    "transfers",
}

INVESTMENT_CATEGORIES = {"Investments", "Investimentos"}
CARD_PAYMENT_CATEGORIES = {"Credit card payment", "Pagamento de fatura", "Payment"}
_CARD_PAYMENT_CATEGORY_KEYS = {item.lower() for item in CARD_PAYMENT_CATEGORIES}
_CARD_PAYMENT_TEXT_RE = re.compile(
    r"\b("
    r"pagamento\s+(?:de\s+)?fatura|"
    r"pagamento\s+(?:do\s+)?cart[aã]o|"
    r"pagamento\s+on\s*line|"
    r"pagamento\s+online|"
    r"pgto\s+fatura|"
    r"credit\s+card\s+payment|"
    r"invoice\s+payment"
    r")\b",
    re.IGNORECASE,
)
_OWN_TRANSFER_TEXT_RE = re.compile(r"\b(transferencia enviada|pix enviado)\b", re.IGNORECASE)
_OWNER_LINK_TOKENS = {"de", "da", "do", "das", "dos", "e"}
_OWNER_ALIAS_BLOCKED_TOKENS = {
    "banco",
    "bank",
    "bradesco",
    "btg",
    "caixa",
    "cartao",
    "click",
    "conta",
    "corrente",
    "credito",
    "financeira",
    "instituicao",
    "inter",
    "itau",
    "mastercard",
    "mercado",
    "nu",
    "nubank",
    "pagamento",
    "pagamentos",
    "pago",
    "plat",
    "santander",
    "visa",
}
_DEFAULT_PROFILE = object()

_TOKEN = re.compile(r"[a-zà-ÿ0-9]+", re.IGNORECASE)
_NOISE_TOKENS = {"pessoa", "num", "conta", "cpf", "cnpj", "compra", "debito",
                 "credito", "pagamento", "de", "da", "do", "no", "na", "boleto"}

# Comerciantes que parecem transferência/saque — não são "assinatura/recorrência".
_TRANSFER_NOISE = ("transferencia", "transfer", "pix", "ted", "doc", "saque",
                   "deposito", "resgate", "aplicacao")


def _is_transfer_noise(key: str) -> bool:
    return any(tok in key for tok in _TRANSFER_NOISE)


def _month_key(iso_date: str) -> str:
    return iso_date[:7]  # YYYY-MM


def _category_name(category: str | None) -> str:
    return category or "(sem categoria)"


def _normalized_category(category: str | None) -> str:
    return _category_name(category).strip().lower()


def _fold_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _owner_tokens(value: str | None) -> tuple[str, ...]:
    return tuple(
        token
        for token in _TOKEN.findall(_fold_text(value))
        if token not in _OWNER_LINK_TOKENS
    )


def _owner_alias_tokens(value: str | None) -> tuple[str, ...]:
    tokens = tuple(token for token in _owner_tokens(value) if not token.isdigit())
    if len(tokens) < 2:
        return ()
    if any(token in _OWNER_ALIAS_BLOCKED_TOKENS for token in tokens):
        return ()
    return tokens


def account_owner_aliases(
    accounts: Iterable[Any],
    *,
    profile_name: str | None = None,
) -> tuple[str, ...]:
    aliases: set[str] = set()
    for candidate in (profile_name,):
        tokens = _owner_alias_tokens(candidate)
        if tokens:
            aliases.add(" ".join(tokens))
    for account in accounts:
        for field in ("name", "institution"):
            tokens = _owner_alias_tokens(_row_value(account, field))
            if tokens:
                aliases.add(" ".join(tokens))
    return tuple(sorted(aliases))


def _is_non_credit_account(account_type: str | None) -> bool:
    return (account_type or "").upper() not in CREDIT_TYPES


def _is_pix_transfer_income_candidate(
    amount: float,
    account_type: str | None,
    category: str | None,
) -> bool:
    return (
        float(amount) > 0
        and _is_non_credit_account(account_type)
        and _normalized_category(category) in PIX_TRANSFER_INCOME_CATEGORIES
    )


def is_card_payment_like(
    amount: float,
    account_type: str | None,
    category: str | None,
    *,
    description: str | None = None,
    raw_description: str | None = None,
) -> bool:
    if _normalized_category(category) in _CARD_PAYMENT_CATEGORY_KEYS:
        return True
    if float(amount) >= 0 or (account_type or "").upper() not in CREDIT_TYPES:
        return False

    text = " ".join(
        part.strip()
        for part in (raw_description, description)
        if part and part.strip()
    )
    return bool(text and _CARD_PAYMENT_TEXT_RE.search(text))


def is_own_account_transfer_like(
    amount: float,
    account_type: str | None,
    category: str | None,
    *,
    description: str | None = None,
    raw_description: str | None = None,
    owner_names: Iterable[str] | None = None,
) -> bool:
    if float(amount) >= 0 or not _is_non_credit_account(account_type):
        return False
    if not owner_names:
        return False

    text = " ".join(
        part.strip()
        for part in (raw_description, description)
        if part and part.strip()
    )
    folded_text = _fold_text(text)
    if not _OWN_TRANSFER_TEXT_RE.search(folded_text):
        return False

    text_tokens = set(_owner_tokens(folded_text))
    for owner_name in owner_names:
        owner_tokens = _owner_alias_tokens(owner_name)
        if owner_tokens and set(owner_tokens).issubset(text_tokens):
            return True
    return False


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        pass
    if hasattr(row, "get"):
        return row.get(key, default)
    return default


def _row_account_type(row: Any, account_types: dict[str, str] | None) -> str | None:
    account_type = _row_value(row, "account_type")
    if account_type:
        return str(account_type)
    account_id = _row_value(row, "account_id")
    if account_types and account_id:
        return account_types.get(str(account_id))
    return None


def _row_date(row: Any) -> date | None:
    raw = _row_value(row, "posted_at")
    if raw is None:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def internal_transfer_credit_ids(
    rows: list[Any],
    *,
    account_types: dict[str, str] | None = None,
    day_window: int = 2,
) -> set[Any]:
    """Return positive PIX transfer row ids that have a mirrored connected-account debit."""
    credits: list[dict[str, Any]] = []
    debits: list[dict[str, Any]] = []

    for row in rows:
        account_type = _row_account_type(row, account_types)
        if not _is_non_credit_account(account_type):
            continue

        try:
            amount = float(_row_value(row, "amount", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue

        category = _row_value(row, "category")
        row_id = _row_value(row, "id")
        account_id = _row_value(row, "account_id")
        posted = _row_date(row)
        if row_id is None or account_id is None or posted is None:
            continue

        normalized_category = _normalized_category(category)
        payload = {
            "id": row_id,
            "account_id": str(account_id),
            "posted": posted,
            "amount_abs": round(abs(amount), 2),
        }
        if amount > 0 and normalized_category in PIX_TRANSFER_INCOME_CATEGORIES:
            credits.append(payload)
        elif amount < 0 and normalized_category in INTERNAL_TRANSFER_MATCH_CATEGORIES:
            debits.append(payload)

    matched: set[Any] = set()
    for credit in credits:
        for debit in debits:
            if credit["account_id"] == debit["account_id"]:
                continue
            if abs(credit["amount_abs"] - debit["amount_abs"]) > 0.01:
                continue
            if abs((credit["posted"] - debit["posted"]).days) > day_window:
                continue
            matched.add(credit["id"])
            break
    return matched


def spending_value(
    amount: float,
    account_type: str | None,
    category: str | None,
    *,
    description: str | None = None,
    raw_description: str | None = None,
    owner_names: Iterable[str] | None = None,
) -> float:
    """Return positive spending impact for expenses and negative impact for refunds."""
    category_name = _category_name(category)
    if category_name in NON_SPENDING_CATEGORIES or is_card_payment_like(
        amount,
        account_type,
        category,
        description=description,
        raw_description=raw_description,
    ) or is_own_account_transfer_like(
        amount,
        account_type,
        category,
        description=description,
        raw_description=raw_description,
        owner_names=owner_names,
    ):
        return 0.0

    value = float(amount)
    if (account_type or "").upper() in CREDIT_TYPES:
        return value
    return -value if value < 0 else 0.0


def income_value(
    amount: float,
    account_type: str | None,
    category: str | None,
    *,
    external_transfer_income: bool = False,
) -> float:
    """Return income from bank accounts only, excluding internal movements."""
    category_name = _category_name(category)
    value = float(amount)
    if category_name in NON_SPENDING_CATEGORIES:
        if external_transfer_income and _is_pix_transfer_income_candidate(
            value,
            account_type,
            category,
        ):
            return value
        return 0.0
    if (account_type or "").upper() in CREDIT_TYPES:
        return 0.0

    return value if value > 0 else 0.0


def _merchant_key(raw: str) -> str:
    """Normaliza a descrição para agrupar transações do mesmo comerciante."""
    clean = anonymize(raw).lower()
    tokens = [t for t in _TOKEN.findall(clean) if t not in _NOISE_TOKENS and not t.isdigit()]
    return " ".join(tokens[:4])


@dataclass
class FinancialContext:
    today: str
    months_covered: int
    monthly_income: float | None
    goals: list[str]
    accounts: list[dict[str, Any]]
    realized_months: dict[str, dict[str, float]]
    avg_monthly_spending: float
    avg_monthly_income: float
    spending_by_category: list[dict[str, Any]]
    recurring: list[dict[str, Any]]
    financial_cost: dict[str, Any]
    card_payments_total: float
    invested_total: float
    period_invested_total: float
    portfolio_invested_total: float
    future_commitments: dict[str, Any]
    notes: list[str] = field(default_factory=list)
    family_profile: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "hoje": self.today,
            "meses_cobertos": self.months_covered,
            "renda_mensal_informada": self.monthly_income,
            "objetivos": self.goals,
            "contas": self.accounts,
            "fluxo_mensal": self.realized_months,
            "media_gasto_mensal": round(self.avg_monthly_spending, 2),
            "media_renda_mensal": round(self.avg_monthly_income, 2),
            "gasto_por_categoria": self.spending_by_category,
            "recorrencias_provaveis": self.recurring,
            "custo_financeiro": self.financial_cost,
            "pagamentos_cartao_total": round(self.card_payments_total, 2),
            "investido_total": round(self.invested_total, 2),
            "aportes_periodo_total": round(self.period_invested_total, 2),
            "carteira_investimentos_total": round(self.portfolio_invested_total, 2),
            "compromissos_futuros": self.future_commitments,
            "observacoes": self.notes,
        }
        if self.family_profile:
            receitas = self.family_profile.get("receitas", [])
            patrimonio = self.family_profile.get("patrimonio", {})
            provisoes = self.family_profile.get("provisoes", [])
            metas = self.family_profile.get("metas", [])

            imoveis = patrimonio.get("imoveis", [])
            caixas = patrimonio.get("investimentos_caixa", [])

            valor_imoveis = sum(i.get("valor_mercado", 0.0) for i in imoveis)
            valor_caixas = sum(c.get("valor", 0.0) for c in caixas)
            total_ativos = valor_imoveis + valor_caixas

            total_passivos = sum(i.get("saldo_devedor", 0.0) for i in imoveis)
            patrimonio_liquido = total_ativos - total_passivos

            fluxo_imoveis = []
            for i in imoveis:
                rec = i.get("aluguel_receita", 0.0)
                custos = i.get("custos", {})
                custo_total = sum(custos.values())
                fluxo_imoveis.append({
                    "nome": i.get("nome"),
                    "receita": rec,
                    "custos": custos,
                    "custo_total": custo_total,
                    "resultado": rec - custo_total
                })

            d["perfil_familiar"] = {
                "receitas": receitas,
                "patrimonio_consolidado": {
                    "total_ativos": round(total_ativos, 2),
                    "total_passivos": round(total_passivos, 2),
                    "patrimonio_liquido": round(patrimonio_liquido, 2),
                    "detalhe_ativos": {
                        "imoveis": round(valor_imoveis, 2),
                        "caixas_investimentos": round(valor_caixas, 2)
                    }
                },
                "fluxo_imoveis": fluxo_imoveis,
                "investimentos_caixa": caixas,
                "provisoes": provisoes,
                "provisoes_total_mensal": round(sum(p.get("mensal", 0.0) for p in provisoes), 2),
                "metas": metas
            }
        else:
            d["perfil_familiar"] = None
        return d


def _cutoff_iso(today: date, period_months: int) -> str:
    """Primeiro dia do mês `period_months-1` meses atrás (janela inclui o mês atual)."""
    idx = (today.year * 12 + (today.month - 1)) - (period_months - 1)
    cy, cm = divmod(idx, 12)
    return date(cy, cm + 1, 1).isoformat()


def _portfolio_current_value(db: Database) -> float:
    row = db._conn.execute(
        """
        SELECT COALESCE(SUM(COALESCE(current_value, 0)), 0) AS total
          FROM portfolio_assets
         WHERE status IS NULL OR status='ACTIVE'
        """
    ).fetchone()
    return round(float(row["total"] or 0.0), 2) if row else 0.0


def build_financial_context(
    db: Database,
    *,
    monthly_income: float | None = None,
    goals: list[str] | None = None,
    today: date | None = None,
    period_months: int | None = None,
    family_profile: Any = _DEFAULT_PROFILE,
) -> FinancialContext:
    today = today or date.today()
    today_iso = today.isoformat()
    cutoff_iso = _cutoff_iso(today, period_months) if period_months else None

    if family_profile is _DEFAULT_PROFILE:
        from ..config import settings
        family_profile = settings.family_profile

    accounts = db.list_accounts()
    acct_type = {a["id"]: (a["type"] or "").upper() for a in accounts}
    owner_names = account_owner_aliases(accounts)
    rows = db.list_transactions(limit=100_000)
    internal_transfer_income_ids = internal_transfer_credit_ids(rows, account_types=acct_type)

    realized_months: dict[str, dict[str, float]] = defaultdict(
        lambda: {"renda": 0.0, "gasto": 0.0, "investido": 0.0}
    )
    spending: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0.0, "count": 0})
    merchant_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cost_by_cat: dict[str, float] = defaultdict(float)
    cost_total = card_payments_total = period_invested_total = 0.0
    future_total = 0.0
    future_by_cat: dict[str, float] = defaultdict(float)
    future_by_month: dict[str, float] = defaultdict(float)

    for r in rows:
        posted = r["posted_at"]
        amount = float(r["amount"])
        category = _category_name(r["category"])
        account_type = acct_type.get(r["account_id"], "")
        is_credit = account_type in CREDIT_TYPES

        # Valor de consumo (positivo = gastou; negativo = estorno).
        spend_val = spending_value(
            amount,
            account_type,
            category,
            description=r["description"],
            raw_description=r["raw_description"],
            owner_names=owner_names,
        )
        is_spending = spend_val != 0.0

        if posted > today_iso:  # compromisso futuro (ex.: parcelas a vencer)
            if is_spending:
                future_total += spend_val
                future_by_cat[category] += spend_val
                future_by_month[_month_key(posted)] += spend_val
            continue

        # Filtro de período (3/6/12 meses) — só afeta o realizado.
        if cutoff_iso and posted < cutoff_iso:
            continue

        mk = _month_key(posted)

        # Renda: entradas em conta (não-cartão) que não são transferência interna.
        income_val = income_value(
            amount,
            account_type,
            category,
            external_transfer_income=r["id"] not in internal_transfer_income_ids,
        )
        if income_val:
            realized_months[mk]["renda"] += income_val

        if category in INVESTMENT_CATEGORIES and amount < 0:
            period_invested_total += -amount
            realized_months[mk]["investido"] += -amount

        if category in CARD_PAYMENT_CATEGORIES and not is_credit and amount < 0:
            card_payments_total += -amount

        if category in FINANCIAL_COST_CATEGORIES and spend_val > 0:
            cost_total += spend_val
            cost_by_cat[category] += spend_val

        if is_spending:
            realized_months[mk]["gasto"] += spend_val
            spending[category]["total"] += spend_val
            spending[category]["count"] += 1
            key = _merchant_key(r["raw_description"] or r["description"] or "")
            if key:
                merchant_groups[key].append({"month": mk, "amount": spend_val})

    months_covered = max(1, len(realized_months))
    total_spending = sum(m["gasto"] for m in realized_months.values())
    total_income = sum(m["renda"] for m in realized_months.values())

    spending_list = sorted(
        (
            {"categoria": c, "total": round(v["total"], 2), "qtd": int(v["count"]),
             "media_mensal": round(v["total"] / months_covered, 2)}
            for c, v in spending.items() if v["total"] > 0
        ),
        key=lambda x: x["total"],
        reverse=True,
    )

    recurring: list[dict[str, Any]] = []
    for key, items in merchant_groups.items():
        if _is_transfer_noise(key):
            continue
        months = {it["month"] for it in items}
        if len(months) < 3:
            continue
        amounts = [it["amount"] for it in items]
        avg = mean(amounts)
        cv = (pstdev(amounts) / avg) if avg else 0
        recurring.append({
            "comerciante": key,
            "meses": len(months),
            "ocorrencias": len(items),
            "valor_medio": round(avg, 2),
            "estavel": bool(cv < 0.15),
            "total": round(sum(amounts), 2),
        })
    recurring.sort(key=lambda x: x["total"], reverse=True)

    accounts = [
        {"nome": anonymize(a["name"]) or "—", "tipo": a["type"] or "—"}
        for a in db.list_accounts()
    ]

    notes: list[str] = []
    if future_total:
        notes.append(
            f"Há R$ {future_total:,.2f} em compromissos futuros (faturas/parcelas "
            "de cartão a vencer), separados do gasto realizado."
        )
    portfolio_invested_total = _portfolio_current_value(db)
    invested_total = portfolio_invested_total if portfolio_invested_total > 0 else period_invested_total
    if portfolio_invested_total > 0:
        notes.append(
            "Investido total usa o valor atual da carteira de investimentos; "
            "aportes do período ficam separados para o fluxo mensal."
        )
    notes.append(
        "Gasto = regime de competência (compras de cartão + débitos), excluindo "
        "transferências internas, aportes e pagamento de fatura."
    )

    return FinancialContext(
        today=today_iso,
        months_covered=months_covered,
        monthly_income=monthly_income,
        goals=goals or [],
        accounts=accounts,
        realized_months={k: {kk: round(vv, 2) for kk, vv in v.items()}
                         for k, v in sorted(realized_months.items())},
        avg_monthly_spending=total_spending / months_covered,
        avg_monthly_income=total_income / months_covered,
        spending_by_category=spending_list,
        recurring=recurring,
        financial_cost={
            "total": round(cost_total, 2),
            "por_categoria": {k: round(v, 2) for k, v in
                              sorted(cost_by_cat.items(), key=lambda x: -x[1])},
        },
        card_payments_total=card_payments_total,
        invested_total=invested_total,
        period_invested_total=period_invested_total,
        portfolio_invested_total=portfolio_invested_total,
        future_commitments={
            "total": round(future_total, 2),
            "por_categoria": {k: round(v, 2) for k, v in
                              sorted(future_by_cat.items(), key=lambda x: -x[1])},
            "por_mes": {k: round(v, 2) for k, v in sorted(future_by_month.items())},
        },
        notes=notes,
        family_profile=family_profile,
    )
