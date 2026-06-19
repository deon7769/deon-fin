from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Transaction
from src.web.app import create_app, get_db, get_pluggy


@pytest.fixture
def client(tmp_db, monkeypatch):
    # Por padrão, neutraliza o sync em background pra evitar chamadas reais ao
    # Pluggy nos testes. Testes que quiserem checar o agendamento podem
    # patchar src.web.app._background_sync localmente.
    monkeypatch.setattr("src.web.app._background_sync", lambda *a, **kw: None)

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


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Pluggy Connect" in r.text
    assert 'src="https://cdn.pluggy.ai/pluggy-connect/' in r.text


def test_create_connect_token(client):
    r = client.post("/api/connect-token", json={"client_user_id": "u1"})
    assert r.status_code == 200
    assert r.json() == {"accessToken": "fake.connect.token"}


def test_register_item_schedules_sync(client, monkeypatch):
    from unittest.mock import MagicMock
    spy = MagicMock(return_value=None)
    monkeypatch.setattr("src.web.app._background_sync", spy)

    r = client.post("/api/items", json={
        "item_id": "item-123",
        "connector_id": 201,
        "connector_name": "Nubank",
        "status": "UPDATED",
    })
    assert r.status_code == 200
    assert r.json()["sync_scheduled"] is True
    spy.assert_called_once_with("item-123", 365)

    items = client.get("/api/items").json()
    assert any(i["id"] == "item-123" for i in items)


def test_list_items_includes_connected_account_names(client, tmp_db):
    tmp_db.upsert_pluggy_item(
        "item-accounts",
        connector_name="MeuPluggy",
        status="UPDATED",
    )
    tmp_db.upsert_account(Account(
        id="pluggy:acc-bank",
        source="pluggy",
        institution="001/0001/12345-6",
        name="Banco Exemplo",
        type="BANK",
        metadata={"itemId": "item-accounts", "marketingName": "Conta Corrente Exemplo"},
    ))
    tmp_db.upsert_account(Account(
        id="pluggy:acc-card",
        source="pluggy",
        institution="Cartao Exemplo Black",
        name="Cartao Exemplo Black",
        type="CREDIT",
        metadata={"itemId": "item-accounts"},
    ))

    items = client.get("/api/items").json()

    item = next(i for i in items if i["id"] == "item-accounts")
    assert item["display_name"] == "Banco Exemplo"
    assert item["account_labels"] == [
        "Conta: Conta Corrente Exemplo",
        "Cartão: Cartao Exemplo Black",
    ]


def test_sync_all_uses_requested_period(client, monkeypatch):
    from unittest.mock import MagicMock

    spy = MagicMock(return_value="ok")
    monkeypatch.setattr("src.web.app._sync_all_items", spy)

    r = client.post("/api/sync-all", json={"days": 365})

    assert r.status_code == 200
    assert r.json() == {"scheduled": True, "days": 365}
    spy.assert_called_once_with(365)


def test_sync_unknown_item_returns_404(client):
    r = client.post("/api/items/missing/sync", json={"days": 30})
    assert r.status_code == 404


def test_delete_item(client):
    client.post("/api/items", json={"item_id": "item-del", "connector_name": "X"})
    r = client.delete("/api/items/item-del")
    assert r.status_code == 200
    assert client.get("/api/items").json() == []


def test_summary_empty(client):
    s = client.get("/api/summary?days=30").json()
    assert s["transactions"] == 0
    assert s["inflow"] == 0.0
    assert s["outflow"] == 0.0
    assert s["by_category"] == []


def _seed_summary_sign_transactions(db):
    posted = date.today() - timedelta(days=3)
    db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    db.upsert_account(Account(id="card1", source="test", name="Card", type="CREDIT"))
    db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=posted,
            amount=Decimal("1000.00"),
            description="Salary",
            source="test",
            category="Salary",
        ),
        Transaction(
            account_id="bank1",
            posted_at=posted,
            amount=Decimal("-100.00"),
            description="Debit groceries",
            source="test",
            category="Groceries",
        ),
        Transaction(
            account_id="bank1",
            posted_at=posted,
            amount=Decimal("-300.00"),
            description="Invoice payment from bank",
            source="test",
            category="Credit card payment",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("300.00"),
            description="Card purchase",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("-50.00"),
            description="Card refund",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("-300.00"),
            description="Invoice settlement on card",
            source="test",
            category="Credit card payment",
        ),
    ])


def test_summary_uses_canonical_financial_signs(client, tmp_db):
    _seed_summary_sign_transactions(tmp_db)

    s = client.get("/api/summary?days=30").json()

    assert s["transactions"] == 6
    assert s["inflow"] == 1000.0
    assert s["outflow"] == -350.0
    assert s["net"] == 650.0

    by_category = {row["category"]: row["amount"] for row in s["by_category"]}
    assert by_category == {"Shopping": -250.0, "Groceries": -100.0}


def _seed_refund_heavy_summary_transactions(db):
    posted = date.today() - timedelta(days=3)
    db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    db.upsert_account(Account(id="card1", source="test", name="Card", type="CREDIT"))
    db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=posted,
            amount=Decimal("1000.00"),
            description="Salary",
            source="test",
            category="Salary",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("40.00"),
            description="Card shopping purchase",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("-100.00"),
            description="Card shopping refund",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("70.00"),
            description="Card groceries purchase",
            source="test",
            category="Groceries",
        ),
    ])


def test_summary_omits_refund_heavy_categories_from_legacy_spending(client, tmp_db):
    _seed_refund_heavy_summary_transactions(tmp_db)

    s = client.get("/api/summary?days=30").json()

    assert s["transactions"] == 4
    assert s["inflow"] == 1000.0
    assert s["outflow"] == -70.0


def test_summary_can_follow_month_filter(client, tmp_db):
    today = date.today()
    recent = today - timedelta(days=120)
    old = today - timedelta(days=430)
    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    tmp_db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=recent,
            amount=Decimal("-100.00"),
            description="Recent groceries",
            source="test",
            category="Groceries",
        ),
        Transaction(
            account_id="bank1",
            posted_at=old,
            amount=Decimal("-200.00"),
            description="Old groceries",
            source="test",
            category="Groceries",
        ),
    ])

    s = client.get("/api/summary?months=12").json()

    assert s["period_months"] == 12
    assert s["transactions"] == 1
    assert s["outflow"] == -100.0


def test_dashboard_defaults_to_last_12_months(client, tmp_db):
    today = date.today()
    recent = today - timedelta(days=120)
    old = today - timedelta(days=430)
    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    tmp_db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=recent,
            amount=Decimal("-100.00"),
            description="Recent groceries",
            source="test",
            category="Groceries",
        ),
        Transaction(
            account_id="bank1",
            posted_at=old,
            amount=Decimal("-200.00"),
            description="Old groceries",
            source="test",
            category="Groceries",
        ),
    ])

    d = client.get("/api/dashboard").json()
    months = {row["mes"] for row in d["fluxo_mensal"]}

    assert d["kpis"]["periodo_meses"] == 12
    assert recent.isoformat()[:7] in months
    assert old.isoformat()[:7] not in months
