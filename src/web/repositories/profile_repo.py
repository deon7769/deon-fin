from __future__ import annotations

from typing import Any

from ...agent import maintenance as mnt
from ...config import settings
from ...storage import Database


DEFAULT_PROFILE = {
    "name": "",
    "email": "",
    "monthly_income": 0.0,
    "financial_month_start_day": 1,
    "goals_text": "",
}


def initials_for(name: str | None) -> str:
    words = [word for word in (name or "").strip().split() if word]
    if not words:
        return "?"
    return "".join(word[0].upper() for word in words[:2])


def _with_derived_fields(profile: dict[str, Any]) -> dict[str, Any]:
    return {**profile, "initials": initials_for(profile.get("name"))}


def _select_profile(db: Database) -> dict[str, Any] | None:
    row = db._conn.execute(
        """
        SELECT id, name, email, monthly_income, financial_month_start_day,
               goals_text, updated_at
          FROM profile
         WHERE id = 1
        """
    ).fetchone()
    return dict(row) if row else None


def _legacy_seed() -> dict[str, Any]:
    family_profile = mnt.load_family_profile()
    income = settings.monthly_income or mnt.income_from_profile(family_profile) or 0.0
    goals = ", ".join(settings.financial_goals or [])
    return {
        **DEFAULT_PROFILE,
        "monthly_income": float(income),
        "goals_text": goals,
    }


def get_or_create_profile(db: Database) -> dict[str, Any]:
    current = _select_profile(db)
    if current:
        return _with_derived_fields(current)

    seed = _legacy_seed()
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO profile
              (id, name, email, monthly_income, financial_month_start_day, goals_text)
            VALUES
              (1, :name, :email, :monthly_income, :financial_month_start_day, :goals_text)
            """,
            seed,
        )

    created = _select_profile(db)
    if created is None:
        raise RuntimeError("profile row was not created")
    return _with_derived_fields(created)


def get_profile(db: Database) -> dict[str, Any]:
    return get_or_create_profile(db)


def update_profile(db: Database, **fields: Any) -> dict[str, Any]:
    values = {
        **DEFAULT_PROFILE,
        **fields,
    }
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO profile
              (id, name, email, monthly_income, financial_month_start_day, goals_text, updated_at)
            VALUES
              (1, :name, :email, :monthly_income, :financial_month_start_day, :goals_text,
               datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              email=excluded.email,
              monthly_income=excluded.monthly_income,
              financial_month_start_day=excluded.financial_month_start_day,
              goals_text=excluded.goals_text,
              updated_at=datetime('now')
            """,
            values,
        )

    updated = _select_profile(db)
    if updated is None:
        raise RuntimeError("profile row was not updated")
    return _with_derived_fields(updated)
