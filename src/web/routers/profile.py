from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from ...storage import Database
from ..dependencies import get_db
from ..repositories import profile_repo, transactions_repo

router = APIRouter(prefix="/api", tags=["profile"])
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ProfileInput(BaseModel):
    name: str | None = ""
    email: str | None = ""
    monthly_income: float = 0.0
    financial_month_start_day: int = 1
    goals_text: str | None = ""


def _normalize_profile_input(body: ProfileInput) -> dict[str, Any]:
    name = " ".join((body.name or "").split())
    email = (body.email or "").strip()
    goals_text = (body.goals_text or "").strip()

    if email and not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="e-mail inválido")
    if body.monthly_income < 0:
        raise HTTPException(status_code=422, detail="renda mensal inválida")
    if body.financial_month_start_day < 1 or body.financial_month_start_day > 28:
        raise HTTPException(status_code=422, detail="início do mês financeiro inválido")

    return {
        "name": name,
        "email": email,
        "monthly_income": float(body.monthly_income),
        "financial_month_start_day": int(body.financial_month_start_day),
        "goals_text": goals_text,
    }


def recompute_reference_month_all(database_path: str | Path, start_day: int) -> int:
    db = Database(database_path)
    try:
        return transactions_repo.recompute_reference_months(db, start_day)
    finally:
        db.close()


@router.get("/profile")
def get_profile(db: Database = Depends(get_db)) -> dict[str, Any]:
    return profile_repo.get_profile(db)


@router.put("/profile")
def update_profile(
    body: ProfileInput,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    current = profile_repo.get_or_create_profile(db)
    values = _normalize_profile_input(body)
    day_changed = (
        values["financial_month_start_day"] != current["financial_month_start_day"]
    )
    profile = profile_repo.update_profile(db, **values)

    if day_changed:
        background_tasks.add_task(
            recompute_reference_month_all,
            db.path,
            values["financial_month_start_day"],
        )

    return {
        "saved": True,
        "reference_month_recompute": "scheduled" if day_changed else "not_needed",
        "profile": profile,
    }
