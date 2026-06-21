from __future__ import annotations

import re
from typing import Any

from ...storage import Database

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

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


def _money(value: Any) -> float:
    return round(float(value or 0.0), 2)


def _validate_color(value: str | None) -> str | None:
    if value is None:
        return None
    color = value.strip()
    if not _HEX_COLOR_RE.match(color):
        raise ValueError("color inválida")
    return color


def _validate_name(value: str | None) -> str:
    name = " ".join((value or "").split())
    if not name:
        raise ValueError("name obrigatório")
    return name


def _validate_plan(kind: str | None, value: float | None) -> tuple[str | None, float | None]:
    if kind is not None and kind not in {"percent", "amount"}:
        raise ValueError("planned_kind inválido")
    if value is None:
        return kind, None
    parsed = float(value)
    if parsed < 0:
        raise ValueError("planned_value inválido")
    if kind == "percent" and parsed > 100:
        raise ValueError("planned_value inválido")
    return kind, _money(parsed)


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


def set_planned(
    db: Database,
    bucket_id: int,
    *,
    name: str | None = None,
    color: str | None = None,
    planned_kind: str | None = None,
    planned_value: float | None = None,
) -> dict[str, Any] | None:
    current = get_bucket(db, bucket_id)
    if current is None:
        return None

    next_kind = planned_kind if planned_kind is not None else current["planned_kind"]
    next_value = (
        float(planned_value)
        if planned_value is not None
        else float(current["planned_value"] or 0.0)
    )
    _validate_plan(next_kind, next_value)

    updates: dict[str, Any] = {}
    if name is not None:
        updates["name"] = _validate_name(name)
    if color is not None:
        updates["color"] = _validate_color(color)
    if planned_kind is not None:
        updates["planned_kind"] = next_kind
    if planned_value is not None:
        updates["planned_value"] = _money(next_value)

    if updates:
        assignments = ", ".join(f"{field}=?" for field in updates)
        params = list(updates.values()) + [bucket_id]
        with db._cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                f"UPDATE budget_buckets SET {assignments} WHERE id=?",
                params,
            )
    return get_bucket(db, bucket_id)


def set_sort(db: Database, order: list[int]) -> int:
    if not order:
        raise ValueError("order obrigatório")
    normalized = [int(bucket_id) for bucket_id in order]
    if len(set(normalized)) != len(normalized):
        raise ValueError("order duplicado")

    existing = {
        int(row["id"])
        for row in db._conn.execute("SELECT id FROM budget_buckets").fetchall()
    }
    if any(bucket_id not in existing for bucket_id in normalized):
        raise ValueError("bucket inválido")

    with db._cursor() as cur:  # type: ignore[attr-defined]
        for index, bucket_id in enumerate(normalized, start=1):
            cur.execute(
                "UPDATE budget_buckets SET sort_order=? WHERE id=?",
                (index, bucket_id),
            )
    return len(normalized)


def bucket_plan(db: Database, month: str) -> dict[str, Any]:
    from . import budget_repo

    budget = budget_repo.budget_for_month(db, month)
    buckets = [
        {
            "id": category["id"],
            "key": category["key"],
            "name": category["name"],
            "color": category["color"],
            "planned_kind": category["planned_kind"],
            "planned_value": category["planned_value"],
            "planned_amount": category["planned"],
            "spent_month": category["spent"],
        }
        for category in budget["categories"]
    ]
    sum_percent = _money(
        sum(
            float(bucket["planned_value"] or 0.0)
            for bucket in buckets
            if bucket["planned_kind"] == "percent"
        )
    )
    sum_amount = _money(sum(float(bucket["planned_amount"] or 0.0) for bucket in buckets))
    warning = None
    if abs(sum_percent - 100.0) > 0.01:
        warning = {
            "code": "percent_total_mismatch",
            "message": "A soma dos percentuais planejados deve fechar em 100%.",
        }

    return {
        "month": budget["month"],
        "income": budget["income"],
        "income_source": budget["income_source"],
        "buckets": buckets,
        "sum_percent": sum_percent,
        "sum_amount": sum_amount,
        "warning": warning,
    }


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
