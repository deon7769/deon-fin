from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

LEGACY_TABLES = (
    "pluggy_items",
    "accounts",
    "account_balances",
    "transactions",
    "tags",
    "budget_buckets",
    "bucket_rules",
    "tag_rules",
    "profile",
    "savings_goals",
    "portfolio_assets",
    "portfolio_transactions",
    "allocation_targets",
    "investment_profile",
    "asset_questions",
    "asset_answers",
    "classification_audit_log",
    "account_total_settings",
    "movement_total_settings",
)

TARGET_TABLES = {
    "pluggy_items": "provider_connections",
    "profile": "family_profiles",
}


@dataclass(frozen=True)
class SQLiteMigrationReport:
    sqlite_path: Path
    default_family_name: str
    counts: dict[str, int]
    target_tables: dict[str, str]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def collect_sqlite_migration_report(
    sqlite_path: Path,
    *,
    default_family_name: str = "Familia Principal",
) -> SQLiteMigrationReport:
    path = Path(sqlite_path)
    if not path.exists():
        raise FileNotFoundError(path)

    counts: dict[str, int] = {}
    sqlite_uri = f"{path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(sqlite_uri, uri=True) as conn:
        for table in LEGACY_TABLES:
            if _table_exists(conn, table):
                counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            else:
                counts[table] = 0

    return SQLiteMigrationReport(
        sqlite_path=path,
        default_family_name=default_family_name,
        counts=counts,
        target_tables={table: TARGET_TABLES.get(table, table) for table in LEGACY_TABLES},
    )
