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
