from __future__ import annotations

import sqlite3
from collections.abc import Callable


Migration = Callable[[sqlite3.Connection], None]


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _add_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id         INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _applied_ids(conn: sqlite3.Connection) -> set[int]:
    rows = conn.execute("SELECT id FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def m0001_tx_bucket_columns(conn: sqlite3.Connection) -> None:
    _add_column(conn, "transactions", "bucket_id", "INTEGER")
    _add_column(conn, "transactions", "bucket_source", "TEXT")


def m0002_tx_tag_column(conn: sqlite3.Connection) -> None:
    _add_column(conn, "transactions", "tag_id", "INTEGER")


def m0003_tx_reference_month(conn: sqlite3.Connection) -> None:
    _add_column(conn, "transactions", "reference_month", "TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tx_reference_month "
        "ON transactions(reference_month)"
    )


def m0004_tx_hidden_note(conn: sqlite3.Connection) -> None:
    _add_column(conn, "transactions", "hidden", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "transactions", "note", "TEXT")


def m0005_budget_buckets(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_buckets (
            id            INTEGER PRIMARY KEY,
            key           TEXT UNIQUE NOT NULL,
            name          TEXT NOT NULL,
            color         TEXT,
            planned_kind  TEXT,
            planned_value REAL,
            sort_order    INTEGER NOT NULL DEFAULT 0,
            is_system     INTEGER NOT NULL DEFAULT 1
        )
        """
    )


def m0006_tags(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id         INTEGER PRIMARY KEY,
            name       TEXT UNIQUE NOT NULL,
            color      TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def m0007_bucket_rules(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bucket_rules (
            id         INTEGER PRIMARY KEY,
            match_key  TEXT UNIQUE NOT NULL,
            bucket_id  INTEGER REFERENCES budget_buckets(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def m0008_profile(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS profile (
            id                        INTEGER PRIMARY KEY CHECK (id = 1),
            name                      TEXT,
            email                     TEXT,
            monthly_income            REAL,
            financial_month_start_day INTEGER NOT NULL DEFAULT 1,
            goals_text                TEXT,
            updated_at                TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def m0009_account_balances(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS account_balances (
            account_id   TEXT PRIMARY KEY REFERENCES accounts(id),
            balance      REAL,
            credit_limit REAL,
            used         REAL,
            available    REAL,
            last_sync_at TEXT,
            sync_status  TEXT,
            updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def m0010_backfill_reference_month(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE transactions
           SET reference_month = substr(posted_at, 1, 7)
         WHERE reference_month IS NULL
           AND posted_at IS NOT NULL
        """
    )


def m0011_tx_filter_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_tag_id ON transactions(tag_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_bucket_id ON transactions(bucket_id)")


MIGRATIONS: list[tuple[int, str, Migration]] = [
    (1, "tx_bucket_columns", m0001_tx_bucket_columns),
    (2, "tx_tag_column", m0002_tx_tag_column),
    (3, "tx_reference_month", m0003_tx_reference_month),
    (4, "tx_hidden_note", m0004_tx_hidden_note),
    (5, "budget_buckets", m0005_budget_buckets),
    (6, "tags", m0006_tags),
    (7, "bucket_rules", m0007_bucket_rules),
    (8, "profile", m0008_profile),
    (9, "account_balances", m0009_account_balances),
    (10, "backfill_reference_month", m0010_backfill_reference_month),
    (11, "tx_filter_indexes", m0011_tx_filter_indexes),
]


def apply_migrations(conn: sqlite3.Connection) -> int:
    ran = 0

    try:
        conn.execute("BEGIN IMMEDIATE")
        _ensure_migrations_table(conn)
        applied = _applied_ids(conn)

        for migration_id, name, migration in MIGRATIONS:
            if migration_id in applied:
                continue
            migration(conn)
            cur = conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (id, name) VALUES (?, ?)",
                (migration_id, name),
            )
            ran += cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    return ran
