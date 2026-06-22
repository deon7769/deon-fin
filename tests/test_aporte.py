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


def test_sem_carteira_classe_internacional_escala_aporte_maior():
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

    result = calcular_aporte(10000, ativos, {"acoes_int": 100})

    sugestoes = {item["ticker"]: item for item in result["sugestoes"]}
    assert sugestoes["INT2"]["sugest_rs"] == pytest.approx(1111.11, abs=0.01)
    assert sugestoes["INT6"]["sugest_rs"] == pytest.approx(3333.33, abs=0.01)
    assert sugestoes["INT10"]["sugest_rs"] == pytest.approx(5555.56, abs=0.01)
    assert result["troco"] == pytest.approx(0.0, abs=0.01)


def test_com_carteira_classe_internacional_aporta_proporcional_ao_deficit():
    calcular_aporte = _calcular_aporte()
    ativos = [
        {
            "id": 1,
            "asset_class": "acoes_int",
            "ticker": "ACNB",
            "nota": 8,
            "valor_atual": 0,
            "preco": 12.5,
            "fracionavel": True,
        },
        {
            "id": 2,
            "asset_class": "acoes_int",
            "ticker": "BMI",
            "nota": 4,
            "valor_atual": 0,
            "preco": 25,
            "fracionavel": True,
        },
        {
            "id": 3,
            "asset_class": "acoes_int",
            "ticker": "MET",
            "nota": 2,
            "valor_atual": 1111.10,
            "preco": 50,
            "fracionavel": True,
        },
        {
            "id": 4,
            "asset_class": "acoes_int",
            "ticker": "OSBC",
            "nota": 6,
            "valor_atual": 3333.34,
            "preco": 100,
            "fracionavel": True,
        },
        {
            "id": 5,
            "asset_class": "acoes_int",
            "ticker": "WTBA",
            "nota": 10,
            "valor_atual": 5555.56,
            "preco": 128.34,
            "fracionavel": True,
        },
    ]

    result = calcular_aporte(10000, ativos, {"acoes_int": 100})

    sugestoes = {item["ticker"]: item for item in result["sugestoes"]}
    expected = {
        "ACNB": 5333.33,
        "BMI": 2666.67,
        "MET": 222.24,
        "OSBC": 666.66,
        "WTBA": 1111.11,
    }
    for ticker, value in expected.items():
        assert sugestoes[ticker]["sugest_rs"] == pytest.approx(value, abs=0.02)
    assert sum(item["sugest_rs"] for item in sugestoes.values()) == pytest.approx(10000, abs=0.01)
    assert result["troco"] == pytest.approx(0.0, abs=0.01)


def test_cota_inteira_pula_ativo_mais_caro_que_o_caixa_e_informa_troco():
    calcular_aporte = _calcular_aporte()
    ativos = [
        {
            "id": 1,
            "asset_class": "acoes_nac",
            "ticker": "CARA3",
            "nota": 10,
            "valor_atual": 0,
            "preco": 128,
            "fracionavel": False,
        },
        {
            "id": 2,
            "asset_class": "acoes_nac",
            "ticker": "MEDIA3",
            "nota": 6,
            "valor_atual": 0,
            "preco": 40,
            "fracionavel": False,
        },
        {
            "id": 3,
            "asset_class": "acoes_nac",
            "ticker": "BARATA3",
            "nota": 2,
            "valor_atual": 0,
            "preco": 35,
            "fracionavel": False,
        },
    ]

    result = calcular_aporte(100, ativos, {"acoes_nac": 100})

    sugestoes = {item["ticker"]: item for item in result["sugestoes"]}
    assert sugestoes["CARA3"]["sugest_rs"] == 0.0
    assert sugestoes["CARA3"]["sugest_un"] == 0.0
    assert sugestoes["MEDIA3"]["sugest_rs"] == 40.0
    assert sugestoes["MEDIA3"]["sugest_un"] == 1.0
    assert sugestoes["BARATA3"]["sugest_rs"] == 35.0
    assert sugestoes["BARATA3"]["sugest_un"] == 1.0
    assert result["troco"] == 25.0


def test_aporte_menor_que_menor_cota_vira_troco():
    calcular_aporte = _calcular_aporte()
    ativos = [
        {
            "id": 1,
            "asset_class": "fii",
            "ticker": "FIIA11",
            "nota": 10,
            "valor_atual": 0,
            "preco": 90,
            "fracionavel": False,
        }
    ]

    result = calcular_aporte(50, ativos, {"fii": 100})

    assert result["sugestoes"][0]["sugest_rs"] == 0.0
    assert result["sugestoes"][0]["sugest_un"] == 0.0
    assert result["troco"] == 50.0
