from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.storage import Database
from src.web.app import create_app, get_db, get_pluggy


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("src.web.app._background_sync", lambda *a, **kw: None)
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.mnt.load_family_profile",
        lambda: None,
    )

    db = Database(tmp_path / "test.db")
    app = create_app()

    def _override_db():
        yield db

    class FakePluggy:
        def close(self):
            return None

    def _override_pluggy():
        yield FakePluggy()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    try:
        yield TestClient(app)
    finally:
        db.close()


def test_juros_compostos_endpoint_returns_common_contract(client):
    response = client.post(
        "/api/sim/juros-compostos",
        json={
            "valor_inicial": 500,
            "valor_mensal": 500,
            "taxa": 8,
            "taxa_periodo": "anual",
            "periodo": 1,
            "periodo_unidade": "anos",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["resumo"]["valor_final"] == pytest.approx(6756.94, abs=0.01)
    assert data["resumo"]["total_investido"] == 6500.0
    assert data["resumo"]["total_juros"] == pytest.approx(256.94, abs=0.01)
    assert len(data["serie"]) == 12


@pytest.mark.parametrize(
    ("path", "payload", "expected_key"),
    [
        (
            "/api/sim/renda",
            {
                "valor_inicial": 200000,
                "retirada_mensal": 800,
                "taxa": 13,
                "taxa_periodo": "anual",
                "periodo": 10,
                "periodo_unidade": "anos",
            },
            "valor_final",
        ),
        (
            "/api/sim/pix-parcelado",
            {"valor_pix": 1000, "n_parcelas": 4, "juros_mensal_pct": 2},
            "valor_parcela",
        ),
        (
            "/api/sim/cdb",
            {
                "investimento_inicial": 1000,
                "investimento_mensal": 0,
                "cdi_pct": 100,
                "tempo": 1,
                "tempo_unidade": "anos",
                "cdi_aa": 12,
            },
            "valor_liquido",
        ),
        (
            "/api/sim/marcacao-mercado",
            {
                "tipo": "prefixado",
                "data_aplicacao": "2024-01-01",
                "data_vencimento": "2026-01-01",
                "data_hoje": "2025-01-01",
                "valor_investido": 10000,
                "valor_atual_bruto": 10500,
                "rentabilidade_contratada_aa": 10,
                "isento_ir": False,
                "rentabilidade_nova_oferta_aa": 12,
            },
            "tir_implicita_aa",
        ),
        (
            "/api/sim/amortizacao",
            {
                "valor_emprestimo": 12000,
                "data_inicio": "2026-01-01",
                "sistema": "price",
                "taxa": 12,
                "taxa_periodo": "anual",
                "n_parcelas": 12,
                "correcao": "nenhuma",
                "aportes_extra": [{"mes": 1, "valor": 1000}],
                "modo_aporte": "reduzir_prazo",
            },
            "parcela_inicial",
        ),
        (
            "/api/sim/imovel",
            {
                "valor_imovel": 300000,
                "entrada": 60000,
                "custos_financiamento": 10000,
                "prazo_meses": 24,
                "taxa_aa": 10,
                "sistema": "price",
                "aluguel_mensal": 1800,
                "reajuste_aluguel_aa": 5,
                "rendimento_investimento_aa": 8,
                "valorizacao_imovel_aa": 4,
            },
            "vantagem",
        ),
    ],
)
def test_additional_simulation_endpoints_return_resumo(client, path, payload, expected_key):
    response = client.post(path, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert expected_key in data["resumo"]


def test_legacy_simulator_endpoints_keep_working(client):
    response = client.post(
        "/api/simular",
        json={
            "preco": 50000,
            "entrada": 10000,
            "prazo_meses": 48,
            "juros_aa": 24,
            "sobra_mensal": 2000,
            "rendimento_aa": 0,
        },
    )

    assert response.status_code == 200
    assert response.json()["juntar_a_vista"]["meses_para_juntar"] == 25
