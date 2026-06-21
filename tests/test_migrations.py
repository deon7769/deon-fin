from __future__ import annotations

import sqlite3
from pathlib import Path

from src.storage.db import SCHEMA, Database
from src.storage.migrations import _add_column, apply_migrations


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def _indexes(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA index_list({table})").fetchall()
    return {row[1] for row in rows}


def test_new_database_has_new_transaction_columns_and_tables(tmp_path: Path):
    db = Database(tmp_path / "new.db")
    conn = db._conn

    assert {
        "bucket_id",
        "bucket_source",
        "tag_id",
        "reference_month",
        "hidden",
        "note",
    }.issubset(_columns(conn, "transactions"))

    assert {
        "schema_migrations",
        "budget_buckets",
        "tags",
        "bucket_rules",
        "profile",
        "account_balances",
    }.issubset(_tables(conn))

    ids = [
        row[0]
        for row in conn.execute("SELECT id FROM schema_migrations ORDER BY id").fetchall()
    ]
    assert ids == list(range(1, 12))
    assert "idx_tx_reference_month" in _indexes(conn, "transactions")
    assert "idx_tx_tag_id" in _indexes(conn, "transactions")
    assert "idx_tx_bucket_id" in _indexes(conn, "transactions")

    hidden = {
        row[1]: row for row in conn.execute("PRAGMA table_info(transactions)").fetchall()
    }["hidden"]
    assert hidden[3] == 1
    assert hidden[4] == "0"
    db.close()


def test_apply_migrations_is_idempotent(tmp_db):
    first_count = tmp_db._conn.execute(
        "SELECT COUNT(*) FROM schema_migrations"
    ).fetchone()[0]

    assert apply_migrations(tmp_db._conn) == 0
    assert apply_migrations(tmp_db._conn) == 0

    second_count = tmp_db._conn.execute(
        "SELECT COUNT(*) FROM schema_migrations"
    ).fetchone()[0]
    assert second_count == first_count


def test_backfill_reference_month_on_legacy_database(tmp_path: Path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        INSERT INTO accounts (id, source, institution, name, type)
        VALUES ('acc-1', 'csv', 'Banco', 'Conta', 'CHECKING')
        """
    )
    conn.execute(
        """
        INSERT INTO transactions (
            id, account_id, posted_at, amount, description, source
        )
        VALUES ('tx-1', 'acc-1', '2026-06-14', -42.5, 'Mercado', 'csv')
        """
    )
    conn.commit()
    conn.close()

    db = Database(path)
    value = db._conn.execute(
        "SELECT reference_month FROM transactions WHERE id='tx-1'"
    ).fetchone()[0]
    assert value == "2026-06"

    assert apply_migrations(db._conn) == 0
    value_after_second_run = db._conn.execute(
        "SELECT reference_month FROM transactions WHERE id='tx-1'"
    ).fetchone()[0]
    assert value_after_second_run == "2026-06"
    db.close()


def test_add_column_guard_is_safe_when_column_exists(tmp_db):
    _add_column(tmp_db._conn, "transactions", "note", "TEXT")
    _add_column(tmp_db._conn, "transactions", "note", "TEXT")

    assert "note" in _columns(tmp_db._conn, "transactions")


def test_apply_migrations_recovers_when_schema_migrations_was_cleared(tmp_db):
    tmp_db._conn.execute("DELETE FROM schema_migrations")
    tmp_db._conn.commit()

    assert apply_migrations(tmp_db._conn) == 11
    assert apply_migrations(tmp_db._conn) == 0

    ids = [
        row[0]
        for row in tmp_db._conn.execute(
            "SELECT id FROM schema_migrations ORDER BY id"
        ).fetchall()
    ]
    assert ids == list(range(1, 12))
