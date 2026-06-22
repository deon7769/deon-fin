from __future__ import annotations

import sqlite3
import json
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
        "savings_goals",
        "portfolio_assets",
        "portfolio_transactions",
        "quote_cache",
        "allocation_targets",
        "investment_profile",
        "asset_questions",
        "asset_answers",
    }.issubset(_tables(conn))

    ids = [
        row[0]
        for row in conn.execute("SELECT id FROM schema_migrations ORDER BY id").fetchall()
    ]
    assert ids == list(range(1, 18))
    assert "idx_tx_reference_month" in _indexes(conn, "transactions")
    assert "idx_tx_tag_id" in _indexes(conn, "transactions")
    assert "idx_tx_bucket_id" in _indexes(conn, "transactions")

    hidden = {
        row[1]: row for row in conn.execute("PRAGMA table_info(transactions)").fetchall()
    }["hidden"]
    assert hidden[3] == 1
    assert hidden[4] == "0"
    db.close()


def test_new_database_has_account_connection_columns(tmp_path: Path):
    db = Database(tmp_path / "new.db")
    conn = db._conn

    assert {"sort_order", "pluggy_item_id"}.issubset(_columns(conn, "accounts"))
    assert {"brand", "last4"}.issubset(_columns(conn, "account_balances"))
    db.close()


def test_new_database_has_savings_goals_table(tmp_path: Path):
    db = Database(tmp_path / "new.db")
    conn = db._conn

    assert {
        "id",
        "name",
        "target_amount",
        "term_months",
        "saved_amount",
        "priority",
        "created_at",
        "updated_at",
    }.issubset(_columns(conn, "savings_goals"))
    db.close()


def test_new_database_has_portfolio_tables(tmp_path: Path):
    db = Database(tmp_path / "new.db")
    conn = db._conn

    assert {
        "id",
        "asset_class",
        "ticker",
        "name",
        "quantity",
        "source",
        "external_id",
        "manual_value",
        "current_value",
        "unit_price",
        "currency",
        "provider_type",
        "provider_subtype",
        "status",
        "as_of_date",
        "metadata_json",
        "manually_adjusted",
        "manual_adjusted_at",
        "price_source",
        "price_updated_at",
        "created_at",
        "updated_at",
    }.issubset(_columns(conn, "portfolio_assets"))
    assert {
        "id",
        "asset_id",
        "source",
        "external_id",
        "type",
        "movement_type",
        "trade_date",
        "posted_at",
        "quantity",
        "unit_value",
        "amount",
        "net_amount",
        "description",
        "metadata_json",
        "created_at",
    }.issubset(_columns(conn, "portfolio_transactions"))
    assert "idx_portfolio_assets_class" in _indexes(conn, "portfolio_assets")
    assert "idx_portfolio_transactions_asset" in _indexes(conn, "portfolio_transactions")
    db.close()


def test_new_database_has_quote_cache_table(tmp_path: Path):
    db = Database(tmp_path / "new.db")
    conn = db._conn

    assert {
        "symbol",
        "asset_class",
        "price",
        "currency",
        "fetched_at",
    }.issubset(_columns(conn, "quote_cache"))

    indexes = _indexes(conn, "quote_cache")
    assert any(index.startswith("sqlite_autoindex_quote_cache") for index in indexes)
    db.close()


def test_new_database_has_investment_allocation_targets(tmp_path: Path):
    db = Database(tmp_path / "new.db")
    conn = db._conn

    assert {"asset_class", "target_pct"}.issubset(_columns(conn, "allocation_targets"))
    assert {"id", "perfil", "ultimo_aporte", "updated_at"}.issubset(_columns(conn, "investment_profile"))

    rows = conn.execute(
        "SELECT asset_class, target_pct FROM allocation_targets ORDER BY asset_class"
    ).fetchall()
    assert {row["asset_class"] for row in rows} == {
        "acoes_nac",
        "acoes_int",
        "fii",
        "reit",
        "cripto",
        "rf",
        "rf_int",
    }
    assert all(row["target_pct"] == 0 for row in rows)
    profile = conn.execute("SELECT perfil FROM investment_profile WHERE id=1").fetchone()
    assert profile["perfil"] == "custom"
    db.close()


def test_new_database_has_asset_questions_and_answers_seeded(tmp_path: Path):
    db = Database(tmp_path / "new.db")
    conn = db._conn

    assert {
        "id",
        "diagram_type",
        "criterio",
        "pergunta",
        "peso",
        "sort_order",
        "ativo",
    }.issubset(_columns(conn, "asset_questions"))
    assert {
        "asset_id",
        "question_id",
        "resposta",
    }.issubset(_columns(conn, "asset_answers"))

    rows = conn.execute(
        """
        SELECT diagram_type, COUNT(*) AS total
          FROM asset_questions
         WHERE ativo=1
         GROUP BY diagram_type
        """
    ).fetchall()
    assert {row["diagram_type"]: row["total"] for row in rows} == {
        "acoes": 5,
        "imobiliario": 5,
    }

    first_acoes = conn.execute(
        """
        SELECT criterio, pergunta, peso, sort_order
          FROM asset_questions
         WHERE diagram_type='acoes'
         ORDER BY sort_order, id
         LIMIT 1
        """
    ).fetchone()
    assert first_acoes["criterio"]
    assert "ROE" in first_acoes["pergunta"]
    assert first_acoes["peso"] == 1
    assert first_acoes["sort_order"] == 10
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


def test_backfill_account_balances_from_legacy_pluggy_metadata(tmp_path: Path):
    path = tmp_path / "legacy-accounts.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        INSERT INTO pluggy_items (id, connector_name, status, last_synced_at)
        VALUES ('item-bank', 'Banco Inter', 'UPDATED', '2026-06-20T10:00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO accounts (id, source, institution, name, type, currency, metadata_json)
        VALUES (?, 'pluggy', '077/0001/12345-6', 'Conta Corrente', 'BANK', 'BRL', ?)
        """,
        (
            "pluggy:bank",
            json.dumps(
                {
                    "itemId": "item-bank",
                    "balance": 58.77,
                    "bankData": {"transferNumber": "077/0001/12345-6"},
                }
            ),
        ),
    )
    conn.execute(
        """
        INSERT INTO accounts (id, source, institution, name, type, currency, metadata_json)
        VALUES (?, 'pluggy', 'Cartao Black', 'Cartao Black', 'CREDIT', 'BRL', ?)
        """,
        (
            "pluggy:card",
            json.dumps(
                {
                    "itemId": "item-bank",
                    "number": "550000001234",
                    "creditData": {
                        "brand": "MASTERCARD",
                        "creditLimit": 4000.0,
                        "availableCreditLimit": 3250.5,
                    },
                }
            ),
        ),
    )
    conn.commit()
    conn.close()

    db = Database(path)
    bank = db._conn.execute(
        "SELECT pluggy_item_id FROM accounts WHERE id='pluggy:bank'"
    ).fetchone()
    card_balance = db._conn.execute(
        """
        SELECT credit_limit, available, used, brand, last4, sync_status
          FROM account_balances
         WHERE account_id='pluggy:card'
        """
    ).fetchone()
    bank_balance = db._conn.execute(
        "SELECT balance, sync_status FROM account_balances WHERE account_id='pluggy:bank'"
    ).fetchone()

    assert bank["pluggy_item_id"] == "item-bank"
    assert bank_balance["balance"] == 58.77
    assert bank_balance["sync_status"] == "UPDATED"
    assert card_balance["credit_limit"] == 4000.0
    assert card_balance["available"] == 3250.5
    assert card_balance["used"] == 749.5
    assert card_balance["brand"] == "MASTERCARD"
    assert card_balance["last4"] == "1234"
    assert card_balance["sync_status"] == "UPDATED"
    assert apply_migrations(db._conn) == 0
    db.close()


def test_add_column_guard_is_safe_when_column_exists(tmp_db):
    _add_column(tmp_db._conn, "transactions", "note", "TEXT")
    _add_column(tmp_db._conn, "transactions", "note", "TEXT")

    assert "note" in _columns(tmp_db._conn, "transactions")


def test_apply_migrations_recovers_when_schema_migrations_was_cleared(tmp_db):
    tmp_db._conn.execute("DELETE FROM schema_migrations")
    tmp_db._conn.commit()

    assert apply_migrations(tmp_db._conn) == 17
    assert apply_migrations(tmp_db._conn) == 0

    ids = [
        row[0]
        for row in tmp_db._conn.execute(
            "SELECT id FROM schema_migrations ORDER BY id"
        ).fetchall()
    ]
    assert ids == list(range(1, 18))
