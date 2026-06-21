from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Transaction
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


def _seed_account(db) -> None:
    db.upsert_account(Account(id="acc-profile", source="test", type="CHECKING"))


def _insert_tx(db, external_id: str, posted_at: date) -> Transaction:
    tx = Transaction(
        account_id="acc-profile",
        posted_at=posted_at,
        amount=Decimal("-10.00"),
        description="Compra perfil",
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    return tx


def test_get_profile_creates_singleton_with_initials(client):
    response = client.get("/api/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["name"] == ""
    assert body["email"] == ""
    assert body["monthly_income"] == 0.0
    assert body["financial_month_start_day"] == 1
    assert body["goals_text"] == ""
    assert body["initials"] == "?"


def test_put_profile_persists_values_and_reports_no_recompute(client):
    response = client.put(
        "/api/profile",
        json={
            "name": "Davi Alves",
            "email": "davi@example.com",
            "monthly_income": 10490.41,
            "financial_month_start_day": 1,
            "goals_text": "Quitar financiamento",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "saved": True,
        "reference_month_recompute": "not_needed",
        "profile": {
            "id": 1,
            "name": "Davi Alves",
            "email": "davi@example.com",
            "monthly_income": 10490.41,
            "financial_month_start_day": 1,
            "goals_text": "Quitar financiamento",
            "initials": "DA",
            "updated_at": response.json()["profile"]["updated_at"],
        },
    }


def test_put_profile_validates_email_day_and_income(client):
    cases = [
        {"email": "sem-arroba", "monthly_income": 1, "financial_month_start_day": 1},
        {"email": "", "monthly_income": -1, "financial_month_start_day": 1},
        {"email": "", "monthly_income": 1, "financial_month_start_day": 0},
        {"email": "", "monthly_income": 1, "financial_month_start_day": 29},
    ]

    for payload in cases:
        response = client.put(
            "/api/profile",
            json={"name": "", "goals_text": "", **payload},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


def test_put_profile_recomputes_reference_month_when_start_day_changes(client, tmp_db):
    _seed_account(tmp_db)
    before_cycle = _insert_tx(tmp_db, "profile-recompute-1", date(2026, 6, 14))
    cycle_start = _insert_tx(tmp_db, "profile-recompute-2", date(2026, 6, 15))

    response = client.put(
        "/api/profile",
        json={
            "name": "Davi Alves",
            "email": "",
            "monthly_income": 1000,
            "financial_month_start_day": 15,
            "goals_text": "",
        },
    )

    assert response.status_code == 200
    assert response.json()["reference_month_recompute"] == "scheduled"
    rows = tmp_db._conn.execute(
        "SELECT id, reference_month FROM transactions ORDER BY posted_at"
    ).fetchall()
    assert [(row["id"], row["reference_month"]) for row in rows] == [
        (before_cycle.id, "2026-05"),
        (cycle_start.id, "2026-06"),
    ]
