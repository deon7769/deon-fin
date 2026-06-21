from __future__ import annotations

from typing import Any

from ...storage import Database


def list_tags(db: Database) -> list[dict[str, Any]]:
    rows = db._conn.execute(
        """
        SELECT id, name, color, created_at
          FROM tags
         ORDER BY name COLLATE NOCASE, id
        """
    ).fetchall()
    return [dict(row) for row in rows]
