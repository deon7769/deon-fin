from __future__ import annotations

from typing import Any


def _money(value: float) -> float:
    return round(float(value), 2)


def _number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _valor_atual(ativo: dict[str, Any]) -> float:
    return _number(ativo.get("valor_atual", ativo.get("current_value")))


def _preco(ativo: dict[str, Any]) -> float:
    return _number(ativo.get("preco", ativo.get("unit_price")))


def _target_ratio(value: Any) -> float:
    target = _number(value)
    return target if target <= 1 else target / 100


def calcular_aporte(
    aporte: float,
    ativos: list[dict[str, Any]],
    targets: dict[str, float],
) -> dict[str, Any]:
    aporte_rs = _number(aporte)
    patrimonio = sum(_valor_atual(ativo) for ativo in ativos)
    pl_alvo = patrimonio + aporte_rs

    elegiveis = [
        ativo
        for ativo in ativos
        if _number(ativo.get("nota")) > 0 and _preco(ativo) > 0
    ]

    notas_por_classe: dict[str, float] = {}
    for ativo in elegiveis:
        asset_class = str(ativo.get("asset_class") or "")
        notas_por_classe[asset_class] = notas_por_classe.get(asset_class, 0.0) + _number(ativo.get("nota"))

    alvos: dict[int, float] = {}
    pesos_alvo: dict[int, float] = {}
    deficits: dict[int, float] = {}
    for ativo in elegiveis:
        asset_class = str(ativo.get("asset_class") or "")
        nota_total = notas_por_classe.get(asset_class, 0.0)
        if nota_total <= 0:
            continue
        alvo_classe = pl_alvo * _target_ratio(targets.get(asset_class, 0))
        peso = _number(ativo.get("nota")) / nota_total
        alvo_ativo = alvo_classe * peso
        key = id(ativo)
        alvos[key] = alvo_ativo
        pesos_alvo[key] = alvo_ativo
        deficits[key] = max(0.0, alvo_ativo - _valor_atual(ativo))

    total_deficit = sum(deficits.values())
    total_peso_alvo = sum(pesos_alvo.values())
    excedente = max(0.0, aporte_rs - total_deficit)
    sugestoes = []
    alocado = 0.0

    for ativo in elegiveis:
        key = id(ativo)
        deficit = deficits.get(key, 0.0)
        if total_deficit >= aporte_rs and total_deficit > 0:
            sugest_rs = aporte_rs * deficit / total_deficit
        elif total_peso_alvo > 0:
            sugest_rs = deficit + excedente * pesos_alvo.get(key, 0.0) / total_peso_alvo
        else:
            sugest_rs = 0.0

        sugest_rs = _money(sugest_rs)
        preco = _preco(ativo)
        valor_atual = _valor_atual(ativo)
        sugest_un = round(sugest_rs / preco, 6) if preco > 0 else 0.0
        total_apos_aporte_pct = (
            _money((valor_atual + sugest_rs) / pl_alvo * 100) if pl_alvo > 0 else 0.0
        )
        alocado += sugest_rs
        sugestoes.append(
            {
                "id": ativo.get("id"),
                "tipo": ativo.get("asset_class"),
                "asset_class": ativo.get("asset_class"),
                "ticker": ativo.get("ticker"),
                "valor_atual": _money(valor_atual),
                "preco": _money(preco),
                "nota": _number(ativo.get("nota")),
                "sugest_rs": sugest_rs,
                "sugest_un": sugest_un,
                "total_apos_aporte_pct": total_apos_aporte_pct,
            }
        )

    return {
        "patrimonio": _money(patrimonio),
        "pl_alvo": _money(pl_alvo),
        "sugestoes": sugestoes,
        "troco": _money(max(0.0, aporte_rs - alocado)),
    }
