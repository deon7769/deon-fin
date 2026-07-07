from __future__ import annotations

import pytest

from src.auth.family_guard import MultiFamilySQLiteGuardError, enforce_sqlite_single_family_mode


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params or {}))
        return self

    def fetchone(self):
        return self.rows.pop(0)


class FakeConnection:
    def __init__(self, rows):
        self.cursor_obj = FakeCursor(rows)

    def cursor(self):
        return self.cursor_obj


def test_sqlite_single_family_guard_allows_existing_default_family():
    conn = FakeConnection(
        [
            {"active_family_count": 1},
            {"conflicting_family_count": 0},
        ],
    )

    enforce_sqlite_single_family_mode(
        conn,
        financial_database_url="sqlite:///data/financas.db",
        requested_family_slug="familia-principal",
    )

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    assert "count(*) AS active_family_count" in sql
    assert "slug <> %(family_slug)s" in sql


def test_sqlite_single_family_guard_blocks_multiple_active_families():
    conn = FakeConnection([{"active_family_count": 2}])

    with pytest.raises(MultiFamilySQLiteGuardError, match="SQLite"):
        enforce_sqlite_single_family_mode(
            conn,
            financial_database_url="sqlite:///data/financas.db",
        )


def test_sqlite_single_family_guard_blocks_bootstrap_of_second_family_slug():
    conn = FakeConnection(
        [
            {"active_family_count": 1},
            {"conflicting_family_count": 1},
        ],
    )

    with pytest.raises(MultiFamilySQLiteGuardError, match="uma família"):
        enforce_sqlite_single_family_mode(
            conn,
            financial_database_url="sqlite:///data/financas.db",
            requested_family_slug="outra-familia",
        )


def test_sqlite_single_family_guard_noops_when_financial_database_is_postgres():
    conn = FakeConnection([])

    enforce_sqlite_single_family_mode(
        conn,
        financial_database_url="postgresql://deon_fin:secret@postgres/deon_fin",
        requested_family_slug="outra-familia",
    )

    assert conn.cursor_obj.statements == []
