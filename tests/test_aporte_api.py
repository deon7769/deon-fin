from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import portfolio_repo, score_repo


@pytest.fixture
def client(tmp_db, monkeypatch):
    monkeypatch.setattr("src.web.app._background_sync", lambda *a, **kw: None)
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.mnt.load_family_profile",
        lambda: None,
    )

    app = create_app()

    def _override_db():
        yield tmp_db

    class FakePluggy:
        def create_connect_token(self, *, client_user_id=None, item_id=None):
            return "fake.connect.token"

        def delete_item(self, item_id):
            return None

        def close(self):
            return None

    def _override_pluggy():
        yield FakePluggy()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    return TestClient(app)


def _save_targets(tmp_db, **targets):
    base = {
        "rf": 0,
        "rf_int": 0,
        "acoes_nac": 0,
        "acoes_int": 0,
        "fii": 0,
        "reit": 0,
        "cripto": 0,
    }
    base.update(targets)
    portfolio_repo.save_allocation_targets(tmp_db, base)


def _question_ids(tmp_db, diagram_type: str = "acoes") -> list[int]:
    return [
        row["id"]
        for row in tmp_db._conn.execute(
            """
            SELECT id
              FROM asset_questions
             WHERE diagram_type=?
             ORDER BY sort_order, id
            """,
            (diagram_type,),
        ).fetchall()
    ]


def _set_yes_count(tmp_db, asset_id: int, yes_count: int) -> None:
    ids = _question_ids(tmp_db)
    score_repo.save_asset_answers(
        tmp_db,
        asset_id,
        {question_id: index < yes_count for index, question_id in enumerate(ids)},
    )


def test_calcular_aporte_requires_targets_sum_100(client):
    response = client.post("/api/investments/aporte/calcular", json={"aporte": 1000})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "targets_sum"


def test_calcular_aporte_uses_assets_targets_and_scores(client, tmp_db):
    _save_targets(tmp_db, acoes_int=100)
    assets = [
        portfolio_repo.create_manual_asset(
            tmp_db,
            asset_class="acoes_int",
            ticker="INT2",
            quantity=0,
            unit_price=10,
        ),
        portfolio_repo.create_manual_asset(
            tmp_db,
            asset_class="acoes_int",
            ticker="INT6",
            quantity=0,
            unit_price=100,
        ),
        portfolio_repo.create_manual_asset(
            tmp_db,
            asset_class="acoes_int",
            ticker="INT10",
            quantity=0,
            unit_price=250,
        ),
    ]
    _set_yes_count(tmp_db, assets[0]["id"], 3)
    _set_yes_count(tmp_db, assets[1]["id"], 4)
    _set_yes_count(tmp_db, assets[2]["id"], 5)

    response = client.post("/api/investments/aporte/calcular", json={"aporte": 1000})

    assert response.status_code == 200
    body = response.json()
    assert body["patrimonio"] == 0.0
    assert body["pl_alvo"] == 1000.0
    assert body["troco"] == 0.0
    sugestoes = {item["ticker"]: item for item in body["sugestoes"]}
    assert sugestoes["INT2"]["nota"] == 2.0
    assert sugestoes["INT2"]["sugest_rs"] == pytest.approx(111.11, abs=0.01)
    assert sugestoes["INT6"]["sugest_rs"] == pytest.approx(333.33, abs=0.01)
    assert sugestoes["INT10"]["sugest_rs"] == pytest.approx(555.56, abs=0.01)


def test_calcular_aporte_does_not_allocate_fixed_income_without_unit_price(client, tmp_db):
    _save_targets(tmp_db, rf=100)
    portfolio_repo.create_manual_asset(
        tmp_db,
        asset_class="rf",
        name="Tesouro Selic",
        manual_value=1000,
    )

    response = client.post("/api/investments/aporte/calcular", json={"aporte": 500})

    assert response.status_code == 200
    body = response.json()
    assert body["patrimonio"] == 1000.0
    assert body["pl_alvo"] == 1500.0
    assert body["sugestoes"] == []
    assert body["troco"] == 500.0


def test_confirmar_aporte_adds_quantity_updates_value_and_saves_ultimo_aporte(
    client,
    tmp_db,
):
    asset = portfolio_repo.create_manual_asset(
        tmp_db,
        asset_class="acoes_nac",
        ticker="WEGE3",
        quantity=10,
        unit_price=40,
    )

    response = client.post(
        "/api/investments/aporte/confirmar",
        json={
            "aporte": 200,
            "compras": [{"asset_id": asset["id"], "quantidade": 5}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assets"][0]["quantity"] == 15.0
    assert body["assets"][0]["current_value"] == 600.0
    assert body["assets"][0]["manually_adjusted"] is True

    profile = tmp_db._conn.execute(
        "SELECT ultimo_aporte FROM investment_profile WHERE id=1"
    ).fetchone()
    assert profile["ultimo_aporte"] == 200.0
    tx_count = tmp_db._conn.execute("SELECT COUNT(*) FROM portfolio_transactions").fetchone()[0]
    assert tx_count == 0
