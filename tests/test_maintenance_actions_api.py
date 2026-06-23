from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Transaction
from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import buckets_repo, tags_repo


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
    db.upsert_account(
        Account(
            id="maint-bank",
            source="test",
            institution="Banco Teste",
            name="Conta Principal",
            type="CHECKING",
        )
    )


def _insert_tx(
    db,
    *,
    external_id: str,
    amount: str = "-42.50",
    description: str = "Mercado Teste",
    category: str | None = "Groceries",
    posted_at: date = date(2026, 6, 20),
) -> Transaction:
    tx = Transaction(
        account_id="maint-bank",
        posted_at=posted_at,
        amount=Decimal(amount),
        description=description,
        raw_description=description.upper(),
        category=category,
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    db._conn.execute(
        "UPDATE transactions SET reference_month=? WHERE id=?",
        (posted_at.strftime("%Y-%m"), tx.id),
    )
    db._conn.commit()
    return tx


def test_maintenance_reprocess_classification_runs_bucket_and_tag_classifiers(
    client,
    tmp_db,
    monkeypatch,
):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db, external_id="maint-reprocess-1")
    monkeypatch.setattr(
        "src.agent.maintenance.load_overrides",
        lambda: {"categorias_pt": {"groceries": "Mercado"}, "recorrencias": []},
    )

    response = client.post("/api/maintenance/classification/reprocess")

    assert response.status_code == 200
    body = response.json()
    assert body["changed"] == 2
    assert body["bucket"]["by_map"] == 1
    assert body["tag"]["by_map"] == 1
    row = tmp_db._conn.execute(
        "SELECT bucket_id, bucket_source, tag_id, tag_source FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()
    assert row["bucket_id"] is not None
    assert row["bucket_source"] == "auto"
    assert row["tag_id"] is not None
    assert row["tag_source"] == "auto"


def test_maintenance_bulk_preview_and_apply_updates_classification_queue(
    client,
    tmp_db,
):
    _seed_account(tmp_db)
    tags_repo.seed_tags(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    target_tag = tags_repo.list_tags(tmp_db)[0]
    target_bucket = next(
        bucket for bucket in buckets_repo.list_buckets(tmp_db) if bucket["key"] == "conforto"
    )
    first = _insert_tx(tmp_db, external_id="maint-bulk-1", description="Pet shop um", category="Pet Shops")
    second = _insert_tx(tmp_db, external_id="maint-bulk-2", description="Pet shop dois", category="Pet Shops")
    _insert_tx(
        tmp_db,
        external_id="maint-bulk-other-month",
        description="Pet shop outro mes",
        category="Pet Shops",
        posted_at=date(2026, 7, 5),
    )

    tag_preview = client.post(
        "/api/maintenance/classification/bulk-preview",
        json={"kind": "tag", "target_id": target_tag["id"], "month": "2026-06"},
    )

    assert tag_preview.status_code == 200
    tag_body = tag_preview.json()
    assert tag_body["kind"] == "tag"
    assert tag_body["target_name"] == target_tag["name"]
    assert tag_body["total"] == 2
    assert {item["id"] for item in tag_body["items"]} == {first.id, second.id}
    assert tag_body["total_abs"] == 85.0

    tag_apply = client.post(
        "/api/maintenance/classification/bulk-apply",
        json={"kind": "tag", "target_id": target_tag["id"], "month": "2026-06"},
    )

    assert tag_apply.status_code == 200
    assert tag_apply.json()["updated"] == 2
    rows = {
        row["id"]: (row["tag_id"], row["tag_source"])
        for row in tmp_db._conn.execute("SELECT id, tag_id, tag_source FROM transactions")
    }
    assert rows[first.id] == (target_tag["id"], "manual")
    assert rows[second.id] == (target_tag["id"], "manual")

    bucket_preview = client.post(
        "/api/maintenance/classification/bulk-preview",
        json={"kind": "bucket", "target_id": target_bucket["id"], "month": "2026-06"},
    )
    assert bucket_preview.status_code == 200
    assert bucket_preview.json()["total"] == 2

    bucket_apply = client.post(
        "/api/maintenance/classification/bulk-apply",
        json={"kind": "bucket", "target_id": target_bucket["id"], "month": "2026-06"},
    )
    assert bucket_apply.status_code == 200
    assert bucket_apply.json()["updated"] == 2
    assert {
        row["id"]: (row["bucket_id"], row["bucket_source"])
        for row in tmp_db._conn.execute("SELECT id, bucket_id, bucket_source FROM transactions")
        if row["id"] in {first.id, second.id}
    } == {
        first.id: (target_bucket["id"], "manual"),
        second.id: (target_bucket["id"], "manual"),
    }


def test_maintenance_bulk_preview_validates_target(client, tmp_db):
    _seed_account(tmp_db)
    _insert_tx(tmp_db, external_id="maint-bulk-invalid")

    response = client.post(
        "/api/maintenance/classification/bulk-preview",
        json={"kind": "tag", "target_id": 9999, "month": "2026-06"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_maintenance_classification_rules_can_be_listed_updated_and_deleted(client, tmp_db):
    tags_repo.seed_tags(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    tag = tags_repo.list_tags(tmp_db)[0]
    next_tag = tags_repo.list_tags(tmp_db)[1]
    bucket = buckets_repo.list_buckets(tmp_db)[0]
    tmp_db._conn.execute(
        "INSERT INTO tag_rules (match_key, tag_id) VALUES (?, ?)",
        ("-ifood mercado", tag["id"]),
    )
    tmp_db._conn.execute(
        "INSERT INTO bucket_rules (match_key, bucket_id) VALUES (?, ?)",
        ("-uber viagem", bucket["id"]),
    )
    tmp_db._conn.commit()

    listed = client.get("/api/maintenance/classification/rules")

    assert listed.status_code == 200
    body = listed.json()
    assert body["tag_rules"] == [
        {
            "kind": "tag",
            "match_key": "-ifood mercado",
            "target_id": tag["id"],
            "target_name": tag["name"],
            "target_color": tag["color"],
        }
    ]
    assert body["bucket_rules"] == [
        {
            "kind": "bucket",
            "match_key": "-uber viagem",
            "target_id": bucket["id"],
            "target_name": bucket["name"],
            "target_color": bucket["color"],
        }
    ]

    updated = client.patch(
        "/api/maintenance/classification/rules",
        json={"kind": "tag", "match_key": "-ifood mercado", "target_id": next_tag["id"]},
    )

    assert updated.status_code == 200
    assert updated.json()["tag_rules"][0]["target_id"] == next_tag["id"]

    deleted = client.patch(
        "/api/maintenance/classification/rules",
        json={"kind": "bucket", "match_key": "-uber viagem", "target_id": None},
    )

    assert deleted.status_code == 200
    assert deleted.json()["bucket_rules"] == []


def test_maintenance_classification_rules_validate_targets(client, tmp_db):
    response = client.patch(
        "/api/maintenance/classification/rules",
        json={"kind": "tag", "match_key": "-ifood mercado", "target_id": 9999},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
