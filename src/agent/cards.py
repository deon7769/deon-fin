"""Visão de cartões de crédito mês a mês (realizado + parcelas futuras) + insights.

Em conta de CARTÃO, a compra entra positiva e estorno/pagamento negativo. Aqui
agregamos só as contas de crédito, por mês, separando o que já foi gasto
(realizado/mês atual) do que já está parcelado para os próximos meses (futuro).
Também calcula: % da renda comprometida, top comerciantes e alertas.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import mean
from typing import Any

from ..storage import Database
from .context import NON_SPENDING_CATEGORIES, _merchant_key

CREDIT_TYPES = {"CREDIT", "CREDIT_CARD"}
# No cartão, ignoramos pagamentos de fatura/transferências; "gasto" = compras.
_EXCLUDE = NON_SPENDING_CATEGORIES | {"Payment", "Pagamento de fatura"}


def card_monthly_breakdown(
    db: Database,
    *,
    today: date | None = None,
    cat_map: dict[str, str] | None = None,
    income: float | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    cur_month = today.isoformat()[:7]
    cat_map = cat_map or {}

    def tr(name: str) -> str:
        return cat_map.get((name or "").lower().strip(), name)

    accounts = list(db.list_accounts())
    acct_type = {a["id"]: (a["type"] or "").upper() for a in accounts}
    acct_name = {a["id"]: (a["name"] or "—") for a in accounts}

    months: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0.0, "n": 0, "cats": defaultdict(float), "cartoes": defaultdict(float)}
    )
    # comerciantes (só realizado/atual) → total, ocorrências, 1º mês visto
    merchants: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0.0, "count": 0, "first": "9999-99"}
    )

    for r in db.list_transactions(limit=100_000):
        if acct_type.get(r["account_id"]) not in CREDIT_TYPES:
            continue
        category = r["category"] or "(sem categoria)"
        amt = float(r["amount"])
        if amt <= 0 or category in _EXCLUDE:  # só compras
            continue
        mk = r["posted_at"][:7]
        m = months[mk]
        m["total"] += amt
        m["n"] += 1
        m["cats"][category] += amt
        m["cartoes"][acct_name.get(r["account_id"], "—")] += amt

        if mk <= cur_month:  # comerciantes só do realizado/atual
            key = _merchant_key(r["raw_description"] or r["description"] or "")
            if key:
                mm = merchants[key]
                mm["total"] += amt
                mm["count"] += 1
                mm["first"] = min(mm["first"], mk)

    meses: list[dict[str, Any]] = []
    gasto_realizado = futuro_parcelado = fatura_atual = 0.0
    idx_atual = 0
    realized_before = [mk for mk in months if mk < cur_month]
    for i, mk in enumerate(sorted(months)):
        m = months[mk]
        tipo = "realizado" if mk < cur_month else ("atual" if mk == cur_month else "futuro")
        if tipo == "futuro":
            futuro_parcelado += m["total"]
        else:
            gasto_realizado += m["total"]
        if tipo == "atual":
            fatura_atual = m["total"]
            idx_atual = i
        cats = sorted(
            ((tr(k), round(v, 2)) for k, v in m["cats"].items() if v > 0),
            key=lambda x: -x[1],
        )[:6]
        cartoes = sorted(
            ((k, round(v, 2)) for k, v in m["cartoes"].items() if v != 0),
            key=lambda x: -x[1],
        )
        meses.append({
            "mes": mk,
            "tipo": tipo,
            "total": round(m["total"], 2),
            "transacoes": m["n"],
            "por_categoria": [{"categoria": c, "total": v} for c, v in cats],
            "por_cartao": [{"cartao": k, "total": v} for k, v in cartoes],
        })

    # -------------------------------------------------------- top comerciantes
    top_comerciantes = [
        {"comerciante": k, "total": round(v["total"], 2), "compras": v["count"]}
        for k, v in sorted(merchants.items(), key=lambda kv: -kv[1]["total"])
    ][:20]

    # -------------------------------------------------------- alertas
    alertas: list[dict[str, Any]] = []
    cur = months.get(cur_month)
    media_faturas = round(mean([months[mk]["total"] for mk in realized_before]), 2) if realized_before else 0.0

    if cur and media_faturas and cur["total"] > media_faturas * 1.1:
        alertas.append({
            "tipo": "fatura_alta",
            "msg": f"Fatura do mês ({_brl(cur['total'])}) está acima da média ({_brl(media_faturas)}).",
        })

    if cur and realized_before:
        for cat, val in cur["cats"].items():
            prev = [months[mk]["cats"].get(cat, 0.0) for mk in realized_before]
            avg_prev = mean(prev) if prev else 0.0
            if val >= 150 and avg_prev >= 80 and val > avg_prev * 1.2:
                cresc = round((val / avg_prev - 1) * 100)
                alertas.append({
                    "tipo": "categoria_alta",
                    "msg": f"{tr(cat)} subiu {cresc}% vs média ({_brl(val)} vs {_brl(avg_prev)}).",
                })

    novos = sorted(
        [k for k, v in merchants.items() if v["first"] == cur_month and v["total"] >= 50],
        key=lambda k: -merchants[k]["total"],
    )[:5]
    for n in novos:
        alertas.append({
            "tipo": "comerciante_novo",
            "msg": f"Novo no cartão este mês: {n} ({_brl(merchants[n]['total'])}).",
        })

    pct_renda = round(fatura_atual / income * 100, 1) if income else None

    return {
        "meses": meses,
        "indice_atual": idx_atual,
        "resumo": {
            "mes_atual": cur_month,
            "fatura_mes_atual": round(fatura_atual, 2),
            "gasto_realizado": round(gasto_realizado, 2),
            "futuro_parcelado": round(futuro_parcelado, 2),
            "media_faturas": media_faturas,
            "pct_renda_comprometida": pct_renda,
        },
        "top_comerciantes": top_comerciantes,
        "alertas": alertas,
    }


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
