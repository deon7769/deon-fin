from __future__ import annotations

from src.agent.budget import summarize_wishlist
from src.agent.simulator import (
    meses_para_juntar,
    simular_amortizacao,
    simular_compra,
    simular_consorcio,
    simular_price,
    simular_sac,
)


def test_consorcio_sem_juros_com_taxa_adm():
    c = simular_consorcio(60000, 60, 18)
    assert c["total_parcelas"] == 70800.0          # 60000 * 1.18
    assert c["parcela"] == 1180.0                  # 70800 / 60
    assert c["custo_taxa_adm"] == 10800.0


def test_amortizacao_extra_reduz_prazo_e_juros():
    r = simular_amortizacao(saldo=30000, juros_aa=12, parcela=1000, aporte_extra=500)
    assert r["sem_extra"]["meses"] > r["com_extra"]["meses"]
    assert r["meses_economizados"] > 0
    assert r["juros_economizados"] > 0


def test_simular_compra_inclui_consorcio():
    r = simular_compra(preco=50000, entrada=0, prazo_meses=48, juros_aa=24)
    assert r["consorcio"]["sistema"] == "consorcio"
    assert r["consorcio"]["total_parcelas"] > 50000


def test_price_juros_zero_e_positivo():
    # juros 0 → parcela = principal/n
    p0 = simular_price(12000, 12, 0)
    assert p0["parcela"] == 1000.0
    assert p0["total_juros"] == 0.0
    # juros positivo → parcela > principal/n e há juros
    p = simular_price(12000, 12, 20)
    assert p["parcela"] > 1000.0
    assert p["total_juros"] > 0


def test_sac_parcela_decrescente():
    s = simular_sac(12000, 12, 20)
    assert s["primeira_parcela"] > s["ultima_parcela"]  # SAC decresce
    assert s["total_juros"] > 0


def test_meses_para_juntar():
    assert meses_para_juntar(1000, 0) is None        # sem aporte
    assert meses_para_juntar(1000, 100, 0) == 10     # sem rendimento
    # com rendimento, junta em menos ou igual meses
    assert meses_para_juntar(1000, 100, 12) <= 10


def test_simular_compra_compara_estrategias():
    r = simular_compra(preco=50000, entrada=10000, prazo_meses=48, juros_aa=24,
                        sobra_mensal=2000, rendimento_aa=0)
    assert r["valor_financiado"] == 40000.0
    assert r["financiar"]["custo_total_price"] > 50000  # paga mais que à vista
    assert r["juntar_a_vista"]["meses_para_juntar"] == 25  # 50000/2000
    assert r["economia_juntando_vs_price"] > 0


def test_wishlist_ordena_e_calcula():
    items = [
        {"nome": "Viagem", "valor_alvo": 6000, "prazo_meses": 12, "prioridade": 2},
        {"nome": "Notebook", "valor_alvo": 4000, "prazo_meses": 8, "guardado": 1000, "prioridade": 1},
    ]
    w = summarize_wishlist(items, sobra_mensal=1000)
    # prioridade 1 vem primeiro
    assert w["itens"][0]["nome"] == "Notebook"
    # notebook: (4000-1000)/8 = 375/mês
    assert w["itens"][0]["guardar_mes"] == 375.0
    assert w["itens"][0]["progresso_pct"] == 25.0
    assert w["total_guardar_mes"] == 875.0   # 375 + 500
    assert w["folga"] == 125.0
