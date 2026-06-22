from __future__ import annotations

import pytest


def _calcular_aporte():
    try:
        from src.agent.portfolio.aporte import calcular_aporte
    except ModuleNotFoundError as exc:
        pytest.fail(f"calcular_aporte is not implemented yet: {exc}")
    return calcular_aporte


def test_sem_carteira_classe_internacional_distribui_aporte_por_notas():
    calcular_aporte = _calcular_aporte()
    ativos = [
        {
            "id": 1,
            "asset_class": "acoes_int",
            "ticker": "INT2",
            "nota": 2,
            "valor_atual": 0,
            "preco": 10,
            "fracionavel": True,
        },
        {
            "id": 2,
            "asset_class": "acoes_int",
            "ticker": "INT6",
            "nota": 6,
            "valor_atual": 0,
            "preco": 100,
            "fracionavel": True,
        },
        {
            "id": 3,
            "asset_class": "acoes_int",
            "ticker": "INT10",
            "nota": 10,
            "valor_atual": 0,
            "preco": 250,
            "fracionavel": True,
        },
    ]

    result = calcular_aporte(1000, ativos, {"acoes_int": 100})

    assert result["patrimonio"] == 0.0
    assert result["pl_alvo"] == 1000.0
    assert result["troco"] == pytest.approx(0.0, abs=0.01)

    sugestoes = {item["ticker"]: item for item in result["sugestoes"]}
    assert list(sugestoes) == ["INT2", "INT6", "INT10"]

    expected_rs = {"INT2": 111.05, "INT6": 333.15, "INT10": 555.26}
    for ativo in ativos:
        sugestao = sugestoes[ativo["ticker"]]
        assert sugestao["sugest_rs"] == pytest.approx(expected_rs[ativo["ticker"]], abs=0.5)
        assert sugestao["sugest_un"] == pytest.approx(
            sugestao["sugest_rs"] / ativo["preco"],
            abs=0.0001,
        )
        assert sugestao["total_apos_aporte_pct"] == pytest.approx(
            (ativo["valor_atual"] + sugestao["sugest_rs"]) / result["pl_alvo"] * 100,
            abs=0.01,
        )

    assert sum(item["sugest_rs"] for item in sugestoes.values()) == pytest.approx(1000.0, abs=0.01)
    assert sum(item["total_apos_aporte_pct"] for item in sugestoes.values()) == pytest.approx(100.0, abs=0.01)
