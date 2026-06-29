from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from src.storage import Account, Database, Transaction
from src.storage.migrate_sqlite_to_postgres import (
    LEGACY_TABLES,
    collect_sqlite_migration_report,
)


def test_collect_sqlite_migration_report_counts_legacy_rows(tmp_path):
    db_path = tmp_path / "legacy.db"
    db = Database(db_path)
    db.upsert_account(Account(id="acc-1", source="csv", name="Conta", type="CHECKING"))
    db.insert_transactions(
        [
            Transaction(
                account_id="acc-1",
                posted_at=date(2026, 6, 1),
                amount=Decimal("-10.00"),
                description="Mercado",
                source="csv",
            )
        ]
    )
    db.upsert_pluggy_item("item-1", connector_id=1, connector_name="Banco", status="UPDATED")
    db.close()

    report = collect_sqlite_migration_report(db_path)

    assert report.sqlite_path == db_path
    assert report.default_family_name == "Familia Principal"
    assert report.counts["accounts"] == 1
    assert report.counts["transactions"] == 1
    assert report.counts["pluggy_items"] == 1
    assert report.target_tables["pluggy_items"] == "provider_connections"


def test_collect_sqlite_migration_report_counts_missing_legacy_tables_as_zero(tmp_path):
    db_path = tmp_path / "partial.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO accounts (id) VALUES ('acc-1')")
    conn.commit()
    conn.close()

    report = collect_sqlite_migration_report(db_path)

    assert report.counts["accounts"] == 1
    for table in LEGACY_TABLES:
        if table != "accounts":
            assert report.counts[table] == 0


def test_collect_sqlite_migration_report_missing_file_raises(tmp_path):
    db_path = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError):
        collect_sqlite_migration_report(db_path)

    assert not db_path.exists()


def test_collect_sqlite_migration_report_preserves_custom_family_name(tmp_path):
    db_path = tmp_path / "legacy.db"
    sqlite3.connect(db_path).close()

    report = collect_sqlite_migration_report(db_path, default_family_name="Casa Azul")

    assert report.default_family_name == "Casa Azul"
