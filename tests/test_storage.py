from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.storage import Account, Transaction


def test_account_upsert_idempotent(tmp_db):
    acc = Account(id="csv:test:1", source="csv", institution="Test", name="x", type="CHECKING")
    tmp_db.upsert_account(acc)
    tmp_db.upsert_account(acc)
    rows = tmp_db.list_accounts()
    assert len(rows) == 1
    assert rows[0]["id"] == "csv:test:1"


def test_transaction_dedup_via_fingerprint(tmp_db):
    tmp_db.upsert_account(Account(id="ofx:bb:1", source="ofx"))
    tx = Transaction(
        account_id="ofx:bb:1",
        posted_at=date(2026, 5, 1),
        amount=Decimal("-42.50"),
        description="UBER VIAGEM",
        source="ofx",
        external_id="ext-1",
    )
    inserted, skipped = tmp_db.insert_transactions([tx])
    assert (inserted, skipped) == (1, 0)
    inserted, skipped = tmp_db.insert_transactions([tx])
    assert (inserted, skipped) == (0, 1)


def test_transaction_dedup_without_external_id(tmp_db):
    tmp_db.upsert_account(Account(id="csv:nu:1", source="csv"))
    tx1 = Transaction(
        account_id="csv:nu:1",
        posted_at=date(2026, 5, 1),
        amount=Decimal("-15.00"),
        description="iFood",
        source="csv",
    )
    tx2 = Transaction(
        account_id="csv:nu:1",
        posted_at=date(2026, 5, 1),
        amount=Decimal("-15.00"),
        description="iFood",
        source="csv",
    )
    inserted, skipped = tmp_db.insert_transactions([tx1, tx2])
    assert (inserted, skipped) == (1, 1)
