from __future__ import annotations

from datetime import date

from src.agent.buckets import apply_buckets_to_database
from src.agent.tags import apply_tags_to_database
from src.importers.pluggy_sync import sync_pluggy_item
from src.storage import Database
from src.web.repositories import buckets_repo, tags_repo, transactions_repo


class FakePluggy:
    def list_accounts(self, item_id):
        assert item_id == "item-1"
        return [
            {
                "id": "bank-1",
                "itemId": "item-1",
                "name": "Conta Corrente",
                "type": "BANK",
                "currencyCode": "BRL",
                "balance": 58.77,
                "bankData": {"transferNumber": "077/0001/12345-6"},
            },
            {
                "id": "card-1",
                "itemId": "item-1",
                "name": "Cartao Black",
                "type": "CREDIT",
                "currencyCode": "BRL",
                "number": "550000001234",
                "creditData": {
                    "brand": "MASTERCARD",
                    "creditLimit": 4000.0,
                    "availableCreditLimit": 3250.5,
                },
            },
        ]

    def list_transactions(self, account_id, from_date=None):
        if account_id == "bank-1":
            return [
                {
                    "id": "tx-bank-1",
                    "date": "2026-06-20T10:00:00",
                    "amount": -10.0,
                    "description": "Compra",
                    "descriptionRaw": "Compra",
                    "category": "Groceries",
                    "type": "DEBIT",
                    "status": "POSTED",
                }
            ]
        return []


def test_sync_pluggy_item_populates_account_balances(tmp_db: Database):
    tmp_db.upsert_pluggy_item("item-1", connector_name="Banco Inter", status="UPDATED")

    results = sync_pluggy_item(FakePluggy(), tmp_db, "item-1", since=date(2026, 6, 1))

    assert [result.account_id for result in results] == ["pluggy:bank-1", "pluggy:card-1"]
    bank_account = tmp_db._conn.execute(
        "SELECT pluggy_item_id FROM accounts WHERE id='pluggy:bank-1'"
    ).fetchone()
    bank_balance = tmp_db._conn.execute(
        """
        SELECT balance, credit_limit, used, available, sync_status, last_sync_at
          FROM account_balances
         WHERE account_id='pluggy:bank-1'
        """
    ).fetchone()
    card_balance = tmp_db._conn.execute(
        """
        SELECT balance, credit_limit, used, available, brand, last4, sync_status
          FROM account_balances
         WHERE account_id='pluggy:card-1'
        """
    ).fetchone()

    assert bank_account["pluggy_item_id"] == "item-1"
    assert bank_balance["balance"] == 58.77
    assert bank_balance["credit_limit"] is None
    assert bank_balance["used"] is None
    assert bank_balance["available"] is None
    assert bank_balance["sync_status"] == "UPDATED"
    assert bank_balance["last_sync_at"] is not None

    assert card_balance["balance"] is None
    assert card_balance["credit_limit"] == 4000.0
    assert card_balance["available"] == 3250.5
    assert card_balance["used"] == 749.5
    assert card_balance["brand"] == "MASTERCARD"
    assert card_balance["last4"] == "1234"
    assert card_balance["sync_status"] == "UPDATED"
    assert tmp_db.count_transactions("pluggy:bank-1") == 1


def test_sync_pluggy_item_preserves_manual_transaction_classification(tmp_db: Database):
    tmp_db.upsert_pluggy_item("item-1", connector_name="Banco Inter", status="UPDATED")
    sync_pluggy_item(FakePluggy(), tmp_db, "item-1", since=date(2026, 6, 1))

    buckets_repo.seed_buckets(tmp_db)
    bucket_id = int(
        tmp_db._conn.execute(
            "SELECT id FROM budget_buckets WHERE key='metas'"
        ).fetchone()["id"]
    )
    tag_id = int(tags_repo.create_tag(tmp_db, name="Reserva", bucket_id=bucket_id)["id"])
    tx_id = tmp_db._conn.execute(
        "SELECT id FROM transactions WHERE external_id='tx-bank-1'"
    ).fetchone()["id"]

    transactions_repo.set_bucket(tmp_db, tx_id, bucket_id=bucket_id)
    transactions_repo.set_tag(tmp_db, tx_id, tag_id=tag_id)

    sync_pluggy_item(FakePluggy(), tmp_db, "item-1", since=date(2026, 6, 1))
    apply_buckets_to_database(tmp_db)
    apply_tags_to_database(tmp_db)

    row = tmp_db._conn.execute(
        """
        SELECT bucket_id, bucket_source, tag_id, tag_source
          FROM transactions
         WHERE id=?
        """,
        (tx_id,),
    ).fetchone()
    assert row["bucket_id"] == bucket_id
    assert row["bucket_source"] == "manual"
    assert row["tag_id"] == tag_id
    assert row["tag_source"] == "manual"
    assert tmp_db.count_transactions("pluggy:bank-1") == 1
