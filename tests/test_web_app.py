from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Database, Transaction
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


def test_cors_headers_allow_next_dev_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:3000"})

    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_error_envelope_404(client):
    r = client.get("/api/does-not-exist")

    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    assert "message" in r.json()["error"]


def test_error_envelope_422(client):
    r = client.post("/api/items", json={"connector_name": "missing item id"})

    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert "message" in r.json()["error"]


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


def test_list_items_uses_bank_code_when_account_name_is_generic(client, tmp_db):
    tmp_db.upsert_pluggy_item(
        "item-inter",
        connector_name="MeuPluggy",
        status="UPDATED",
    )
    tmp_db.upsert_account(Account(
        id="pluggy:inter-bank",
        source="pluggy",
        institution="077/0001/31238064-0",
        name="Conta Corrente",
        type="BANK",
        metadata={
            "itemId": "item-inter",
            "subtype": "CHECKING_ACCOUNT",
            "bankData": {"transferNumber": "077/0001/31238064-0"},
        },
    ))
    tmp_db.upsert_account(Account(
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
    ))

    items = client.get("/api/items").json()

    item = next(i for i in items if i["id"] == "item-inter")
    assert item["display_name"] == "Banco Inter"
    assert item["account_labels"] == [
        "Conta: Banco Inter - Conta Corrente",
        "Cartão: Banco Inter Mastercard final 1122",
    ]


def test_sync_all_uses_requested_period(client, monkeypatch):
    from unittest.mock import MagicMock

    spy = MagicMock(return_value="ok")
    monkeypatch.setattr("src.web.app._sync_all_items", spy)

    r = client.post("/api/sync-all", json={"days": 365})

    assert r.status_code == 200
    assert r.json() == {"scheduled": True, "days": 365}
    spy.assert_called_once_with(365)


def test_background_sync_fills_missing_reference_month(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from src.web import app as web_app

    db_path = tmp_path / "sync.db"
    seed = Database(db_path)
    seed.close()

    class FakePluggy:
        def close(self):
            return None

    class FakeCategorizer:
        def apply_to_database(self, db):
            return {"updated": 0}

    def fake_sync(pc, db, item_id, *, since):
        db.upsert_account(Account(id="acc-sync", source="pluggy", type="CHECKING"))
        db.insert_transactions([
            Transaction(
                account_id="acc-sync",
                posted_at=date(2026, 6, 14),
                amount=Decimal("-10.00"),
                description="Synced transaction",
                source="pluggy",
            )
        ])

    monkeypatch.setattr(
        web_app,
        "settings",
        SimpleNamespace(
            database_path=db_path,
            client_id="client",
            client_secret="secret",
        ),
    )
    monkeypatch.setattr(web_app, "PluggyClient", lambda *args, **kwargs: FakePluggy())
    monkeypatch.setattr(web_app, "Categorizer", FakeCategorizer)
    monkeypatch.setattr(web_app, "sync_pluggy_item", fake_sync)

    web_app._background_sync("item-sync", 30)

    check = Database(db_path)
    value = check._conn.execute(
        "SELECT reference_month FROM transactions WHERE description='Synced transaction'"
    ).fetchone()[0]
    assert value == "2026-06"
    check.close()


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


def test_dashboard_period_kpis_use_filtered_income_not_fixed_profile(
    client,
    tmp_db,
    monkeypatch,
):
    today = date.today()
    posted = today - timedelta(days=20)
    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    tmp_db.insert_transactions([
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
            description="Groceries",
            source="test",
            category="Groceries",
        ),
    ])
    monkeypatch.setattr(
        "src.web.app.mnt.load_family_profile",
        lambda: {"receitas": [{"membro": "Config", "valor": 9999}]},
    )

    d = client.get("/api/dashboard?meses=12").json()

    assert d["kpis"]["renda_informada"] == 9999
    assert d["kpis"]["renda_media"] == 1000.0
    assert d["kpis"]["saldo_medio"] == 900.0
    assert d["budget_5030"]["renda"] == 1000.0
    assert d["executivo"]["renda"] == 1000.0
