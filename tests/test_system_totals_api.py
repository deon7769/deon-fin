from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Database
from src.web.app import create_app, get_db, get_pluggy


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

    fake = FakePluggy()

    def _override_pluggy():
        yield fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    return TestClient(app)


def test_maintenance_system_totals_endpoint_saves_policy(
    tmp_db: Database, client: TestClient
):
    tmp_db.upsert_account(
        Account(
            id="acc-api",
            source="test",
            institution="Banco Teste",
            name="Conta API",
            type="CHECKING",
        )
    )

    initial = client.get("/api/maintenance/system-totals")
    assert initial.status_code == 200
    account = next(item for item in initial.json()["accounts"] if item["id"] == "acc-api")
    assert account["include_balance"] is True
    assert account["include_transactions"] is True

    saved = client.patch(
        "/api/maintenance/system-totals",
        json={
            "accounts": [
                {
                    "account_id": "acc-api",
                    "include_balance": False,
                    "include_transactions": False,
                }
            ],
            "movements": [
                {"movement_type": "investment", "include_in_totals": False}
            ],
        },
    )

    assert saved.status_code == 200
    account = next(item for item in saved.json()["accounts"] if item["id"] == "acc-api")
    movement = next(item for item in saved.json()["movements"] if item["key"] == "investment")
    assert account["include_balance"] is False
    assert account["include_transactions"] is False
    assert movement["include_in_totals"] is False


def test_maintenance_system_totals_patch_is_atomic(tmp_db: Database, client: TestClient):
    tmp_db.upsert_account(
        Account(
            id="acc-atomic",
            source="test",
            institution="Banco Teste",
            name="Conta Atomica",
            type="CHECKING",
        )
    )

    response = client.patch(
        "/api/maintenance/system-totals",
        json={
            "accounts": [
                {
                    "account_id": "acc-atomic",
                    "include_balance": False,
                    "include_transactions": False,
                }
            ],
            "movements": [
                {"movement_type": "movimento-inexistente", "include_in_totals": False}
            ],
        },
    )

    assert response.status_code == 400
    current = client.get("/api/maintenance/system-totals")
    account = next(item for item in current.json()["accounts"] if item["id"] == "acc-atomic")
    assert account["include_balance"] is True
    assert account["include_transactions"] is True
