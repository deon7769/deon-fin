from __future__ import annotations

import pytest

from src.agent.simulator import simular_price
from src.agent.simulators import (
    aluguel_vs_financiamento,
    amortizacao_completa,
    cdb,
    juros_compostos,
    marcacao_mercado,
    pix_parcelado,
    renda_retiradas,
)


def test_juros_compostos_matches_spec_fixture():
    result = juros_compostos(
        valor_inicial=500,
        valor_mensal=500,
        taxa=8,
        taxa_periodo="anual",
        periodo=1,
        periodo_unidade="anos",
    )

    assert result["resumo"]["valor_final"] == pytest.approx(6756.94, abs=0.01)
    assert result["resumo"]["total_investido"] == 6500.0
    assert result["resumo"]["total_juros"] == pytest.approx(256.94, abs=0.01)
    assert len(result["serie"]) == 12
    assert result["serie"][0]["juros"] == pytest.approx(3.22, abs=0.01)
    assert result["serie"][0]["total_acumulado"] == pytest.approx(503.22, abs=0.01)


def test_juros_compostos_zero_rate_is_linear():
    result = juros_compostos(
        valor_inicial=1000,
        valor_mensal=100,
        taxa=0,
        taxa_periodo="mensal",
        periodo=6,
        periodo_unidade="meses",
    )

    assert result["resumo"] == {
        "valor_final": 1600.0,
        "total_investido": 1600.0,
        "total_juros": 0.0,
    }
    assert result["serie"][-1]["total_acumulado"] == 1500.0


def test_renda_retiradas_matches_spec_fixture():
    result = renda_retiradas(
        valor_inicial=200000,
        retirada_mensal=800,
        taxa=13,
        taxa_periodo="anual",
        periodo=10,
        periodo_unidade="anos",
    )

    assert result["resumo"]["valor_final"] == pytest.approx(491780.23, abs=0.01)
    assert result["resumo"]["total_retirado"] == 96000.0
    assert result["resumo"]["total_juros"] == pytest.approx(387780.23, abs=0.01)
    assert result["resumo"]["sustentavel"] is True
    assert result["resumo"]["meses_ate_zerar"] is None
    assert result["serie"][0]["juros"] == pytest.approx(2047.37, abs=0.01)


def test_pix_parcelado_direct_and_reverse_modes():
    direct = pix_parcelado(
        valor_pix=1000,
        n_parcelas=4,
        juros_mensal_pct=2,
    )

    assert direct["resumo"]["valor_parcela"] == pytest.approx(262.62, abs=0.01)
    assert direct["resumo"]["total_pago"] == pytest.approx(1050.49, abs=0.01)
    assert direct["resumo"]["total_juros"] == pytest.approx(50.49, abs=0.01)
    assert direct["resumo"]["cet_mensal_pct"] == pytest.approx(2.0, abs=0.01)
    assert direct["resumo"]["acrescimo_pct"] == pytest.approx(5.05, abs=0.01)

    reverse = pix_parcelado(
        valor_pix=1000,
        n_parcelas=4,
        juros_mensal_pct=0,
        incluir_valor_parcela=True,
        valor_parcela=direct["resumo"]["valor_parcela"],
    )

    assert reverse["resumo"]["cet_mensal_pct"] == pytest.approx(2.0, abs=0.05)
    assert reverse["resumo"]["total_pago"] == pytest.approx(direct["resumo"]["total_pago"], abs=0.05)


def test_cdb_applies_regressive_income_tax():
    result = cdb(
        investimento_inicial=1000,
        investimento_mensal=0,
        cdi_pct=100,
        tempo=1,
        tempo_unidade="anos",
        cdi_aa=12,
    )

    assert result["resumo"]["valor_bruto"] == pytest.approx(1120.0, abs=0.01)
    assert result["resumo"]["total_investido"] == 1000.0
    assert result["resumo"]["juros_bruto"] == pytest.approx(120.0, abs=0.01)
    assert result["resumo"]["aliquota_ir_pct"] == 17.5
    assert result["resumo"]["ir"] == pytest.approx(21.0, abs=0.01)
    assert result["resumo"]["valor_liquido"] == pytest.approx(1099.0, abs=0.01)


def test_marcacao_mercado_returns_target_rate_and_offer_comparison():
    result = marcacao_mercado(
        tipo="prefixado",
        data_aplicacao="2024-01-01",
        data_vencimento="2026-01-01",
        data_hoje="2025-01-01",
        valor_investido=10000,
        valor_atual_bruto=10500,
        rentabilidade_contratada_aa=10,
        isento_ir=False,
        rentabilidade_nova_oferta_aa=12,
    )

    assert result["resumo"]["tipo"] == "prefixado"
    assert result["resumo"]["caixa_hoje"] < 10500
    assert result["resumo"]["tir_implicita_aa"] > 0
    assert result["resumo"]["agio_desagio"] == pytest.approx(
        result["resumo"]["valor_atual_bruto"] - result["resumo"]["valor_na_curva"],
        abs=0.01,
    )
    assert isinstance(result["resumo"]["comparativo_oferta"]["vale_a_pena"], bool)


def test_amortizacao_completa_generates_price_schedule_and_extra_payment_case():
    result = amortizacao_completa(
        valor_emprestimo=12000,
        data_inicio="2026-01-01",
        sistema="price",
        taxa=12,
        taxa_periodo="anual",
        n_parcelas=12,
        correcao="nenhuma",
        aportes_extra=[{"mes": 1, "valor": 1000}],
        modo_aporte="reduzir_prazo",
        seguros_taxas_mensal=10,
    )

    assert result["resumo"]["parcela_inicial"] == pytest.approx(simular_price(12000, 12, 12)["parcela"] + 10, abs=0.01)
    assert result["resumo"]["meses"] < 12
    assert result["resumo"]["com_aporte"]["meses_economizados"] > 0
    assert result["serie"][0]["seguro"] == 10.0
    assert result["serie"][-1]["saldo"] == 0.0


def test_aluguel_vs_financiamento_returns_series_and_breakeven():
    result = aluguel_vs_financiamento(
        valor_imovel=300000,
        entrada=60000,
        custos_financiamento=10000,
        prazo_meses=24,
        taxa_aa=10,
        sistema="price",
        aluguel_mensal=1800,
        reajuste_aluguel_aa=5,
        rendimento_investimento_aa=8,
        valorizacao_imovel_aa=4,
    )

    assert result["resumo"]["patrimonio_final_comprar"] > 0
    assert result["resumo"]["patrimonio_final_alugar"] > 0
    assert result["resumo"]["vantagem"] in {"comprar", "alugar"}
    assert "breakeven_mes" in result["resumo"]
    assert len(result["serie"]) == 24
