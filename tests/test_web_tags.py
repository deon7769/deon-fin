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
    db.upsert_account(Account(id="acc-tags-web", source="test", type="CHECKING"))


def _insert_tx(db, external_id: str) -> Transaction:
    tx = Transaction(
        account_id="acc-tags-web",
        posted_at=date(2026, 6, 20),
        amount=Decimal("-10.00"),
        description="Compra teste",
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    return tx


def _items(client):
    return client.get("/api/tags").json()["items"]


def test_get_tags_returns_seeded_items(client):
    response = client.get("/api/tags")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["name"] for item in items] == [
        "Alimentação",
        "Conforto",
        "Educação",
        "Lazer",
        "Saúde",
        "Transporte",
        "Vestuário",
    ]
    assert all(item["color"].startswith("#") for item in items)
    assert all(item["tx_count"] == 0 for item in items)


def test_post_tag_creates_and_rejects_duplicates_and_invalid_color(client):
    created = client.post("/api/tags", json={"name": " Pets ", "color": "#10B981"})

    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Pets"
    assert body["color"] == "#10b981"
    assert body["tx_count"] == 0

    duplicate = client.post("/api/tags", json={"name": "pets", "color": None})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    invalid = client.post("/api/tags", json={"name": "Outra", "color": "red"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_patch_tag_edits_partial_fields_and_reports_errors(client):
    items = _items(client)
    saude_id = next(item["id"] for item in items if item["name"] == "Saúde")

    renamed = client.patch(f"/api/tags/{saude_id}", json={"name": "Saúde e Bem-estar"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Saúde e Bem-estar"
    assert renamed.json()["color"] == "#3B82F6"

    cleared = client.patch(f"/api/tags/{saude_id}", json={"color": None})
    assert cleared.status_code == 200
    assert cleared.json()["color"] is None

    conflict = client.patch(f"/api/tags/{saude_id}", json={"name": "lazer"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "conflict"

    invalid = client.patch(f"/api/tags/{saude_id}", json={"color": "ff0000"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    missing = client.patch("/api/tags/9999", json={"name": "Nada"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_delete_tag_unlinks_transactions_and_returns_count(client, tmp_db):
    _seed_account(tmp_db)
    tag = client.post("/api/tags", json={"name": "Pets", "color": "#10B981"}).json()
    tagged_a = _insert_tx(tmp_db, "web-tags-delete-1")
    tagged_b = _insert_tx(tmp_db, "web-tags-delete-2")
    tmp_db._conn.execute("UPDATE transactions SET tag_id=? WHERE id=?", (tag["id"], tagged_a.id))
    tmp_db._conn.execute("UPDATE transactions SET tag_id=? WHERE id=?", (tag["id"], tagged_b.id))
    tmp_db._conn.commit()

    deleted = client.delete(f"/api/tags/{tag['id']}")

    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_id": tag["id"], "untagged": 2}
    assert tmp_db.count_transactions() == 2
    assert [
        row["tag_id"]
        for row in tmp_db._conn.execute("SELECT tag_id FROM transactions ORDER BY external_id")
    ] == [None, None]

    missing = client.delete(f"/api/tags/{tag['id']}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_patch_transaction_tag_sets_clears_and_validates(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db, "web-tags-patch-1")
    tag_id = next(item["id"] for item in _items(client) if item["name"] == "Lazer")

    tagged = client.patch(f"/api/transactions/{tx.id}", json={"tag_id": tag_id})
    assert tagged.status_code == 200
    assert tagged.json()["tag_id"] == tag_id
    assert tmp_db._conn.execute(
        "SELECT tag_id FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()["tag_id"] == tag_id

    invalid = client.patch(f"/api/transactions/{tx.id}", json={"tag_id": 9999})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    cleared = client.patch(f"/api/transactions/{tx.id}", json={"tag_id": None})
    assert cleared.status_code == 200
    assert cleared.json()["tag_id"] is None

    missing = client.patch("/api/transactions/missing", json={"tag_id": tag_id})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
