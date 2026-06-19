"""Simulador de compras (carro / imóvel).

Compara duas estratégias para uma compra:
1. **Financiar** — entrada agora + parcelas. Suporta tabela Price (parcela fixa)
   e SAC (amortização constante, parcela decrescente — comum em imóvel).
2. **Juntar à vista** — guardar a sobra mensal até ter o valor total (com ou sem
   rendimento), e comprar sem juros.

Funções puras, sem dependência de banco — fáceis de testar.
"""

from __future__ import annotations

from typing import Any


def _taxa_mensal(juros_aa: float) -> float:
    """Converte taxa anual efetiva (%) em taxa mensal efetiva (fração)."""
    return (1 + juros_aa / 100) ** (1 / 12) - 1


def simular_price(valor_financiado: float, prazo_meses: int, juros_aa: float) -> dict[str, Any]:
    i = _taxa_mensal(juros_aa)
    n = max(1, int(prazo_meses))
    if i <= 0:
        parcela = valor_financiado / n
    else:
        parcela = valor_financiado * i / (1 - (1 + i) ** (-n))
    total = parcela * n
    return {
        "sistema": "price",
        "parcela": round(parcela, 2),
        "total_parcelas": round(total, 2),
        "total_juros": round(total - valor_financiado, 2),
    }


def simular_sac(valor_financiado: float, prazo_meses: int, juros_aa: float) -> dict[str, Any]:
    i = _taxa_mensal(juros_aa)
    n = max(1, int(prazo_meses))
    amortizacao = valor_financiado / n
    primeira = amortizacao + valor_financiado * i
    ultima = amortizacao + amortizacao * i
    total_juros = i * valor_financiado * (n + 1) / 2  # soma PA dos juros
    return {
        "sistema": "sac",
        "primeira_parcela": round(primeira, 2),
        "ultima_parcela": round(ultima, 2),
        "total_parcelas": round(valor_financiado + total_juros, 2),
        "total_juros": round(total_juros, 2),
    }


def simular_consorcio(preco: float, prazo_meses: int, taxa_adm_pct: float = 18.0) -> dict[str, Any]:
    """Consórcio: sem juros, mas com taxa de administração sobre a carta (simplificado).

    Não há uso imediato do bem até a contemplação — modelado só no custo.
    """
    n = max(1, int(prazo_meses))
    total = preco * (1 + taxa_adm_pct / 100)
    return {
        "sistema": "consorcio",
        "taxa_adm_pct": taxa_adm_pct,
        "parcela": round(total / n, 2),
        "total_parcelas": round(total, 2),
        "custo_taxa_adm": round(total - preco, 2),
    }


def _payoff(saldo: float, i: float, parcela: float, teto: int = 1200) -> dict[str, Any] | None:
    """Quita um saldo pagando `parcela` fixa/mês a juros `i`. None se nunca quita."""
    juros_pagos = 0.0
    s = saldo
    for m in range(1, teto + 1):
        juros = s * i
        amort = parcela - juros
        if amort <= 0:
            return None  # parcela não cobre os juros
        juros_pagos += juros
        s -= amort
        if s <= 0:
            return {"meses": m, "juros_pagos": round(juros_pagos, 2)}
    return None


def simular_amortizacao(
    saldo: float, juros_aa: float, parcela: float, aporte_extra: float = 0.0
) -> dict[str, Any]:
    """Compara quitar um financiamento com a parcela atual vs. com aporte extra/mês."""
    i = _taxa_mensal(juros_aa)
    base = _payoff(saldo, i, parcela)
    com = _payoff(saldo, i, parcela + aporte_extra) if aporte_extra > 0 else base
    economia = None
    if base and com:
        economia = round(base["juros_pagos"] - com["juros_pagos"], 2)
    return {
        "saldo": round(saldo, 2),
        "parcela_atual": round(parcela, 2),
        "aporte_extra": round(aporte_extra, 2),
        "sem_extra": base,
        "com_extra": com,
        "meses_economizados": (base["meses"] - com["meses"]) if (base and com) else None,
        "juros_economizados": economia,
    }


def meses_para_juntar(
    alvo: float, aporte_mensal: float, rendimento_aa: float = 0.0, teto: int = 1200
) -> int | None:
    """Quantos meses para acumular `alvo` guardando `aporte_mensal` (com rendimento)."""
    if aporte_mensal <= 0 or alvo <= 0:
        return None
    r = _taxa_mensal(rendimento_aa)
    saldo = 0.0
    for m in range(1, teto + 1):
        saldo = saldo * (1 + r) + aporte_mensal
        if saldo >= alvo:
            return m
    return None  # não atinge dentro do teto


def simular_compra(
    *,
    preco: float,
    entrada: float = 0.0,
    prazo_meses: int = 48,
    juros_aa: float = 18.0,
    sobra_mensal: float = 0.0,
    rendimento_aa: float = 0.0,
    taxa_adm_consorcio: float = 18.0,
) -> dict[str, Any]:
    """Compara financiar (Price + SAC), consórcio e juntar à vista."""
    preco = float(preco)
    entrada = min(float(entrada), preco)
    valor_financiado = max(0.0, preco - entrada)

    price = simular_price(valor_financiado, prazo_meses, juros_aa)
    sac = simular_sac(valor_financiado, prazo_meses, juros_aa)
    consorcio = simular_consorcio(preco, prazo_meses, taxa_adm_consorcio)
    custo_financiar_price = round(entrada + price["total_parcelas"], 2)
    custo_financiar_sac = round(entrada + sac["total_parcelas"], 2)

    meses_juntar = meses_para_juntar(preco, sobra_mensal, rendimento_aa)
    juntar = {
        "aporte_mensal": round(sobra_mensal, 2),
        "rendimento_aa": rendimento_aa,
        "meses_para_juntar": meses_juntar,
        "anos_para_juntar": round(meses_juntar / 12, 1) if meses_juntar else None,
        "custo_total": round(preco, 2),  # à vista: sem juros
    }

    # Economia de juros ao juntar à vista vs financiar (Price).
    economia_vs_price = round(custo_financiar_price - preco, 2)

    return {
        "entrada": round(entrada, 2),
        "valor_financiado": round(valor_financiado, 2),
        "financiar": {
            "price": price,
            "sac": sac,
            "custo_total_price": custo_financiar_price,
            "custo_total_sac": custo_financiar_sac,
        },
        "consorcio": consorcio,
        "juntar_a_vista": juntar,
        "economia_juntando_vs_price": economia_vs_price,
    }
