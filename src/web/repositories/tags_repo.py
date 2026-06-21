from __future__ import annotations

import re
import sqlite3
from typing import Any

from ...storage import Database

TAG_SEED: list[dict[str, str]] = [
    {"name": "Alimentação", "color": "#F5B301"},
    {"name": "Conforto", "color": "#EF4444"},
    {"name": "Educação", "color": "#38BDF8"},
    {"name": "Lazer", "color": "#9F1239"},
    {"name": "Saúde", "color": "#3B82F6"},
    {"name": "Transporte", "color": "#F97316"},
    {"name": "Vestuário", "color": "#A855F7"},
]

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_UNSET = object()


def normalize_color(color: str | None) -> str | None:
    if color is None:
        return None

    normalized = color.strip()
    if normalized == "":
        return None
    if not _HEX_RE.match(normalized):
        raise ValueError("cor inválida")
    return normalized.lower()


def normalize_name(name: str) -> str:
    normalized = " ".join((name or "").split())
    if not normalized:
        raise ValueError("nome obrigatório")
    if len(normalized) > 40:
        raise ValueError("nome muito longo")
    return normalized


def seed_tags(db: Database) -> int:
    inserted = 0
    with db._cursor() as cur:  # type: ignore[attr-defined]
        for tag in TAG_SEED:
            cur.execute(
                """
                INSERT INTO tags (name, color)
                VALUES (:name, :color)
                ON CONFLICT(name) DO NOTHING
                """,
                tag,
            )
            inserted += max(cur.rowcount, 0)
    return inserted


def seed_tags_if_empty(db: Database) -> int:
    count = db._conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    if count:
        return 0
    return seed_tags(db)


def list_tags(db: Database) -> list[dict[str, Any]]:
    rows = db._conn.execute(
        """
        SELECT t.id, t.name, t.color, COUNT(tx.id) AS tx_count
          FROM tags t
          LEFT JOIN transactions tx ON tx.tag_id = t.id
         GROUP BY t.id, t.name, t.color
         ORDER BY LOWER(t.name), t.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_tag(db: Database, tag_id: int) -> dict[str, Any] | None:
    row = db._conn.execute(
        """
        SELECT t.id, t.name, t.color, COUNT(tx.id) AS tx_count
          FROM tags t
          LEFT JOIN transactions tx ON tx.tag_id = t.id
         WHERE t.id=?
         GROUP BY t.id, t.name, t.color
        """,
        (tag_id,),
    ).fetchone()
    return dict(row) if row else None


def tag_exists(db: Database, tag_id: int) -> bool:
    row = db._conn.execute(
        "SELECT 1 FROM tags WHERE id=? LIMIT 1",
        (tag_id,),
    ).fetchone()
    return row is not None


def name_taken(db: Database, name: str, *, exclude_id: int | None = None) -> bool:
    normalized = normalize_name(name)
    rows = db._conn.execute("SELECT id, name FROM tags").fetchall()
    return any(
        row["name"].casefold() == normalized.casefold()
        and (exclude_id is None or row["id"] != exclude_id)
        for row in rows
    )


def create_tag(db: Database, *, name: str, color: str | None = None) -> dict[str, Any]:
    normalized_name = normalize_name(name)
    normalized_color = normalize_color(color)
    if name_taken(db, normalized_name):
        raise ValueError("duplicate")

    try:
        with db._cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                "INSERT INTO tags (name, color) VALUES (?, ?)",
                (normalized_name, normalized_color),
            )
            new_id = int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("duplicate") from exc

    tag = get_tag(db, new_id)
    if tag is None:
        raise RuntimeError("tag created but not found")
    return tag


def update_tag(
    db: Database,
    tag_id: int,
    *,
    name: str | None = None,
    color: str | None | object = _UNSET,
) -> dict[str, Any] | None:
    if get_tag(db, tag_id) is None:
        return None

    assignments: list[str] = []
    params: list[Any] = []

    if name is not None:
        normalized_name = normalize_name(name)
        if name_taken(db, normalized_name, exclude_id=tag_id):
            raise ValueError("duplicate")
        assignments.append("name=?")
        params.append(normalized_name)

    if color is not _UNSET:
        assignments.append("color=?")
        params.append(normalize_color(color if isinstance(color, str) else None))

    if assignments:
        try:
            with db._cursor() as cur:  # type: ignore[attr-defined]
                cur.execute(
                    f"UPDATE tags SET {', '.join(assignments)} WHERE id=?",
                    (*params, tag_id),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("duplicate") from exc

    return get_tag(db, tag_id)


def delete_tag(db: Database, tag_id: int) -> dict[str, int] | None:
    if get_tag(db, tag_id) is None:
        return None

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("UPDATE transactions SET tag_id=NULL WHERE tag_id=?", (tag_id,))
        untagged = max(cur.rowcount, 0)
        cur.execute("DELETE FROM tags WHERE id=?", (tag_id,))

    return {"deleted_id": tag_id, "untagged": untagged}
