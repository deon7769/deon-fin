from __future__ import annotations

from typing import Any

from ...storage import Database

BUCKET_SEED: list[dict[str, Any]] = [
    {
        "key": "liberdade_financeira",
        "name": "Liberdade Financeira",
        "color": "#22C55E",
        "planned_kind": "percent",
        "planned_value": 10.0,
        "sort_order": 1,
    },
    {
        "key": "custos_fixos",
        "name": "Custos Fixos",
        "color": "#3B82F6",
        "planned_kind": "percent",
        "planned_value": 55.0,
        "sort_order": 2,
    },
    {
        "key": "conforto",
        "name": "Conforto",
        "color": "#06B6D4",
        "planned_kind": "percent",
        "planned_value": 10.0,
        "sort_order": 3,
    },
    {
        "key": "metas",
        "name": "Metas",
        "color": "#A855F7",
        "planned_kind": "percent",
        "planned_value": 10.0,
        "sort_order": 4,
    },
    {
        "key": "prazeres",
        "name": "Prazeres",
        "color": "#F97316",
        "planned_kind": "percent",
        "planned_value": 10.0,
        "sort_order": 5,
    },
    {
        "key": "conhecimento",
        "name": "Conhecimento",
        "color": "#9F1239",
        "planned_kind": "percent",
        "planned_value": 5.0,
        "sort_order": 6,
    },
]


def seed_buckets(db: Database) -> int:
    inserted = 0
    with db._cursor() as cur:  # type: ignore[attr-defined]
        for bucket in BUCKET_SEED:
            cur.execute(
                """
                INSERT INTO budget_buckets
                  (key, name, color, planned_kind, planned_value, sort_order, is_system)
                VALUES
                  (:key, :name, :color, :planned_kind, :planned_value, :sort_order, 1)
                ON CONFLICT(key) DO NOTHING
                """,
                bucket,
            )
            inserted += max(cur.rowcount, 0)
    return inserted


def list_buckets(db: Database) -> list[dict[str, Any]]:
    rows = db._conn.execute(
        """
        SELECT id, key, name, color, planned_kind, planned_value, sort_order, is_system
          FROM budget_buckets
         ORDER BY sort_order, id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_bucket(db: Database, bucket_id: int) -> dict[str, Any] | None:
    row = db._conn.execute(
        """
        SELECT id, key, name, color, planned_kind, planned_value, sort_order, is_system
          FROM budget_buckets
         WHERE id=?
        """,
        (bucket_id,),
    ).fetchone()
    return dict(row) if row else None


def bucket_exists(db: Database, bucket_id: int) -> bool:
    return get_bucket(db, bucket_id) is not None


def list_rules(db: Database) -> list[dict[str, Any]]:
    rows = db._conn.execute(
        """
        SELECT id, match_key, bucket_id, created_at
          FROM bucket_rules
         ORDER BY match_key
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_rule(db: Database, match_key: str) -> dict[str, Any] | None:
    row = db._conn.execute(
        """
        SELECT id, match_key, bucket_id, created_at
          FROM bucket_rules
         WHERE match_key=?
        """,
        (match_key,),
    ).fetchone()
    return dict(row) if row else None


def upsert_rule(db: Database, match_key: str, bucket_id: int) -> None:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO bucket_rules (match_key, bucket_id)
            VALUES (?, ?)
            ON CONFLICT(match_key) DO UPDATE SET bucket_id=excluded.bucket_id
            """,
            (match_key, bucket_id),
        )


def delete_rule(db: Database, match_key: str) -> bool:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("DELETE FROM bucket_rules WHERE match_key=?", (match_key,))
        return cur.rowcount > 0
