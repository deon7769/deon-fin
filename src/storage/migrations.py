from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from typing import Any

from src.domain.investment_questions import DEFAULT_ASSET_QUESTIONS


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


def _json_obj(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _last4(*values: Any) -> str | None:
    for value in values:
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if len(digits) >= 4:
            return digits[-4:]
    return None


def m0012_account_connection_metadata(conn: sqlite3.Connection) -> None:
    _add_column(conn, "accounts", "sort_order", "INTEGER")
    _add_column(conn, "accounts", "pluggy_item_id", "TEXT")
    _add_column(conn, "account_balances", "brand", "TEXT")
    _add_column(conn, "account_balances", "last4", "TEXT")

    items = {
        row[0]: {"status": row[1], "last_synced_at": row[2], "updated_at": row[3]}
        for row in conn.execute(
            "SELECT id, status, last_synced_at, updated_at FROM pluggy_items"
        ).fetchall()
    }

    for account_id, source, account_type, metadata_json in conn.execute(
        "SELECT id, source, type, metadata_json FROM accounts"
    ).fetchall():
        meta = _json_obj(metadata_json)
        item_id = meta.get("itemId") or meta.get("item_id")
        if item_id:
            conn.execute(
                "UPDATE accounts SET pluggy_item_id=? WHERE id=?",
                (str(item_id), account_id),
            )

        if source != "pluggy":
            continue

        credit_data = meta.get("creditData") if isinstance(meta.get("creditData"), dict) else {}
        bank_data = meta.get("bankData") if isinstance(meta.get("bankData"), dict) else {}
        is_credit = (account_type or "").upper() in {"CREDIT", "CREDIT_CARD"}
        credit_limit = _number(
            credit_data.get("creditLimit")
            or credit_data.get("credit_limit")
            or credit_data.get("limit")
        )
        available = _number(
            credit_data.get("availableCreditLimit")
            or credit_data.get("available_credit_limit")
            or credit_data.get("available")
        )
        used = (
            round(credit_limit - available, 2)
            if credit_limit is not None and available is not None
            else _number(credit_data.get("balance") or credit_data.get("used"))
        )
        balance = None if is_credit else _number(meta.get("balance"))
        brand = (
            credit_data.get("brand")
            or credit_data.get("network")
            or meta.get("brand")
            or meta.get("network")
        )
        last4 = _last4(
            meta.get("last4"),
            meta.get("lastFourDigits"),
            meta.get("number"),
            credit_data.get("last4"),
            credit_data.get("lastFourDigits"),
            credit_data.get("number"),
            bank_data.get("transferNumber"),
        )
        item = items.get(str(item_id)) if item_id else None
        sync_status = (item or {}).get("status") or "UPDATED"
        last_sync_at = (item or {}).get("last_synced_at") or (item or {}).get("updated_at")

        conn.execute(
            """
            INSERT INTO account_balances (
                account_id, balance, credit_limit, used, available, brand, last4,
                last_sync_at, sync_status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(account_id) DO UPDATE SET
                balance=excluded.balance,
                credit_limit=excluded.credit_limit,
                used=excluded.used,
                available=excluded.available,
                brand=excluded.brand,
                last4=excluded.last4,
                last_sync_at=COALESCE(excluded.last_sync_at, account_balances.last_sync_at),
                sync_status=COALESCE(excluded.sync_status, account_balances.sync_status),
                updated_at=datetime('now')
            """,
            (
                account_id,
                balance,
                credit_limit,
                used,
                available,
                str(brand).strip() if brand else None,
                last4,
                last_sync_at,
                sync_status,
            ),
        )


def m0013_savings_goals(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS savings_goals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            target_amount REAL NOT NULL,
            term_months   INTEGER NOT NULL DEFAULT 12,
            saved_amount  REAL NOT NULL DEFAULT 0,
            priority      INTEGER NOT NULL DEFAULT 99,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS savings_goals_import_state (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            imported_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def m0014_portfolio(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_assets (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_class      TEXT NOT NULL,
            ticker           TEXT,
            name             TEXT,
            quantity         REAL NOT NULL DEFAULT 0,
            source           TEXT NOT NULL DEFAULT 'manual',
            external_id      TEXT,
            manual_value     REAL,
            current_value    REAL,
            unit_price       REAL,
            currency         TEXT DEFAULT 'BRL',
            provider_type    TEXT,
            provider_subtype TEXT,
            status           TEXT,
            as_of_date       TEXT,
            metadata_json    TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_assets_external
          ON portfolio_assets(source, external_id)
         WHERE external_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_portfolio_assets_class
          ON portfolio_assets(asset_class, ticker)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id             TEXT PRIMARY KEY,
            asset_id       INTEGER NOT NULL REFERENCES portfolio_assets(id) ON DELETE CASCADE,
            source         TEXT NOT NULL,
            external_id    TEXT,
            type           TEXT,
            movement_type  TEXT,
            trade_date     TEXT,
            posted_at      TEXT,
            quantity       REAL,
            unit_value     REAL,
            amount         REAL,
            net_amount     REAL,
            description    TEXT,
            metadata_json  TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_transactions_external
          ON portfolio_transactions(source, external_id)
         WHERE external_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_asset
          ON portfolio_transactions(asset_id, posted_at)
        """
    )


def m0015_portfolio_quotes_and_manual_adjustments(conn: sqlite3.Connection) -> None:
    _add_column(conn, "portfolio_assets", "manually_adjusted", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "portfolio_assets", "manual_adjusted_at", "TEXT")
    _add_column(conn, "portfolio_assets", "price_source", "TEXT")
    _add_column(conn, "portfolio_assets", "price_updated_at", "TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quote_cache (
            symbol      TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            price       REAL,
            currency    TEXT DEFAULT 'BRL',
            fetched_at  TEXT NOT NULL,
            PRIMARY KEY (symbol, asset_class)
        )
        """
    )


def m0016_investment_allocation_targets(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS allocation_targets (
            asset_class TEXT PRIMARY KEY,
            target_pct  REAL NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS investment_profile (
            id            INTEGER PRIMARY KEY CHECK (id = 1),
            perfil        TEXT,
            ultimo_aporte REAL,
            updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    for asset_class in (
        "acoes_nac",
        "acoes_int",
        "etf",
        "fii",
        "reit",
        "cripto",
        "rf",
        "rf_int",
    ):
        conn.execute(
            """
            INSERT OR IGNORE INTO allocation_targets (asset_class, target_pct)
            VALUES (?, 0)
            """,
            (asset_class,),
        )
    conn.execute(
        """
        INSERT OR IGNORE INTO investment_profile (id, perfil)
        VALUES (1, 'custom')
        """
    )


def m0017_asset_questions_answers(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_questions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            diagram_type TEXT NOT NULL CHECK (diagram_type IN ('acoes', 'imobiliario')),
            criterio     TEXT,
            pergunta     TEXT NOT NULL,
            peso         REAL NOT NULL DEFAULT 1,
            sort_order   INTEGER NOT NULL DEFAULT 0,
            ativo        INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_asset_questions_diagram_order
          ON asset_questions(diagram_type, ativo, sort_order, id)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_answers (
            asset_id    INTEGER NOT NULL REFERENCES portfolio_assets(id) ON DELETE CASCADE,
            question_id INTEGER NOT NULL REFERENCES asset_questions(id) ON DELETE CASCADE,
            resposta    INTEGER NOT NULL DEFAULT 0 CHECK (resposta IN (0, 1)),
            PRIMARY KEY (asset_id, question_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_asset_answers_question
          ON asset_answers(question_id)
        """
    )

    for diagram_type, questions in DEFAULT_ASSET_QUESTIONS.items():
        existing = conn.execute(
            "SELECT COUNT(*) FROM asset_questions WHERE diagram_type=?",
            (diagram_type,),
        ).fetchone()[0]
        if existing:
            continue
        for question in questions:
            conn.execute(
                """
                INSERT INTO asset_questions (
                    diagram_type, criterio, pergunta, peso, sort_order, ativo
                )
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    diagram_type,
                    question["criterio"],
                    question["pergunta"],
                    question["peso"],
                    question["sort_order"],
                ),
            )


def m0018_investment_etf_asset_class(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO allocation_targets (asset_class, target_pct)
        VALUES ('etf', 0)
        """
    )
    conn.execute(
        """
        UPDATE portfolio_assets
           SET asset_class='etf',
               updated_at=datetime('now')
         WHERE asset_class='fii'
           AND UPPER(COALESCE(ticker, name, '')) IN ('AUVP11')
        """
    )


def m0019_system_total_settings(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS account_total_settings (
            account_id            TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,
            include_balance       INTEGER NOT NULL DEFAULT 1 CHECK (include_balance IN (0, 1)),
            include_transactions  INTEGER NOT NULL DEFAULT 1 CHECK (include_transactions IN (0, 1)),
            updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS movement_total_settings (
            movement_type       TEXT PRIMARY KEY,
            label               TEXT NOT NULL,
            include_in_totals   INTEGER NOT NULL DEFAULT 1 CHECK (include_in_totals IN (0, 1)),
            sort_order          INTEGER NOT NULL DEFAULT 0,
            updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


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
    (12, "account_connection_metadata", m0012_account_connection_metadata),
    (13, "savings_goals", m0013_savings_goals),
    (14, "portfolio", m0014_portfolio),
    (15, "portfolio_quotes_and_manual_adjustments", m0015_portfolio_quotes_and_manual_adjustments),
    (16, "investment_allocation_targets", m0016_investment_allocation_targets),
    (17, "asset_questions_answers", m0017_asset_questions_answers),
    (18, "investment_etf_asset_class", m0018_investment_etf_asset_class),
    (19, "system_total_settings", m0019_system_total_settings),
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
