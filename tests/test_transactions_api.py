from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Transaction
from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import savings_repo


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
    assert body["items"][0]["category_label"] == body["items"][0]["category"]

    invalid_month = client.get("/api/transactions?month=202606")
    assert invalid_month.status_code == 422
    assert invalid_month.json()["error"]["code"] == "validation_error"

    invalid_amount = client.get("/api/transactions?min=20&max=10")
    assert invalid_amount.status_code == 422
    assert invalid_amount.json()["error"]["code"] == "validation_error"

    invalid_bucket = client.get("/api/transactions?bucket_ids=abc")
    assert invalid_bucket.status_code == 422
    assert invalid_bucket.json()["error"]["code"] == "validation_error"


def test_get_transactions_translates_pluggy_category_labels(client, tmp_db):
    _seed_account(tmp_db)
    tx = Transaction(
        account_id="api-checking",
        posted_at=date(2026, 6, 20),
        amount=Decimal("-89.90"),
        description="Restaurante",
        raw_description="RESTAURANTE",
        category="Eating out",
        source="test",
        external_id="api-category-label",
    )
    tmp_db.insert_transactions([tx])
    tmp_db._conn.execute("UPDATE transactions SET reference_month='2026-06' WHERE id=?", (tx.id,))
    tmp_db._conn.commit()

    response = client.get("/api/transactions?month=2026-06")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["category"] == "Eating out"
    assert item["category_label"] == "Restaurantes"


def test_get_transactions_type_filter_excludes_neutral_movements(client, tmp_db):
    _seed_account(tmp_db)
    rows = [
        Transaction(
            account_id="api-checking",
            posted_at=date(2026, 6, 20),
            amount=Decimal("-120.00"),
            description="Mercado",
            raw_description="MERCADO",
            category="Groceries",
            source="test",
            external_id="api-type-expense-1",
        ),
        Transaction(
            account_id="api-checking",
            posted_at=date(2026, 6, 20),
            amount=Decimal("-700.00"),
            description="Pix entre contas",
            raw_description="PIX ENTRE CONTAS",
            category="Transfer - PIX",
            source="test",
            external_id="api-type-expense-2",
        ),
        Transaction(
            account_id="api-checking",
            posted_at=date(2026, 6, 20),
            amount=Decimal("-900.00"),
            description="Pagamento fatura",
            raw_description="PAGAMENTO FATURA",
            category="Credit card payment",
            source="test",
            external_id="api-type-expense-3",
        ),
    ]
    tmp_db.insert_transactions(rows)
    tmp_db._conn.execute("UPDATE transactions SET reference_month='2026-06'")
    tmp_db._conn.commit()

    response = client.get("/api/transactions?month=2026-06&type=expense")

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [rows[0].id]
    assert body["summary"] == {"income": 0.0, "expense": 120.0, "balance": -120.0}


def test_get_transactions_quality_filter_returns_actionable_missing_tag_rows(client, tmp_db):
    _seed_account(tmp_db)
    tagged = _insert_tx(tmp_db, external_id="api-quality-1")
    untagged = _insert_tx(tmp_db, external_id="api-quality-2")
    transfer = Transaction(
        account_id="api-checking",
        posted_at=date(2026, 6, 20),
        amount=Decimal("-500.00"),
        description="Pix proprio",
        raw_description="PIX PROPRIO",
        category="Transfer - PIX",
        source="test",
        external_id="api-quality-3",
    )
    tmp_db.insert_transactions([transfer])
    tmp_db._conn.execute("UPDATE transactions SET reference_month='2026-06'")
    tag_id = client.get("/api/tags").json()["items"][0]["id"]
    tmp_db._conn.execute(
        "UPDATE transactions SET tag_id=?, tag_source='manual' WHERE id=?",
        (tag_id, tagged.id),
    )
    tmp_db._conn.commit()

    response = client.get("/api/transactions?month=2026-06&quality=missing_tag")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == untagged.id
    assert body["summary"] == {"income": 0.0, "expense": 42.5, "balance": -42.5}


def test_get_transactions_filters_internal_transfers(client, tmp_db):
    _seed_account(tmp_db, account_id="api-main")
    _seed_account(tmp_db, account_id="api-reserve")
    rows = [
        Transaction(
            account_id="api-main",
            posted_at=date(2026, 6, 20),
            amount=Decimal("-300.00"),
            description="Pix enviado reserva",
            raw_description="PIX ENVIADO RESERVA",
            category="Transfer - PIX",
            source="test",
            external_id="api-internal-transfer-1",
        ),
        Transaction(
            account_id="api-reserve",
            posted_at=date(2026, 6, 20),
            amount=Decimal("300.00"),
            description="Pix recebido principal",
            raw_description="PIX RECEBIDO PRINCIPAL",
            category="Transfer - PIX",
            source="test",
            external_id="api-internal-transfer-2",
        ),
        Transaction(
            account_id="api-main",
            posted_at=date(2026, 6, 20),
            amount=Decimal("-90.00"),
            description="Mercado",
            raw_description="MERCADO",
            category="Groceries",
            source="test",
            external_id="api-internal-transfer-3",
        ),
    ]
    tmp_db.insert_transactions(rows)
    tmp_db._conn.execute("UPDATE transactions SET reference_month='2026-06'")
    tmp_db._conn.commit()

    response = client.get("/api/transactions?month=2026-06&internal_transfer=only")

    assert response.status_code == 200
    body = response.json()
    assert {item["id"] for item in body["items"]} == {rows[0].id, rows[1].id}
    assert body["summary"] == {"income": 0.0, "expense": 0.0, "balance": 0.0}


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
    assert body["tag_source"] == "manual"
    assert body["hidden"] is True
    assert body["note"] == "Conferir depois"
    assert body["reference_month"] == "2026-07"
    row = tmp_db._conn.execute(
        """
        SELECT bucket_id, bucket_source, tag_id, tag_source, hidden, note, reference_month
          FROM transactions
         WHERE id=?
        """,
        (tx.id,),
    ).fetchone()
    assert tuple(row) == (
        bucket_id,
        "manual",
        tag_id,
        "manual",
        1,
        "Conferir depois",
        "2026-07",
    )


def test_patch_and_filter_transaction_savings_goal(client, tmp_db):
    _seed_account(tmp_db)
    tx = _insert_tx(tmp_db, external_id="api-savings-goal-1")
    other = _insert_tx(tmp_db, external_id="api-savings-goal-2")
    goal = savings_repo.create_goal(
        tmp_db,
        name="Viagem",
        target_amount=3000,
        term_months=6,
    )

    tagged = client.patch(
        f"/api/transactions/{tx.id}",
        json={"savings_goal_id": goal["id"]},
    )

    assert tagged.status_code == 200
    assert tagged.json()["savings_goal_id"] == goal["id"]
    assert tagged.json()["savings_goal_name"] == "Viagem"
    filtered = client.get(f"/api/transactions?savings_goal_id={goal['id']}")
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [tx.id]

    cleared = client.patch(f"/api/transactions/{tx.id}", json={"savings_goal_id": None})
    assert cleared.status_code == 200
    assert cleared.json()["savings_goal_id"] is None
    assert client.get(f"/api/transactions?savings_goal_id={goal['id']}").json()["items"] == []

    invalid = client.patch(f"/api/transactions/{other.id}", json={"savings_goal_id": 9999})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


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


def test_post_transaction_tag_propagates_to_similar(client, tmp_db):
    _seed_account(tmp_db)
    target = _insert_tx(tmp_db, external_id="api-tag-rule-1")
    similar = _insert_tx(tmp_db, external_id="api-tag-rule-2")
    different = Transaction(
        account_id="api-checking",
        posted_at=date(2026, 6, 20),
        amount=Decimal("-12.00"),
        description="Uber API",
        raw_description="UBER API",
        category="Taxi and ride-hailing",
        source="test",
        external_id="api-tag-rule-3",
    )
    manual = _insert_tx(tmp_db, external_id="api-tag-rule-4")
    tmp_db.insert_transactions([different])
    tag_id = client.get("/api/tags").json()["items"][0]["id"]
    manual_tag_id = client.get("/api/tags").json()["items"][1]["id"]
    tmp_db._conn.execute(
        "UPDATE transactions SET tag_id=?, tag_source='manual' WHERE id=?",
        (manual_tag_id, manual.id),
    )
    tmp_db._conn.commit()

    response = client.post(
        f"/api/transactions/{target.id}/tag",
        json={"tag_id": tag_id, "apply_to_similar": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tag_id"] == tag_id
    assert body["tag_source"] == "manual"
    assert body["similar_ids"] == [similar.id]
    rows = {
        row["id"]: (row["tag_id"], row["tag_source"])
        for row in tmp_db._conn.execute(
            "SELECT id, tag_id, tag_source FROM transactions ORDER BY external_id"
        )
    }
    assert rows[target.id] == (tag_id, "manual")
    assert rows[similar.id] == (tag_id, "rule")
    assert rows[different.id] == (None, None)
    assert rows[manual.id] == (manual_tag_id, "manual")

    invalid = client.post(
        f"/api/transactions/{target.id}/tag",
        json={"tag_id": 9999, "apply_to_similar": True},
    )
    assert invalid.status_code == 422

    missing = client.post(
        "/api/transactions/missing/tag",
        json={"tag_id": tag_id, "apply_to_similar": True},
    )
    assert missing.status_code == 404


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
