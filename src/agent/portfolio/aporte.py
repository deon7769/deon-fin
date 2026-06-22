from __future__ import annotations

from typing import Any

B3_WHOLE_UNIT_CLASSES = {"acoes_nac", "fii"}
DEFAULT_FRACTIONAL_CLASSES = {"acoes_int", "reit", "cripto"}
NO_SCORE_CLASSES = {"rf", "rf_int", "cripto"}


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


def _nota(ativo: dict[str, Any]) -> float | None:
    value = ativo.get("nota")
    if value is None:
        return None
    return _number(value)


def _target_ratio(value: Any) -> float:
    target = _number(value)
    return target if target <= 1 else target / 100


def _asset_class(ativo: dict[str, Any]) -> str:
    return str(ativo.get("asset_class") or "")


def _is_fractional(ativo: dict[str, Any]) -> bool:
    if "fracionavel" in ativo:
        return bool(ativo.get("fracionavel"))
    return _asset_class(ativo) in DEFAULT_FRACTIONAL_CLASSES


def _is_fixed_income(asset_class: str) -> bool:
    return asset_class in {"rf", "rf_int"}


def _candidate_weight(ativo: dict[str, Any]) -> float:
    nota = _nota(ativo)
    if nota is not None:
        return nota if nota > 0 else 0.0
    asset_class = _asset_class(ativo)
    if asset_class in NO_SCORE_CLASSES:
        return 1.0
    return 0.0


def calcular_aporte(
    aporte: float,
    ativos: list[dict[str, Any]],
    targets: dict[str, float],
) -> dict[str, Any]:
    aporte_rs = _number(aporte)
    patrimonio = sum(_valor_atual(ativo) for ativo in ativos)
    pl_alvo = patrimonio + aporte_rs

    elegiveis = []
    for ativo in ativos:
        asset_class = _asset_class(ativo)
        if _target_ratio(targets.get(asset_class, 0)) <= 0:
            continue
        if _candidate_weight(ativo) <= 0:
            continue
        if _preco(ativo) <= 0 and not _is_fixed_income(asset_class):
            continue
        elegiveis.append(ativo)

    pesos_por_classe: dict[str, float] = {}
    for ativo in elegiveis:
        asset_class = _asset_class(ativo)
        pesos_por_classe[asset_class] = pesos_por_classe.get(asset_class, 0.0) + _candidate_weight(ativo)

    alvos: dict[int, float] = {}
    pesos_alvo: dict[int, float] = {}
    deficits: dict[int, float] = {}
    ideal: dict[int, float] = {}
    for index, ativo in enumerate(elegiveis):
        asset_class = _asset_class(ativo)
        peso_total = pesos_por_classe.get(asset_class, 0.0)
        if peso_total <= 0:
            continue
        alvo_classe = pl_alvo * _target_ratio(targets.get(asset_class, 0))
        peso = _candidate_weight(ativo) / peso_total
        alvo_ativo = alvo_classe * peso
        key = index
        alvos[key] = alvo_ativo
        pesos_alvo[key] = alvo_ativo
        deficits[key] = max(0.0, alvo_ativo - _valor_atual(ativo))

    total_deficit = sum(deficits.values())
    total_peso_alvo = sum(pesos_alvo.values())
    excedente = max(0.0, aporte_rs - total_deficit)
    for index, _ativo in enumerate(elegiveis):
        deficit = deficits.get(index, 0.0)
        if total_deficit >= aporte_rs and total_deficit > 0:
            ideal[index] = aporte_rs * deficit / total_deficit
        elif total_peso_alvo > 0:
            ideal[index] = deficit + excedente * pesos_alvo.get(index, 0.0) / total_peso_alvo
        else:
            ideal[index] = 0.0

    sugestoes_por_index: dict[int, dict[str, float]] = {}
    for index, ativo in enumerate(elegiveis):
        asset_class = _asset_class(ativo)
        if _is_fractional(ativo) or _is_fixed_income(asset_class):
            sugest_rs = _money(ideal.get(index, 0.0))
            preco = _preco(ativo)
            if _is_fixed_income(asset_class) and preco <= 0:
                sugestoes_por_index[index] = {"sugest_rs": 0.0, "sugest_un": 0.0}
                continue
            sugest_un = round(sugest_rs / preco, 6) if preco > 0 else 0.0
            sugestoes_por_index[index] = {"sugest_rs": sugest_rs, "sugest_un": sugest_un}

    whole_indexes = [
        index
        for index, ativo in enumerate(elegiveis)
        if not _is_fractional(ativo) and not _is_fixed_income(_asset_class(ativo))
    ]
    whole_cash = _money(sum(ideal.get(index, 0.0) for index in whole_indexes))
    simulated_values = {
        index: _valor_atual(elegiveis[index]) for index in whole_indexes
    }
    whole_units = {index: 0.0 for index in whole_indexes}
    whole_spend = {index: 0.0 for index in whole_indexes}

    while whole_indexes:
        affordable = [
            index
            for index in whole_indexes
            if _preco(elegiveis[index]) > 0 and _preco(elegiveis[index]) <= whole_cash + 0.0000001
        ]
        if not affordable:
            break
        selected = max(
            affordable,
            key=lambda index: (
                alvos.get(index, 0.0) - simulated_values.get(index, 0.0),
                -_preco(elegiveis[index]),
            ),
        )
        price = _preco(elegiveis[selected])
        whole_units[selected] += 1
        whole_spend[selected] = _money(whole_spend[selected] + price)
        simulated_values[selected] += price
        whole_cash = _money(whole_cash - price)

    for index in whole_indexes:
        sugestoes_por_index[index] = {
            "sugest_rs": _money(whole_spend[index]),
            "sugest_un": whole_units[index],
        }

    sugestoes = []
    alocado = 0.0

    for index, ativo in enumerate(elegiveis):
        suggestion = sugestoes_por_index.get(index, {"sugest_rs": 0.0, "sugest_un": 0.0})
        sugest_rs = _money(suggestion["sugest_rs"])
        preco = _preco(ativo)
        valor_atual = _valor_atual(ativo)
        sugest_un = suggestion["sugest_un"]
        if _is_fixed_income(_asset_class(ativo)) and preco <= 0:
            continue
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
                "nota": _nota(ativo),
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
