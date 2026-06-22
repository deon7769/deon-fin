from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Transaction
from src.web.app import create_app, get_db, get_pluggy


@pytest.fixture
def client(tmp_db, monkeypatch):
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


def _seed_account(db, *, account_id: str = "api-checking", type: str = "CHECKING") -> None:
    db.upsert_account(
        Account(
            id=account_id,
            source="test",
            institution="Banco Teste",
            name=f"Conta {account_id}",
            type=type,
        )
    )


def _insert_tx(db, *, external_id: str, account_id: str = "api-checking") -> Transaction:
    tx = Transaction(
        account_id=account_id,
        posted_at=date(2026, 6, 20),
        amount=Decimal("-42.50"),
        description="Compra API",
        raw_description="COMPRA API",
        category="Alimentação - Restaurante",
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    db._conn.execute("UPDATE transactions SET reference_month='2026-06' WHERE id=?", (tx.id,))
    db._conn.commit()
    return tx


def test_get_transactions_shape_and_bad_params(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db, external_id="api-list-1")

    response = client.get("/api/transactions?month=2026-06&page=1&page_size=10")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 1
    assert body["summary"]["expense"] == 42.5
    assert body["items"][0]["id"] == tx.id
    assert body["items"][0]["account_name"] == "Conta api-checking"
    assert body["items"][0]["bucket"] is None
    assert body["items"][0]["tag"] is None
    assert body["items"][0]["type"] == "expense"
    assert body["items"][0]["signed_value"] == -42.5
    assert body["items"][0]["display_value"] == -42.5

    invalid_month = client.get("/api/transactions?month=202606")
    assert invalid_month.status_code == 422
    assert invalid_month.json()["error"]["code"] == "validation_error"

    invalid_amount = client.get("/api/transactions?min=20&max=10")
    assert invalid_amount.status_code == 422
    assert invalid_amount.json()["error"]["code"] == "validation_error"

    invalid_bucket = client.get("/api/transactions?bucket_ids=abc")
    assert invalid_bucket.status_code == 422
    assert invalid_bucket.json()["error"]["code"] == "validation_error"


def test_patch_transaction_accepts_all_partial_fields(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db, external_id="api-patch-1")
    bucket_id = client.get("/api/buckets").json()["items"][0]["id"]
    tag_id = client.get("/api/tags").json()["items"][0]["id"]

    response = client.patch(
        f"/api/transactions/{tx.id}",
        json={
            "bucket_id": bucket_id,
            "tag_id": tag_id,
            "hidden": True,
            "note": "Conferir depois",
            "reference_month": "2026-07",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["updated"] == 1
    assert body["bucket_id"] == bucket_id
    assert body["bucket_source"] == "manual"
    assert body["tag_id"] == tag_id
    assert body["hidden"] is True
    assert body["note"] == "Conferir depois"
    assert body["reference_month"] == "2026-07"
    row = tmp_db._conn.execute(
        "SELECT bucket_id, bucket_source, tag_id, hidden, note, reference_month FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()
    assert tuple(row) == (bucket_id, "manual", tag_id, 1, "Conferir depois", "2026-07")


def test_patch_transaction_validates_empty_body_fk_and_reference_month(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db, external_id="api-patch-validate-1")

    empty = client.patch(f"/api/transactions/{tx.id}", json={})
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "validation_error"

    invalid_bucket = client.patch(f"/api/transactions/{tx.id}", json={"bucket_id": 9999})
    assert invalid_bucket.status_code == 422

    invalid_tag = client.patch(f"/api/transactions/{tx.id}", json={"tag_id": 9999})
    assert invalid_tag.status_code == 422

    invalid_month = client.patch(f"/api/transactions/{tx.id}", json={"reference_month": "2026"})
    assert invalid_month.status_code == 422

    missing = client.patch("/api/transactions/missing", json={"hidden": True})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_create_manual_transaction_uses_type_sign_and_reference_month(client, tmp_db):
    _seed_account(tmp_db)
    _seed_account(tmp_db, account_id="api-credit", type="CREDIT")
    bucket_id = client.get("/api/buckets").json()["items"][0]["id"]
    tag_id = client.get("/api/tags").json()["items"][0]["id"]

    checking = client.post(
        "/api/transactions",
        json={
            "account_id": "api-checking",
            "posted_at": "2026-06-20",
            "amount": 123.45,
            "type": "expense",
            "description": "Despesa manual",
            "bucket_id": bucket_id,
            "tag_id": tag_id,
            "note": "manual",
        },
    )
    credit = client.post(
        "/api/transactions",
        json={
            "account_id": "api-credit",
            "posted_at": "2026-06-20",
            "amount": 90,
            "type": "expense",
            "description": "Compra cartao manual",
        },
    )

    assert checking.status_code == 201
    assert credit.status_code == 201
    checking_body = checking.json()
    credit_body = credit.json()
    assert checking_body["duplicate"] is False
    assert checking_body["transaction"]["amount"] == -123.45
    assert checking_body["transaction"]["reference_month"] == "2026-06"
    assert checking_body["transaction"]["bucket"]["id"] == bucket_id
    assert checking_body["transaction"]["tag"]["id"] == tag_id
    assert credit_body["transaction"]["amount"] == 90.0
    assert credit_body["transaction"]["type"] == "expense"


def test_create_duplicate_returns_existing_without_second_insert(client, tmp_db):
    _seed_account(tmp_db)
    payload = {
        "account_id": "api-checking",
        "posted_at": "2026-06-20",
        "amount": 10,
        "type": "expense",
        "description": "Duplicada manual",
    }

    first = client.post("/api/transactions", json=payload)
    second = client.post("/api/transactions", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert tmp_db.count_transactions() == 1
    assert second.json()["transaction"]["id"] == first.json()["transaction"]["id"]


def test_delete_transaction_and_bulk_patch(client, tmp_db):
    _seed_account(tmp_db)
    first = _insert_tx(tmp_db, external_id="api-bulk-1")
    second = _insert_tx(tmp_db, external_id="api-bulk-2")
    tag_id = client.get("/api/tags").json()["items"][0]["id"]

    bulk = client.patch(
        "/api/transactions/bulk",
        json={"ids": [first.id, second.id, "missing"], "patch": {"hidden": True, "tag_id": tag_id}},
    )

    assert bulk.status_code == 200
    assert bulk.json()["updated"] == 2
    assert bulk.json()["not_found"] == ["missing"]
    rows = tmp_db._conn.execute(
        "SELECT hidden, tag_id FROM transactions ORDER BY external_id"
    ).fetchall()
    assert [(row["hidden"], row["tag_id"]) for row in rows] == [(1, tag_id), (1, tag_id)]

    deleted = client.delete(f"/api/transactions/{first.id}")
    missing_delete = client.delete(f"/api/transactions/{first.id}")

    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_id": first.id}
    assert missing_delete.status_code == 404
    assert tmp_db.count_transactions() == 1
