from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...storage import Database
from ..dependencies import get_db
from ..repositories import budget_repo, savings_repo

router = APIRouter(prefix="/api", tags=["savings"])


class SavingsGoalCreate(BaseModel):
    name: str
    target_amount: float
    term_months: int = 12
    saved_amount: float = 0.0
    priority: int = 99


class SavingsGoalPatch(BaseModel):
    name: str | None = None
    target_amount: float | None = None
    term_months: int | None = None
    saved_amount: float | None = None
    priority: int | None = None


def _fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is None:
        fields = getattr(model, "__fields_set__", set())
    return set(fields)


def _resolve_month_or_422(db: Database, month: str | None) -> str:
    resolved = budget_repo.resolve_month(db, month)
    if resolved is None:
        raise HTTPException(status_code=422, detail="month deve ser YYYY-MM")
    return resolved


def _repo_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/savings-goals")
def list_savings_goals(
    month: str | None = Query(default=None),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    return savings_repo.list_with_summary(db, _resolve_month_or_422(db, month))


@router.post("/savings-goals", status_code=201)
def create_savings_goal(
    body: SavingsGoalCreate,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return savings_repo.create_goal(
            db,
            name=body.name,
            target_amount=body.target_amount,
            term_months=body.term_months,
            saved_amount=body.saved_amount,
            priority=body.priority,
        )
    except ValueError as exc:
        raise _repo_error(exc) from exc


@router.patch("/savings-goals/{goal_id}")
def update_savings_goal(
    goal_id: int,
    body: SavingsGoalPatch,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    fields = _fields_set(body)
    if not fields:
        raise HTTPException(status_code=422, detail="corpo vazio")
    updates = {field: getattr(body, field) for field in fields}
    try:
        goal = savings_repo.update_goal(db, goal_id, **updates)
    except ValueError as exc:
        raise _repo_error(exc) from exc
    if goal is None:
        raise HTTPException(status_code=404, detail="meta não encontrada")
    return goal


@router.delete("/savings-goals/{goal_id}")
def delete_savings_goal(goal_id: int, db: Database = Depends(get_db)) -> dict[str, int]:
    result = savings_repo.delete_goal(db, goal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="meta não encontrada")
    return result
