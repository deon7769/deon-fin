from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import portfolio_repo


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


def test_portfolio_api_returns_active_assets_summary(client, tmp_db):
    portfolio_repo.upsert_pluggy_asset(
        tmp_db,
        {
            "id": "inv-wege",
            "name": "WEGE3",
            "code": "WEGE3",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 10,
            "value": 40,
            "balance": 400,
            "status": "ACTIVE",
            "date": "2026-06-21T03:00:00.000Z",
        },
    )
    portfolio_repo.upsert_pluggy_asset(
        tmp_db,
        {
            "id": "inv-mxrf",
            "name": "MXRF11",
            "code": "MXRF11",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 20,
            "value": 10,
            "balance": 200,
            "status": "ACTIVE",
            "date": "2026-06-21T03:00:00.000Z",
        },
    )
    portfolio_repo.upsert_pluggy_asset(
        tmp_db,
        {
            "id": "inv-old",
            "name": "ITSA4",
            "code": "ITSA4",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 0,
            "value": 0,
            "balance": 0,
            "status": "TOTAL_WITHDRAWAL",
            "date": "2026-04-07T03:00:00.000Z",
        },
    )

    response = client.get("/api/investments")

    assert response.status_code == 200
    body = response.json()
    assert body["totals"] == {"asset_count": 2, "current_value": 600.0}
    assert body["by_class"] == [
        {
            "asset_class": "acoes_nac",
            "label": "Ações nacionais",
            "count": 1,
            "current_value": 400.0,
            "pct": 66.67,
        },
        {
            "asset_class": "fii",
            "label": "FIIs",
            "count": 1,
            "current_value": 200.0,
            "pct": 33.33,
        },
    ]
    assert [asset["ticker"] for asset in body["assets"]] == ["WEGE3", "MXRF11"]
    assert body["assets"][0]["pct_carteira"] == 66.67
    assert body["assets"][0]["manually_adjusted"] is False
    assert body["assets"][0]["price_source"] is None
    assert body["assets"][0]["price_updated_at"] is None


def test_portfolio_api_can_include_inactive_assets(client, tmp_db):
    portfolio_repo.upsert_pluggy_asset(
        tmp_db,
        {
            "id": "inv-old",
            "name": "ITSA4",
            "code": "ITSA4",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 0,
            "value": 0,
            "balance": 0,
            "status": "TOTAL_WITHDRAWAL",
            "date": "2026-04-07T03:00:00.000Z",
        },
    )

    response = client.get("/api/investments?include_inactive=true")

    assert response.status_code == 200
    assert response.json()["totals"] == {"asset_count": 1, "current_value": 0.0}
    assert response.json()["assets"][0]["status"] == "TOTAL_WITHDRAWAL"


def test_manual_fixed_income_asset_crud(client):
    created = client.post(
        "/api/investments/assets",
        json={
            "asset_class": "rf",
            "name": "Tesouro Selic",
            "manual_value": 1500.55,
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["source"] == "manual"
    assert body["asset_class"] == "rf"
    assert body["current_value"] == 1500.55
    assert body["manual_value"] == 1500.55
    assert body["price_source"] == "manual"

    updated = client.patch(
        f"/api/investments/assets/{body['id']}",
        json={"manual_value": 1750.25},
    )

    assert updated.status_code == 200
    assert updated.json()["current_value"] == 1750.25
    assert updated.json()["manual_value"] == 1750.25

    deleted = client.delete(f"/api/investments/assets/{body['id']}")

    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_id": body["id"]}
    assert client.get("/api/investments").json()["assets"] == []


def test_patch_pluggy_asset_quantity_marks_manual_adjustment_and_next_sync_clears(
    client,
    tmp_db,
):
    asset_id = portfolio_repo.upsert_pluggy_asset(
        tmp_db,
        {
            "id": "inv-wege",
            "name": "WEGE3",
            "code": "WEGE3",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 10,
            "value": 40,
            "balance": 400,
            "status": "ACTIVE",
            "date": "2026-06-21T03:00:00.000Z",
        },
    )

    patched = client.patch(
        f"/api/investments/assets/{asset_id}",
        json={"quantity": 12},
    )

    assert patched.status_code == 200
    patched_body = patched.json()
    assert patched_body["quantity"] == 12.0
    assert patched_body["current_value"] == 480.0
    assert patched_body["manually_adjusted"] is True
    assert patched_body["manual_adjusted_at"] is not None

    portfolio_repo.upsert_pluggy_asset(
        tmp_db,
        {
            "id": "inv-wege",
            "name": "WEGE3",
            "code": "WEGE3",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 11,
            "value": 41,
            "balance": 451,
            "status": "ACTIVE",
            "date": "2026-06-22T03:00:00.000Z",
        },
    )

    refreshed = client.get("/api/investments").json()["assets"][0]
    assert refreshed["quantity"] == 11.0
    assert refreshed["current_value"] == 451.0
    assert refreshed["manually_adjusted"] is False
    assert refreshed["manual_adjusted_at"] is None


def test_investment_profiles_and_targets_contract(client):
    profiles = client.get("/api/investments/profiles")

    assert profiles.status_code == 200
    body = profiles.json()
    assert [profile["key"] for profile in body["profiles"]] == [
        "conservador",
        "moderado",
        "arrojado",
    ]
    assert all(round(sum(profile["targets"].values()), 2) == 100 for profile in body["profiles"])

    targets = client.get("/api/investments/targets")

    assert targets.status_code == 200
    payload = targets.json()
    assert payload["perfil"] == "custom"
    assert payload["sum_pct"] == 0.0
    assert payload["valid"] is False
    assert set(payload["targets"]) == {
        "acoes_nac",
        "acoes_int",
        "fii",
        "reit",
        "cripto",
        "rf",
        "rf_int",
    }


def test_save_investment_targets_rejects_invalid_sum(client):
    response = client.put(
        "/api/investments/targets",
        json={"targets": {"rf": 60, "acoes_nac": 20}},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "targets_sum"
    assert "100%" in response.json()["error"]["message"]


def test_save_investment_targets_detects_matching_profile(client):
    response = client.put(
        "/api/investments/targets",
        json={
            "perfil": "custom",
            "targets": {
                "rf": 35,
                "rf_int": 5,
                "acoes_nac": 20,
                "acoes_int": 15,
                "fii": 15,
                "reit": 5,
                "cripto": 5,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["perfil"] == "moderado"
    assert body["sum_pct"] == 100.0
    assert body["valid"] is True
    assert body["targets"]["acoes_int"] == 15.0

    persisted = client.get("/api/investments/targets").json()
    assert persisted["perfil"] == "moderado"
    assert persisted["targets"] == body["targets"]


def test_questions_api_crud_and_restore_defaults(client):
    initial = client.get("/api/investments/questions?diagram_type=acoes")

    assert initial.status_code == 200
    assert initial.json()["diagram_type"] == "acoes"
    assert len(initial.json()["questions"]) == 5
    assert "ROE" in initial.json()["questions"][0]["pergunta"]

    created = client.post(
        "/api/investments/questions",
        json={
            "diagram_type": "acoes",
            "criterio": "Moat",
            "pergunta": "Possui vantagem competitiva clara?",
            "peso": 2,
            "sort_order": 15,
        },
    )

    assert created.status_code == 201
    created_body = created.json()
    assert created_body["ativo"] is True
    assert created_body["peso"] == 2.0

    patched = client.patch(
        f"/api/investments/questions/{created_body['id']}",
        json={"pergunta": "Possui vantagem competitiva duravel?", "ativo": False},
    )

    assert patched.status_code == 200
    assert patched.json()["pergunta"].endswith("duravel?")
    assert patched.json()["ativo"] is False

    deleted = client.delete(f"/api/investments/questions/{created_body['id']}")

    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_id": created_body["id"]}

    first_default_id = initial.json()["questions"][0]["id"]
    assert client.delete(f"/api/investments/questions/{first_default_id}").status_code == 200

    restored = client.post("/api/investments/questions/restore-defaults?diagram_type=acoes")

    assert restored.status_code == 200
    restored_questions = restored.json()["questions"]
    assert len(restored_questions) == 5
    assert [question["sort_order"] for question in restored_questions] == [10, 20, 30, 40, 50]
    assert "ROE" in restored_questions[0]["pergunta"]


def test_asset_answers_api_updates_score_and_investments_summary(client, tmp_db):
    asset = portfolio_repo.create_manual_asset(
        tmp_db,
        asset_class="acoes_nac",
        ticker="WEGE3",
        name="WEG",
        quantity=10,
        manual_value=400,
    )

    initial = client.get(f"/api/investments/assets/{asset['id']}/answers")

    assert initial.status_code == 200
    initial_body = initial.json()
    assert initial_body["score"]["nota"] == -10.0
    assert len(initial_body["questions"]) == 5
    assert all(answer["resposta"] is False for answer in initial_body["answers"])

    question_ids = [question["id"] for question in initial_body["questions"][:3]]
    updated = client.put(
        f"/api/investments/assets/{asset['id']}/answers",
        json={
            "answers": [
                {"question_id": question_ids[0], "resposta": True},
                {"question_id": question_ids[1], "resposta": True},
                {"question_id": question_ids[2], "resposta": True},
            ]
        },
    )

    assert updated.status_code == 200
    assert updated.json()["score"]["nota"] == 2.0
    assert [answer["resposta"] for answer in updated.json()["answers"][:3]] == [
        True,
        True,
        True,
    ]

    investments = client.get("/api/investments").json()

    assert investments["assets"][0]["nota"] == 2.0
