from __future__ import annotations

from typing import Any

from ...agent import maintenance as mnt
from ...agent.budget import summarize_wishlist
from ...storage import Database
from . import budget_repo


def _money(value: Any) -> float:
    return round(float(value or 0.0), 2)


def _normalize_name(value: str | None) -> str:
    name = " ".join((value or "").split())
    if not name:
        raise ValueError("name obrigatório")
    return name


def _positive_amount(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("target_amount inválido") from exc
    if parsed <= 0:
        raise ValueError("target_amount inválido")
    return _money(parsed)


def _non_negative_amount(value: Any) -> float:
    try:
        parsed = float(value or 0.0)
    except (TypeError, ValueError) as exc:
        raise ValueError("saved_amount inválido") from exc
    if parsed < 0:
        raise ValueError("saved_amount inválido")
    return _money(parsed)


def _term_months(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("term_months inválido") from exc
    if parsed < 1:
        raise ValueError("term_months inválido")
    return parsed


def _priority(value: Any) -> int:
    try:
        parsed = int(value if value is not None else 99)
    except (TypeError, ValueError) as exc:
        raise ValueError("priority inválida") from exc
    if parsed < 1:
        raise ValueError("priority inválida")
    return parsed


def _row_to_public(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "target_amount": _money(row["target_amount"]),
        "term_months": int(row["term_months"]),
        "saved_amount": _money(row["saved_amount"]),
        "priority": int(row["priority"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_wishlist(row: Any) -> dict[str, Any]:
    return {
        "nome": row["name"],
        "valor_alvo": row["target_amount"],
        "prazo_meses": row["term_months"],
        "guardado": row["saved_amount"],
        "prioridade": row["priority"],
    }


def _ordered_rows(db: Database) -> list[Any]:
    return db._conn.execute(
        """
        SELECT id, name, target_amount, term_months, saved_amount, priority,
               created_at, updated_at
          FROM savings_goals
         ORDER BY priority ASC, target_amount DESC, id ASC
        """
    ).fetchall()


def _goals_count(db: Database) -> int:
    return int(db._conn.execute("SELECT COUNT(*) FROM savings_goals").fetchone()[0])


def _import_was_checked(db: Database) -> bool:
    row = db._conn.execute(
        "SELECT 1 FROM savings_goals_import_state WHERE id=1",
    ).fetchone()
    return row is not None


def _mark_import_checked(db: Database) -> None:
    db._conn.execute(
        """
        INSERT INTO savings_goals_import_state (id)
        VALUES (1)
        ON CONFLICT(id) DO NOTHING
        """
    )


def _family_items() -> list[dict[str, Any]]:
    profile = mnt.load_family_profile() or {}
    items: list[dict[str, Any]] = []
    for key in ("metas", "wishlist"):
        raw = profile.get(key) or []
        if isinstance(raw, list):
            items.extend(item for item in raw if isinstance(item, dict))
    return items


def _seed_from_family_profile(db: Database) -> None:
    if _import_was_checked(db):
        return
    if _goals_count(db) > 0:
        with db._cursor() as cur:  # type: ignore[attr-defined]
            _mark_import_checked(db)
        return

    with db._cursor() as cur:  # type: ignore[attr-defined]
        for item in _family_items():
            try:
                name = _normalize_name(item.get("nome") or item.get("name"))
                target = _positive_amount(item.get("valor_alvo") or item.get("target_amount"))
                term = _term_months(item.get("prazo_meses") or item.get("term_months") or 12)
                saved = _non_negative_amount(item.get("guardado") or item.get("saved_amount") or 0)
                priority = _priority(item.get("prioridade") or item.get("priority") or 99)
            except (TypeError, ValueError):
                continue
            cur.execute(
                """
                INSERT INTO savings_goals
                  (name, target_amount, term_months, saved_amount, priority)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, target, term, saved, priority),
            )
        _mark_import_checked(db)


def list_with_summary(db: Database, month: str) -> dict[str, Any]:
    _seed_from_family_profile(db)
    rows = _ordered_rows(db)
    budget = budget_repo.budget_for_month(db, month)
    summary = summarize_wishlist([_row_to_wishlist(row) for row in rows], budget["remaining"])
    items = summary["itens"]
    goals = []
    for row, item in zip(rows, items):
        goals.append(
            {
                **_row_to_public(row),
                "monthly_required": item["guardar_mes"],
                "progress_pct": item["progresso_pct"],
                "fits_surplus": item["cabe_na_sobra"],
            }
        )

    return {
        "month": month,
        "goals": goals,
        "total_monthly_required": summary["total_guardar_mes"],
        "monthly_surplus": summary["sobra_mensal"],
        "surplus_after_goals": summary["folga"],
    }


def create_goal(
    db: Database,
    *,
    name: str,
    target_amount: float,
    term_months: int = 12,
    saved_amount: float = 0.0,
    priority: int = 99,
) -> dict[str, Any]:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        _mark_import_checked(db)
        cur.execute(
            """
            INSERT INTO savings_goals
              (name, target_amount, term_months, saved_amount, priority)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                _normalize_name(name),
                _positive_amount(target_amount),
                _term_months(term_months),
                _non_negative_amount(saved_amount),
                _priority(priority),
            ),
        )
        goal_id = int(cur.lastrowid)
    goal = get_goal(db, goal_id)
    if goal is None:
        raise RuntimeError("savings goal was not created")
    return goal


def get_goal(db: Database, goal_id: int) -> dict[str, Any] | None:
    row = db._conn.execute(
        """
        SELECT id, name, target_amount, term_months, saved_amount, priority,
               created_at, updated_at
          FROM savings_goals
         WHERE id=?
        """,
        (goal_id,),
    ).fetchone()
    return _row_to_public(row) if row else None


def update_goal(db: Database, goal_id: int, **updates: Any) -> dict[str, Any] | None:
    current = get_goal(db, goal_id)
    if current is None:
        return None

    values: dict[str, Any] = {}
    if "name" in updates:
        values["name"] = _normalize_name(updates["name"])
    if "target_amount" in updates:
        values["target_amount"] = _positive_amount(updates["target_amount"])
    if "term_months" in updates:
        values["term_months"] = _term_months(updates["term_months"])
    if "saved_amount" in updates:
        values["saved_amount"] = _non_negative_amount(updates["saved_amount"])
    if "priority" in updates:
        values["priority"] = _priority(updates["priority"])

    if values:
        assignments = ", ".join(f"{field}=?" for field in values)
        params = list(values.values()) + [goal_id]
        with db._cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                f"""
                UPDATE savings_goals
                   SET {assignments},
                       updated_at=datetime('now')
                 WHERE id=?
                """,
                params,
            )
    return get_goal(db, goal_id)


def delete_goal(db: Database, goal_id: int) -> dict[str, int] | None:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        _mark_import_checked(db)
        cur.execute("DELETE FROM savings_goals WHERE id=?", (goal_id,))
        if cur.rowcount <= 0:
            return None
    return {"deleted_id": goal_id}
