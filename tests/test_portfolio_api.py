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
