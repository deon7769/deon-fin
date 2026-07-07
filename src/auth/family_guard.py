from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class CursorLike(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> Any: ...
    def fetchone(self) -> Mapping[str, Any] | tuple[Any, ...] | None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...


class MultiFamilySQLiteGuardError(Exception):
    """Raised when multi-family auth would expose global SQLite financial data."""


def enforce_sqlite_single_family_mode(
    conn: ConnectionLike,
    *,
    financial_database_url: str,
    requested_family_slug: str | None = None,
) -> None:
    if not financial_database_url.startswith("sqlite:///"):
        return

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT count(*) AS active_family_count
        FROM families
        WHERE status = 'active'
        """
    )
    active_count = _int_value(cursor.fetchone(), "active_family_count")
    if active_count > 1:
        raise MultiFamilySQLiteGuardError(
            "Modo multi-familia bloqueado enquanto os dados financeiros usam SQLite."
        )

    if requested_family_slug and active_count:
        cursor.execute(
            """
            SELECT count(*) AS conflicting_family_count
            FROM families
            WHERE status = 'active'
              AND slug <> %(family_slug)s
            """,
            {"family_slug": requested_family_slug},
        )
        conflict_count = _int_value(cursor.fetchone(), "conflicting_family_count")
        if conflict_count:
            raise MultiFamilySQLiteGuardError(
                "Bootstrap bloqueado: mantenha uma família ativa enquanto os dados financeiros usam SQLite."
            )


def _int_value(row: Mapping[str, Any] | tuple[Any, ...] | None, key: str) -> int:
    if row is None:
        return 0
    if isinstance(row, Mapping):
        return int(row.get(key) or 0)
    return int(row[0] or 0)
