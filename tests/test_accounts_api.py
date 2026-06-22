from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Database, Transaction
from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import accounts_repo


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
        def __init__(self):
            self.deleted: list[str] = []
            self.tokens: list[str | None] = []

        def create_connect_token(self, *, client_user_id=None, item_id=None):
            self.tokens.append(item_id)
            return f"token-for-{item_id or 'new'}"

        def delete_item(self, item_id):
            self.deleted.append(item_id)

        def close(self):
            return None

    fake = FakePluggy()

    def _override_pluggy():
        yield fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    client = TestClient(app)
    client.fake_pluggy = fake  # type: ignore[attr-defined]
    return client


def _seed_connected_accounts(db: Database) -> None:
    db.upsert_pluggy_item(
        "item-inter",
        connector_name="Banco Inter",
        status="UPDATED",
        mark_synced=True,
    )
    db.upsert_account(
        Account(
            id="pluggy:bank",
            source="pluggy",
            institution="077/0001/12345-6",
            name="Conta Corrente",
            type="BANK",
            metadata={
                "itemId": "item-inter",
                "bankData": {"transferNumber": "077/0001/12345-6"},
            },
        )
    )
    db.upsert_account(
        Account(
            id="pluggy:card",
            source="pluggy",
            institution="Cartao Inter Black",
            name="Cartao Inter Black",
            type="CREDIT",
            metadata={
                "itemId": "item-inter",
                "number": "550000001234",
                "creditData": {"brand": "MASTERCARD"},
            },
        )
    )
    accounts_repo.upsert_balance(
        db,
        account_id="pluggy:bank",
        balance=58.77,
        credit_limit=None,
        used=None,
        available=None,
        brand=None,
        last4=None,
        last_sync_at="2026-06-20T10:00:00",
        sync_status="UPDATED",
    )
    accounts_repo.upsert_balance(
        db,
        account_id="pluggy:card",
        balance=None,
        credit_limit=4000.0,
        used=749.5,
        available=3250.5,
        brand="MASTERCARD",
        last4="1234",
        last_sync_at="2026-06-20T10:00:00",
        sync_status="UPDATED",
    )


def test_accounts_overview_groups_banks_cards_and_totals(tmp_db: Database):
    _seed_connected_accounts(tmp_db)

    overview = accounts_repo.list_accounts_overview(tmp_db, month="2026-06")

    assert overview["banks"] == [
        {
            "id": "pluggy:bank",
            "institution": "077/0001/12345-6",
            "name": "Banco Inter - Conta Corrente",
            "type": "Conta bancária",
            "agency": "077/0001",
            "number": "12345-6",
            "balance": 58.77,
            "currency": "BRL",
            "pluggy_item_id": "item-inter",
            "connector_name": "Banco Inter",
            "last_sync_at": "2026-06-20T10:00:00",
            "sync_status": "UPDATED",
            "manual": False,
        }
    ]
    assert overview["cards"][0]["id"] == "pluggy:card"
    assert overview["cards"][0]["brand"] == "MASTERCARD"
    assert overview["cards"][0]["last4"] == "1234"
    assert overview["cards"][0]["usage_pct"] == 18.74
    assert overview["totals"] == {
        "accounts_balance": 58.77,
        "card_debt": 749.5,
        "period_result": 0.0,
    }


def test_accounts_overview_respects_balance_total_policy(tmp_db: Database):
    _seed_connected_accounts(tmp_db)
    tmp_db._conn.execute(
        """
        INSERT INTO account_total_settings (
            account_id, include_balance, include_transactions
        )
        VALUES ('pluggy:bank', 0, 1)
        """
    )
    tmp_db._conn.commit()

    overview = accounts_repo.list_accounts_overview(tmp_db, month="2026-06")

    assert overview["banks"][0]["balance"] == 58.77
    assert overview["totals"] == {
        "accounts_balance": 0.0,
        "card_debt": 749.5,
        "period_result": 0.0,
    }


def test_accounts_overview_uses_bank_code_and_card_fallback_names(tmp_db: Database):
    tmp_db.upsert_pluggy_item(
        "item-inter",
        connector_name="MeuPluggy",
        status="UPDATED",
    )
    tmp_db.upsert_account(
        Account(
            id="pluggy:inter-bank",
            source="pluggy",
            institution="077/0001/31238064-0",
            name="Conta Corrente",
            type="BANK",
            metadata={
                "itemId": "item-inter",
                "bankData": {"transferNumber": "077/0001/31238064-0"},
            },
        )
    )
    tmp_db.upsert_account(
        Account(
            id="pluggy:inter-card",
            source="pluggy",
            institution="DAVI OLIVEIRA NETO",
            name="DAVI OLIVEIRA NETO",
            type="CREDIT",
            metadata={
                "itemId": "item-inter",
                "number": "1122",
                "creditData": {"brand": "MASTERCARD"},
            },
        )
    )

    overview = accounts_repo.list_accounts_overview(tmp_db, month="2026-06")

    assert overview["banks"][0]["name"] == "Banco Inter - Conta Corrente"
    assert overview["cards"][0]["name"] == "Banco Inter Mastercard final 1122"


def test_manual_bank_without_snapshot_derives_balance(tmp_db: Database):
    tmp_db.upsert_account(
        Account(id="csv:wallet", source="csv", institution="Manual", name="Carteira", type="BANK")
    )
    tmp_db.insert_transactions(
        [
            Transaction(
                account_id="csv:wallet",
                posted_at=date(2026, 6, 1),
                amount=Decimal("100.00"),
                description="Saldo inicial",
                source="csv",
            ),
            Transaction(
                account_id="csv:wallet",
                posted_at=date(2026, 6, 2),
                amount=Decimal("-35.50"),
                description="Compra",
                source="csv",
            ),
        ]
    )

    overview = accounts_repo.list_accounts_overview(tmp_db, month="2026-06")

    assert overview["banks"][0]["balance"] == 64.5
    assert overview["banks"][0]["sync_status"] == "DERIVED"
    assert overview["banks"][0]["manual"] is True


def test_sort_and_disconnect_keep_transactions(tmp_db: Database):
    _seed_connected_accounts(tmp_db)
    tmp_db.insert_transactions(
        [
            Transaction(
                account_id="pluggy:bank",
                posted_at=date(2026, 6, 1),
                amount=Decimal("-10.00"),
                description="Compra historica",
                source="pluggy",
            )
        ]
    )

    accounts_repo.set_sort(tmp_db, ["pluggy:card", "pluggy:bank"])
    sorted_ids = [
        row["id"]
        for row in tmp_db._conn.execute(
            "SELECT id FROM accounts ORDER BY sort_order, id"
        ).fetchall()
    ]
    assert sorted_ids[:2] == ["pluggy:card", "pluggy:bank"]

    result = accounts_repo.disconnect(tmp_db, "item-inter")

    assert result == {
        "deleted": True,
        "item_id": "item-inter",
        "kept_transactions": True,
        "accounts_disconnected": ["pluggy:bank", "pluggy:card"],
    }
    assert tmp_db.get_pluggy_item("item-inter") is None
    assert tmp_db.count_transactions("pluggy:bank") == 1
    statuses = [
        row["sync_status"]
        for row in tmp_db._conn.execute(
            "SELECT sync_status FROM account_balances ORDER BY account_id"
        ).fetchall()
    ]
    assert statuses == ["DISCONNECTED", "DISCONNECTED"]


def test_accounts_endpoint_validation_and_empty_state(client):
    invalid = client.get("/api/accounts?month=2026-13")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    response = client.get("/api/accounts?month=2026-06")
    assert response.status_code == 200
    body = response.json()
    assert body["banks"] == []
    assert body["cards"] == []
    assert body["totals"] == {
        "accounts_balance": 0.0,
        "card_debt": 0.0,
        "period_result": 0.0,
    }
    assert "sync" in body


def test_account_actions_wrap_item_flow(client, tmp_db, monkeypatch):
    _seed_connected_accounts(tmp_db)
    spy = MagicMock(return_value=None)
    monkeypatch.setattr("src.web.app._background_sync", spy)

    sync = client.post("/api/accounts/pluggy:bank/sync", json={"days": 90})
    assert sync.status_code == 200
    assert sync.json() == {"account_id": "pluggy:bank", "item_id": "item-inter", "sync_scheduled": True, "days": 90}
    spy.assert_called_once_with("item-inter", 90)

    credentials = client.post("/api/accounts/pluggy:bank/credentials")
    assert credentials.status_code == 200
    assert credentials.json() == {"accessToken": "token-for-item-inter"}

    delete = client.delete("/api/accounts/pluggy:bank")
    assert delete.status_code == 200
    assert delete.json()["kept_transactions"] is True
    assert client.fake_pluggy.deleted == ["item-inter"]  # type: ignore[attr-defined]
    assert client.get("/api/items").json() == []


def test_sort_endpoint_persists_order(client, tmp_db):
    _seed_connected_accounts(tmp_db)

    response = client.patch(
        "/api/accounts/sort",
        json={"order": ["pluggy:card", "pluggy:bank"]},
    )

    assert response.status_code == 200
    assert response.json() == {"updated": 2}
    overview = client.get("/api/accounts?month=2026-06").json()
    assert [item["id"] for item in overview["cards"] + overview["banks"]] == [
        "pluggy:card",
        "pluggy:bank",
    ]
