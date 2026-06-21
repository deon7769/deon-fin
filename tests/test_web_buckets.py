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


def _seed_account(db) -> None:
    db.upsert_account(Account(id="acc-1", source="test", type="CHECKING"))


def _insert_tx(db, *, description: str = "IFOOD RESTAURANTE") -> Transaction:
    tx = Transaction(
        account_id="acc-1",
        posted_at=date(2026, 6, 20),
        amount=Decimal("-10.00"),
        description=description,
        source="test",
        external_id=f"web-tx-{db.count_transactions() + 1}",
    )
    db.insert_transactions([tx])
    return tx


def test_get_buckets_returns_seeded_ordered_items(client):
    response = client.get("/api/buckets")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["key"] for item in items] == [
        "liberdade_financeira",
        "custos_fixos",
        "conforto",
        "metas",
        "prazeres",
        "conhecimento",
    ]
    assert all(item["color"].startswith("#") for item in items)


def test_patch_transaction_bucket_marks_manual(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db)
    bucket_id = client.get("/api/buckets").json()["items"][2]["id"]

    response = client.patch(f"/api/transactions/{tx.id}", json={"bucket_id": bucket_id})

    assert response.status_code == 200
    assert response.json()["bucket_id"] == bucket_id
    row = tmp_db._conn.execute(
        "SELECT bucket_id, bucket_source FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()
    assert (row["bucket_id"], row["bucket_source"]) == (bucket_id, "manual")


def test_patch_transaction_bucket_rejects_invalid_bucket(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db)

    response = client.patch(f"/api/transactions/{tx.id}", json={"bucket_id": 9999})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_post_transaction_bucket_propagates(client, tmp_db):
    _seed_account(tmp_db)
    target = _insert_tx(tmp_db)
    similar = _insert_tx(tmp_db)
    different = _insert_tx(tmp_db, description="UBER TRIP")
    bucket_id = client.get("/api/buckets").json()["items"][2]["id"]

    response = client.post(
        f"/api/transactions/{target.id}/bucket",
        json={"bucket_id": bucket_id, "apply_to_similar": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["similar_affected"] == 1
    assert body["similar_ids"] == [similar.id]
    assert tmp_db._conn.execute(
        "SELECT bucket_id FROM transactions WHERE id=?",
        (different.id,),
    ).fetchone()["bucket_id"] is None


def test_reclassify_is_idempotent(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db, description="Compra mercado",)
    tmp_db._conn.execute(
        "UPDATE transactions SET category='Alimentação - Mercado' WHERE id=?",
        (tx.id,),
    )
    tmp_db._conn.commit()

    first = client.post("/api/buckets/reclassify")
    second = client.post("/api/buckets/reclassify")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["stats"]["by_map"] == 1
    assert second.json()["stats"]["by_map"] == 0
    row = tmp_db._conn.execute(
        "SELECT bucket_id, bucket_source FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()
    assert row["bucket_id"] is not None
    assert row["bucket_source"] == "auto"
