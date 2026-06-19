from __future__ import annotations

from datetime import date
from src.agent.context import build_financial_context

def test_family_profile_calculation_and_injection(tmp_db):
    # Setup dummy database entries to satisfy basic query
    # build_financial_context requires some data to compute months_covered
    profile = {
        "receitas": [
            { "membro": "Membro A", "valor": 5000.0 },
            { "membro": "Membro B", "valor": 3000.0 }
        ],
        "patrimonio": {
            "imoveis": [
                {
                    "nome": "Casa Teste",
                    "valor_mercado": 200000.0,
                    "saldo_devedor": 50000.0,
                    "taxa_juros_anual": 5.0,
                    "prazo_restante_meses": 60,
                    "aluguel_receita": 1000.0,
                    "custos": {
                        "financiamento": 400.0,
                        "condominio": 100.0
                    }
                }
            ],
            "investimentos_caixa": [
                { "local": "Banco X", "valor": 10000.0, "aporte_mensal_recorrente": 200.0 }
            ]
        },
        "provisoes": [
            { "nome": "Seguro", "mensal": 100.0, "alvo": 1200.0 }
        ],
        "metas": [
            { "nome": "Reserva", "alvo": 20000.0, "atual": 10000.0 }
        ]
    }

    ctx = build_financial_context(
        tmp_db,
        today=date(2026, 6, 10),
        family_profile=profile
    ).to_dict()

    assert ctx["perfil_familiar"] is not None
    pf = ctx["perfil_familiar"]

    # Rendas
    assert len(pf["receitas"]) == 2
    assert pf["receitas"][0]["valor"] == 5000.0

    # Patrimônio Consolidado
    # Ativos = 200k (imóvel) + 10k (caixa) = 210k
    # Passivos = 50k (financiamento)
    # Líquido = 160k
    pat = pf["patrimonio_consolidado"]
    assert pat["total_ativos"] == 210000.0
    assert pat["total_passivos"] == 50000.0
    assert pat["patrimonio_liquido"] == 160000.0
    assert pat["detalhe_ativos"]["imoveis"] == 200000.0
    assert pat["detalhe_ativos"]["caixas_investimentos"] == 10000.0

    # Fluxo Imóveis
    assert len(pf["fluxo_imoveis"]) == 1
    casa = pf["fluxo_imoveis"][0]
    assert casa["nome"] == "Casa Teste"
    assert casa["receita"] == 1000.0
    assert casa["custo_total"] == 500.0
    assert casa["resultado"] == 500.0

    # Investimentos/Caixa
    assert len(pf["investimentos_caixa"]) == 1
    assert pf["investimentos_caixa"][0]["local"] == "Banco X"

    # Provisões
    assert len(pf["provisoes"]) == 1
    assert pf["provisoes_total_mensal"] == 100.0

    # Metas
    assert len(pf["metas"]) == 1
    assert pf["metas"][0]["nome"] == "Reserva"

def test_family_profile_none(tmp_db):
    ctx = build_financial_context(
        tmp_db,
        today=date(2026, 6, 10),
        family_profile=None
    ).to_dict()
    assert ctx["perfil_familiar"] is None
