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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from statistics import mean, pstdev
from typing import Any

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
    "Transfers",
    "Same person transfer",
    "Transferências - PIX",
    "Transferências - TED/DOC",
    "Transfer - Bank Slip",
    "Credit card payment",
    "Investments",
}

INVESTMENT_CATEGORIES = {"Investments", "Investimentos"}
CARD_PAYMENT_CATEGORIES = {"Credit card payment"}
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

    acct_type = {a["id"]: (a["type"] or "").upper() for a in db.list_accounts()}
    rows = db.list_transactions(limit=100_000)

    realized_months: dict[str, dict[str, float]] = defaultdict(
        lambda: {"renda": 0.0, "gasto": 0.0, "investido": 0.0}
    )
    spending: dict[str, dict[str, float]] = defaultdict(lambda: {"total": 0.0, "count": 0})
    merchant_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cost_by_cat: dict[str, float] = defaultdict(float)
    cost_total = card_payments_total = invested_total = 0.0
    future_total = 0.0
    future_by_cat: dict[str, float] = defaultdict(float)
    future_by_month: dict[str, float] = defaultdict(float)

    for r in rows:
        posted = r["posted_at"]
        amount = float(r["amount"])
        category = r["category"] or "(sem categoria)"
        is_credit = acct_type.get(r["account_id"], "") in CREDIT_TYPES

        # Valor de consumo (positivo = gastou); 0 se não for consumo.
        if is_credit:
            spend_val = amount          # compra positiva, estorno negativo
        else:
            spend_val = -amount if amount < 0 else 0.0
        is_spending = category not in NON_SPENDING_CATEGORIES and spend_val != 0.0

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
        if not is_credit and amount > 0 and category not in NON_SPENDING_CATEGORIES:
            realized_months[mk]["renda"] += amount

        if category in INVESTMENT_CATEGORIES and amount < 0:
            invested_total += -amount
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
        future_commitments={
            "total": round(future_total, 2),
            "por_categoria": {k: round(v, 2) for k, v in
                              sorted(future_by_cat.items(), key=lambda x: -x[1])},
            "por_mes": {k: round(v, 2) for k, v in sorted(future_by_month.items())},
        },
        notes=notes,
        family_profile=family_profile,
    )
