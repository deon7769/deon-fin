from __future__ import annotations

import hashlib
import re
import sqlite3
from typing import Any

from ...storage import Database

TAG_SEED: list[dict[str, str]] = [
    {"name": "Alimentação", "color": "#F5B301", "bucket_key": "conforto"},
    {"name": "Conforto", "color": "#EF4444", "bucket_key": "conforto"},
    {"name": "Educação", "color": "#38BDF8", "bucket_key": "conhecimento"},
    {"name": "Lazer", "color": "#9F1239", "bucket_key": "prazeres"},
    {"name": "Saúde", "color": "#3B82F6", "bucket_key": "custos_fixos"},
    {"name": "Transporte", "color": "#F97316", "bucket_key": "custos_fixos"},
    {"name": "Vestuário", "color": "#A855F7", "bucket_key": "conforto"},
]

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_UNSET = object()
_AUTO_COLOR_PALETTE = [
    "#0ea5e9",
    "#14b8a6",
    "#84cc16",
    "#f59e0b",
    "#ef4444",
    "#ec4899",
    "#8b5cf6",
    "#6366f1",
    "#64748b",
    "#22c55e",
    "#f97316",
    "#06b6d4",
]


def normalize_color(color: str | None) -> str | None:
    if color is None:
        return None

    normalized = color.strip()
    if normalized == "":
        return None
    if not _HEX_RE.match(normalized):
        raise ValueError("cor invalida")
    return normalized.lower()


def normalize_name(name: str) -> str:
    normalized = " ".join((name or "").split())
    if not normalized:
        raise ValueError("nome obrigatorio")
    if len(normalized) > 40:
        raise ValueError("nome muito longo")
    return normalized


def default_tag_color(name: str) -> str:
    normalized = normalize_name(name).casefold()
    digest = hashlib.sha1(normalized.encode("utf-8")).digest()
    return _AUTO_COLOR_PALETTE[digest[0] % len(_AUTO_COLOR_PALETTE)]


def _bucket_id_by_key(db: Database) -> dict[str, int]:
    from . import buckets_repo

    buckets_repo.seed_buckets(db)
    return {bucket["key"]: int(bucket["id"]) for bucket in buckets_repo.list_buckets(db)}


def _validate_bucket_id(db: Database, bucket_id: int | None) -> int | None:
    if bucket_id is None:
        return None
    from . import buckets_repo

    parsed = int(bucket_id)
    if not buckets_repo.bucket_exists(db, parsed):
        raise ValueError(f"bucket_id invalido: {bucket_id}")
    return parsed


def backfill_missing_tag_colors(db: Database) -> int:
    rows = db._conn.execute(
        """
        SELECT id, name
          FROM tags
         WHERE color IS NULL OR TRIM(COALESCE(color, '')) = ''
         ORDER BY id
        """
    ).fetchall()
    if not rows:
        return 0

    with db._cursor() as cur:  # type: ignore[attr-defined]
        for row in rows:
            cur.execute(
                "UPDATE tags SET color=? WHERE id=?",
                (default_tag_color(str(row["name"])), row["id"]),
            )
    return len(rows)


def seed_tags(db: Database) -> int:
    inserted = 0
    bucket_ids = _bucket_id_by_key(db)
    with db._cursor() as cur:  # type: ignore[attr-defined]
        for tag in TAG_SEED:
            cur.execute(
                """
                INSERT INTO tags (name, color, bucket_id)
                VALUES (:name, :color, :bucket_id)
                ON CONFLICT(name) DO NOTHING
                """,
                {
                    "name": tag["name"],
                    "color": tag["color"],
                    "bucket_id": bucket_ids.get(tag["bucket_key"]),
                },
            )
            inserted += max(cur.rowcount, 0)
    backfill_missing_tag_colors(db)
    return inserted


def seed_tags_if_empty(db: Database) -> int:
    count = db._conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    if count:
        backfill_missing_tag_colors(db)
        return 0
    return seed_tags(db)


def list_tags(db: Database) -> list[dict[str, Any]]:
    rows = db._conn.execute(
        """
        SELECT t.id, t.name, t.color, t.bucket_id,
               b.key AS bucket_key, b.name AS bucket_name, b.color AS bucket_color,
               COUNT(tx.id) AS tx_count
          FROM tags t
          LEFT JOIN transactions tx ON tx.tag_id = t.id
          LEFT JOIN budget_buckets b ON b.id = t.bucket_id
         GROUP BY t.id, t.name, t.color, t.bucket_id, b.key, b.name, b.color
         ORDER BY LOWER(t.name), t.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_tag(db: Database, tag_id: int) -> dict[str, Any] | None:
    row = db._conn.execute(
        """
        SELECT t.id, t.name, t.color, t.bucket_id,
               b.key AS bucket_key, b.name AS bucket_name, b.color AS bucket_color,
               COUNT(tx.id) AS tx_count
          FROM tags t
          LEFT JOIN transactions tx ON tx.tag_id = t.id
          LEFT JOIN budget_buckets b ON b.id = t.bucket_id
         WHERE t.id=?
         GROUP BY t.id, t.name, t.color, t.bucket_id, b.key, b.name, b.color
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


def find_tag_by_name(db: Database, name: str) -> dict[str, Any] | None:
    normalized = normalize_name(name)
    rows = db._conn.execute("SELECT id, name FROM tags").fetchall()
    for row in rows:
        if row["name"].casefold() == normalized.casefold():
            return get_tag(db, int(row["id"]))
    return None


def create_tag(
    db: Database,
    *,
    name: str,
    color: str | None = None,
    bucket_id: int | None = None,
) -> dict[str, Any]:
    normalized_name = normalize_name(name)
    normalized_color = normalize_color(color)
    normalized_bucket_id = _validate_bucket_id(db, bucket_id)
    if name_taken(db, normalized_name):
        raise ValueError("duplicate")

    try:
        with db._cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                "INSERT INTO tags (name, color, bucket_id) VALUES (?, ?, ?)",
                (normalized_name, normalized_color, normalized_bucket_id),
            )
            new_id = int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("duplicate") from exc

    tag = get_tag(db, new_id)
    if tag is None:
        raise RuntimeError("tag created but not found")
    return tag


def get_or_create_tag(
    db: Database,
    *,
    name: str,
    color: str | None = None,
    bucket_id: int | None = None,
) -> tuple[dict[str, Any], bool]:
    existing = find_tag_by_name(db, name)
    if existing is not None:
        return existing, False
    return create_tag(db, name=name, color=color, bucket_id=bucket_id), True


def update_tag(
    db: Database,
    tag_id: int,
    *,
    name: str | None = None,
    color: str | None | object = _UNSET,
    bucket_id: int | None | object = _UNSET,
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

    if bucket_id is not _UNSET:
        assignments.append("bucket_id=?")
        params.append(
            _validate_bucket_id(db, int(bucket_id) if bucket_id is not None else None)
        )

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
        cur.execute("UPDATE transactions SET tag_id=NULL, tag_source=NULL WHERE tag_id=?", (tag_id,))
        untagged = max(cur.rowcount, 0)
        cur.execute("DELETE FROM tags WHERE id=?", (tag_id,))

    return {"deleted_id": tag_id, "untagged": untagged}


def list_rules_with_targets(db: Database) -> list[dict[str, Any]]:
    rows = db._conn.execute(
        """
        SELECT r.match_key,
               r.tag_id AS target_id,
               t.name AS target_name,
               t.color AS target_color
          FROM tag_rules r
          LEFT JOIN tags t ON t.id = r.tag_id
         ORDER BY r.match_key
        """
    ).fetchall()
    return [dict(row) for row in rows]


def upsert_rule(db: Database, match_key: str, tag_id: int) -> None:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO tag_rules (match_key, tag_id)
            VALUES (?, ?)
            ON CONFLICT(match_key) DO UPDATE SET
                tag_id=excluded.tag_id,
                updated_at=datetime('now')
            """,
            (match_key, tag_id),
        )


def delete_rule(db: Database, match_key: str) -> bool:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("DELETE FROM tag_rules WHERE match_key=?", (match_key,))
        return cur.rowcount > 0
