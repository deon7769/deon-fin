from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.storage import Account, Transaction
from src.web.repositories import buckets_repo, profile_repo, tags_repo, transactions_repo


def test_recompute_reference_months_updates_all_transactions(tmp_db):
    tmp_db.upsert_account(Account(id="acc-1", source="csv", type="CHECKING"))
    tmp_db.insert_transactions(
        [
            Transaction(
                account_id="acc-1",
                posted_at=date(2026, 6, 14),
                amount=Decimal("-10.00"),
                description="Before cycle",
                source="csv",
            ),
            Transaction(
                account_id="acc-1",
                posted_at=date(2026, 6, 15),
                amount=Decimal("-20.00"),
                description="Cycle start",
                source="csv",
            ),
        ]
    )

    updated = transactions_repo.recompute_reference_months(tmp_db, start_day=15)

    assert updated == 2
    rows = tmp_db._conn.execute(
        "SELECT posted_at, reference_month FROM transactions ORDER BY posted_at"
    ).fetchall()
    assert [(row[0], row[1]) for row in rows] == [
        ("2026-06-14", "2026-05"),
        ("2026-06-15", "2026-06"),
    ]


def test_fill_missing_reference_months_leaves_existing_values_untouched(tmp_db):
    tmp_db.upsert_account(Account(id="acc-1", source="csv", type="CHECKING"))
    tx = Transaction(
        account_id="acc-1",
        posted_at=date(2026, 7, 14),
        amount=Decimal("-10.00"),
        description="Existing month",
        source="csv",
    )
    tmp_db.insert_transactions([tx])
    tmp_db._conn.execute(
        "UPDATE transactions SET reference_month='manual-month' WHERE id=?",
        (tx.id,),
    )
    tmp_db._conn.commit()

    updated = transactions_repo.fill_missing_reference_months(tmp_db, start_day=15)

    assert updated == 0
    value = tmp_db._conn.execute(
        "SELECT reference_month FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()[0]
    assert value == "manual-month"


def test_empty_bucket_and_tag_repositories_have_no_seed_data(tmp_db):
    assert buckets_repo.list_buckets(tmp_db) == []
    assert tags_repo.list_tags(tmp_db) == []


def test_get_profile_returns_default_singleton_idempotently(tmp_db, monkeypatch):
    monkeypatch.setattr(
        profile_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(profile_repo.mnt, "load_family_profile", lambda: None)

    first = profile_repo.get_profile(tmp_db)
    second = profile_repo.get_profile(tmp_db)

    assert first == second
    assert first["id"] == 1
    assert first["financial_month_start_day"] == 1
    assert first["name"] == ""
    assert first["email"] == ""
    assert first["goals_text"] == ""
    assert first["monthly_income"] == 0.0
    assert first["initials"] == "?"

    count = tmp_db._conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0]
    assert count == 1
