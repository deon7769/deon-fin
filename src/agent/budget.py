"""Classificação 50/30/20 das categorias, sem depender da IA.

As categorias vêm do Pluggy em inglês; mapeamos cada uma para um dos três blocos
do orçamento (50% essenciais / 30% desejos / 20% poupança-dívida-financeiro).
Usado pelo dashboard para o "termômetro 50/30/20" — barato e instantâneo.
"""

from __future__ import annotations

from typing import Any

ESSENCIAL = "essencial"
DESEJOS = "desejos"
FINANCEIRO = "financeiro"  # poupança, investimento, dívida e custo financeiro

# Categorias (em minúsculas) → bloco. Default = desejos (conservador).
BUDGET_MAP: dict[str, str] = {
    # --- Essenciais (necessidades) ---
    "services": ESSENCIAL,
    "groceries": ESSENCIAL,
    "gas stations": ESSENCIAL,
    "income taxes": ESSENCIAL,
    "electricity": ESSENCIAL,
    "water": ESSENCIAL,
    "housing": ESSENCIAL,
    "rent": ESSENCIAL,
    "telecommunications": ESSENCIAL,
    "internet": ESSENCIAL,
    "healthcare": ESSENCIAL,
    "hospital clinics and labs": ESSENCIAL,
    "pharmacy": ESSENCIAL,
    "optometry": ESSENCIAL,
    "education": ESSENCIAL,
    "automotive": ESSENCIAL,
    "insurance": ESSENCIAL,
    "vehicle insurance": ESSENCIAL,
    "taxi and ride-hailing": ESSENCIAL,
    "transport": ESSENCIAL,
    "parking": ESSENCIAL,
    "food and drinks": ESSENCIAL,
    "utilities": ESSENCIAL,
    # PT (regras locais)
    "moradia - aluguel": ESSENCIAL,
    "moradia - contas": ESSENCIAL,
    "alimentação - mercado": ESSENCIAL,
    "saúde - farmácia": ESSENCIAL,
    "saúde - plano/consulta": ESSENCIAL,
    "transporte - app": ESSENCIAL,
    "transporte - combustível": ESSENCIAL,
    "transporte - estacionamento": ESSENCIAL,
    "educação": ESSENCIAL,
    # --- Desejos (estilo de vida) ---
    "shopping": DESEJOS,
    "online shopping": DESEJOS,
    "eating out": DESEJOS,
    "food delivery": DESEJOS,
    "clothing": DESEJOS,
    "wellness and fitness": DESEJOS,
    "gyms and fitness centers": DESEJOS,
    "leisure": DESEJOS,
    "tickets": DESEJOS,
    "digital services": DESEJOS,
    "video streaming": DESEJOS,
    "music streaming": DESEJOS,
    "electronics": DESEJOS,
    "bookstore": DESEJOS,
    "houseware": DESEJOS,
    "accomodation": DESEJOS,
    "office supplies": DESEJOS,
    "donations": DESEJOS,
    "travel": DESEJOS,
    "entertainment": DESEJOS,
    # PT
    "alimentação - restaurante": DESEJOS,
    "assinaturas - streaming": DESEJOS,
    "assinaturas - software": DESEJOS,
    "compras - e-commerce": DESEJOS,
    "lazer - cinema/show": DESEJOS,
    # --- Financeiro (poupança / dívida / custo) ---
    "investments": FINANCEIRO,
    "investimentos": FINANCEIRO,
    "savings": FINANCEIRO,
    "credit card fees": FINANCEIRO,
    "interests charged": FINANCEIRO,
    "loans and financing": FINANCEIRO,
    "tax on financial operations": FINANCEIRO,
    "bank fees": FINANCEIRO,
    "financial expenses": FINANCEIRO,
    "tarifas bancárias": FINANCEIRO,
}


def classify(category: str) -> str:
    return BUDGET_MAP.get((category or "").lower().strip(), DESEJOS)


def _period_invested_total(ctx: dict[str, Any]) -> float:
    return float(ctx.get("aportes_periodo_total", ctx.get("investido_total", 0.0)))


def summarize_5030(ctx: dict[str, Any], income: float | None) -> dict[str, Any]:
    """Calcula os blocos 50/30/20 em valores MENSAIS e % da renda.

    - essencial/desejos: soma do gasto médio mensal das categorias de cada bloco.
    - financeiro: gasto médio mensal das categorias de custo financeiro +
      investimento médio mensal (o "20% para poupar/quitar dívida").
    """
    meses = max(1, int(ctx.get("meses_cobertos", 1)))
    blocos = {ESSENCIAL: 0.0, DESEJOS: 0.0, FINANCEIRO: 0.0}

    for item in ctx.get("gasto_por_categoria", []):
        bloco = classify(item.get("categoria", ""))
        blocos[bloco] += float(item.get("media_mensal", 0.0))

    # Investimento médio mensal entra no bloco financeiro/poupança.
    investido_mensal = _period_invested_total(ctx) / meses
    blocos[FINANCEIRO] += investido_mensal

    renda = income if income and income > 0 else float(ctx.get("media_renda_mensal", 0.0))
    metas = {ESSENCIAL: 50, DESEJOS: 30, FINANCEIRO: 20}

    def pct(v: float) -> float:
        return round((v / renda * 100), 1) if renda else 0.0

    return {
        "renda": round(renda, 2),
        "investido_mensal": round(investido_mensal, 2),
        "blocos": {
            nome: {
                "valor_mensal": round(valor, 2),
                "pct_renda": pct(valor),
                "meta_pct": metas[nome],
                "meta_valor": round(renda * metas[nome] / 100, 2),
            }
            for nome, valor in blocos.items()
        },
    }


# ------------------------------------------------------------ Fase 1: tipos de despesa
FIXA, VARIAVEL, PATRIMONIAL = "fixa", "variavel", "patrimonial"

TIPO_MAP: dict[str, str] = {
    # Fixas (recorrentes, valor estável)
    "services": FIXA, "electricity": FIXA, "water": FIXA, "telecommunications": FIXA,
    "internet": FIXA, "education": FIXA, "insurance": FIXA, "vehicle insurance": FIXA,
    "housing": FIXA, "rent": FIXA, "healthcare": FIXA, "hospital clinics and labs": FIXA,
    "income taxes": FIXA, "loans and financing": FIXA, "digital services": FIXA,
    "video streaming": FIXA, "music streaming": FIXA,
    # Patrimoniais (poupança/investimento)
    "investments": PATRIMONIAL,
}  # tudo o que não cair aqui → variável (consumo do dia a dia)


def classify_tipo(category: str) -> str:
    return TIPO_MAP.get((category or "").lower().strip(), VARIAVEL)


def summarize_executivo(
    ctx: dict[str, Any], income: float | None, provisoes_mensal: float = 0.0
) -> dict[str, Any]:
    """KPIs executivos: Saldo Operacional e Patrimonial (valores mensais médios).

    Operacional = Renda − Fixas − Variáveis (sobra antes de poupar).
    Patrimonial = Operacional − Investido − Provisões (livre após poupar/provisionar).
    """
    meses = max(1, int(ctx.get("meses_cobertos", 1)))
    fixas = variaveis = 0.0
    for item in ctx.get("gasto_por_categoria", []):
        t = classify_tipo(item.get("categoria", ""))
        v = float(item.get("media_mensal", 0.0))
        if t == FIXA:
            fixas += v
        elif t == VARIAVEL:
            variaveis += v
    investido_mensal = _period_invested_total(ctx) / meses
    renda = income if income and income > 0 else float(ctx.get("media_renda_mensal", 0.0))
    saldo_operacional = renda - fixas - variaveis
    saldo_patrimonial = saldo_operacional - investido_mensal - provisoes_mensal
    return {
        "renda": round(renda, 2),
        "fixas": round(fixas, 2),
        "variaveis": round(variaveis, 2),
        "investido_mensal": round(investido_mensal, 2),
        "provisoes_mensal": round(provisoes_mensal, 2),
        "saldo_operacional": round(saldo_operacional, 2),
        "saldo_patrimonial": round(saldo_patrimonial, 2),
    }


def summarize_wishlist(items: list[dict[str, Any]], sobra_mensal: float) -> dict[str, Any]:
    """Plano de desejo de economia: quanto guardar/mês por item e viabilidade.

    items: `{nome, valor_alvo, prazo_meses, guardado?, prioridade?}`.
    Ordena por prioridade (menor = mais importante) e calcula o aporte mensal
    necessário, o progresso e se cabe na sobra mensal (cumulativo na ordem).
    """
    ordenados = sorted(
        items or [],
        key=lambda x: (float(x.get("prioridade", 99) or 99), -float(x.get("valor_alvo", 0) or 0)),
    )
    out: list[dict[str, Any]] = []
    acumulado = 0.0
    for it in ordenados:
        alvo = float(it.get("valor_alvo", 0) or 0)
        prazo = max(1, int(it.get("prazo_meses", 12) or 12))
        guardado = float(it.get("guardado", 0) or 0)
        falta = max(0.0, alvo - guardado)
        guardar_mes = round(falta / prazo, 2)
        acumulado += guardar_mes
        out.append({
            "nome": it.get("nome", "—"),
            "valor_alvo": round(alvo, 2),
            "prazo_meses": prazo,
            "guardado": round(guardado, 2),
            "guardar_mes": guardar_mes,
            "progresso_pct": round((guardado / alvo * 100), 1) if alvo else 0.0,
            "cabe_na_sobra": bool(acumulado <= sobra_mensal) if sobra_mensal > 0 else False,
        })
    total_mes = round(sum(i["guardar_mes"] for i in out), 2)
    return {
        "itens": out,
        "total_guardar_mes": total_mes,
        "sobra_mensal": round(sobra_mensal, 2),
        "folga": round(sobra_mensal - total_mes, 2),
    }
