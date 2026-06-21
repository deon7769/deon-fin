from __future__ import annotations

from typing import Any

from ...storage import Database


def list_buckets(db: Database) -> list[dict[str, Any]]:
    rows = db._conn.execute(
        """
        SELECT id, key, name, color, planned_kind, planned_value, sort_order, is_system
          FROM budget_buckets
         ORDER BY sort_order, id
        """
    ).fetchall()
    return [dict(row) for row in rows]
