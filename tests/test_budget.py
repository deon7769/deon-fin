from __future__ import annotations

from src.agent.budget import (
    DESEJOS,
    ESSENCIAL,
    FINANCEIRO,
    classify,
    classify_tipo,
    summarize_5030,
    summarize_executivo,
)


def test_classify_tipo():
    assert classify_tipo("Services") == "fixa"
    assert classify_tipo("Groceries") == "variavel"
    assert classify_tipo("Investments") == "patrimonial"
    assert classify_tipo("Categoria nova") == "variavel"  # default


def test_summarize_executivo():
    ctx = {
        "meses_cobertos": 1,
        "investido_total": 1000.0,
        "media_renda_mensal": 0.0,
        "gasto_por_categoria": [
            {"categoria": "Services", "media_mensal": 2000.0},   # fixa
            {"categoria": "Groceries", "media_mensal": 1500.0},  # variavel
        ],
    }
    ex = summarize_executivo(ctx, income=10000, provisoes_mensal=500)
    assert ex["fixas"] == 2000.0
    assert ex["variaveis"] == 1500.0
    assert ex["saldo_operacional"] == 6500.0          # 10000 - 2000 - 1500
    assert ex["saldo_patrimonial"] == 5000.0          # 6500 - 1000 investido - 500 provisões


def test_classify_categorias_reais():
    assert classify("Groceries") == ESSENCIAL
    assert classify("gas stations") == ESSENCIAL
    assert classify("Shopping") == DESEJOS
    assert classify("Investments") == FINANCEIRO
    assert classify("Credit card fees") == FINANCEIRO
    assert classify("Categoria desconhecida") == DESEJOS  # fallback conservador


def test_summarize_5030_calcula_blocos_e_pct():
    ctx = {
        "meses_cobertos": 2,
        "investido_total": 2000.0,  # 1000/mês entra no bloco financeiro
        "media_renda_mensal": 0.0,
        "gasto_por_categoria": [
            {"categoria": "Groceries", "media_mensal": 2000.0},   # essencial
            {"categoria": "Shopping", "media_mensal": 1500.0},    # desejos
            {"categoria": "Credit card fees", "media_mensal": 100.0},  # financeiro
        ],
    }
    out = summarize_5030(ctx, income=10000)
    assert out["renda"] == 10000
    b = out["blocos"]
    assert b["essencial"]["valor_mensal"] == 2000.0
    assert b["desejos"]["valor_mensal"] == 1500.0
    assert b["financeiro"]["valor_mensal"] == 1100.0  # 100 custo + 1000 investido
    assert b["essencial"]["pct_renda"] == 20.0
    assert b["essencial"]["meta_pct"] == 50


def test_summarize_5030_uses_period_aportes_when_portfolio_total_is_available():
    ctx = {
        "meses_cobertos": 1,
        "investido_total": 10000.0,
        "aportes_periodo_total": 1000.0,
        "media_renda_mensal": 0.0,
        "gasto_por_categoria": [],
    }

    out = summarize_5030(ctx, income=5000)

    assert out["blocos"]["financeiro"]["valor_mensal"] == 1000.0


def test_summarize_5030_sem_renda_usa_media_detectada():
    ctx = {
        "meses_cobertos": 1,
        "investido_total": 0.0,
        "media_renda_mensal": 5000.0,
        "gasto_por_categoria": [{"categoria": "Groceries", "media_mensal": 1000.0}],
    }
    out = summarize_5030(ctx, income=None)
    assert out["renda"] == 5000.0
    assert out["blocos"]["essencial"]["pct_renda"] == 20.0
