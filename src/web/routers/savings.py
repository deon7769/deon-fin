from __future__ import annotations

import re
from datetime import date
from typing import Any
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...storage import Database
from ..dependencies import get_db
from ..repositories import budget_repo, savings_repo

router = APIRouter(prefix="/api", tags=["savings"])
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


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


class SavingsGoalTransactionIds(BaseModel):
    transaction_ids: list[str]


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


def _validate_year_month(value: str | None, *, field: str = "month") -> str | None:
    if value is None:
        return None
    if not _YEAR_MONTH_RE.match(value):
        raise HTTPException(status_code=422, detail=f"{field} inválido")
    month = int(value[5:7])
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail=f"{field} inválido")
    return value


def _parse_date(value: str | None, *, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field} inválido") from exc


def _parse_optional_ids(value: str | None, *, field: str) -> list[int | None] | None:
    if value is None or value.strip() == "":
        return None

    parsed: list[int | None] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if token == "none":
            parsed.append(None)
            continue
        try:
            parsed.append(int(token))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{field} inválido") from exc
    return parsed or None


def _repo_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


def _goal_error(exc: ValueError) -> HTTPException:
    if str(exc) == "meta não encontrada":
        return HTTPException(status_code=404, detail=str(exc))
    return _repo_error(exc)


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


@router.get("/savings-goals/{goal_id}/transactions")
def get_savings_goal_transactions(
    goal_id: int,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return savings_repo.goal_transactions(db, goal_id)
    except ValueError as exc:
        raise _goal_error(exc) from exc


@router.get("/savings-goals/{goal_id}/candidates")
def get_savings_goal_candidates(
    goal_id: int,
    month: str | None = Query(default=None),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    q: str | None = None,
    type: Literal["income", "expense"] | None = None,
    account_id: str | None = None,
    bucket_ids: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return savings_repo.goal_candidates(
            db,
            goal_id,
            month=_validate_year_month(month),
            date_from=_parse_date(from_, field="from"),
            date_to=_parse_date(to, field="to"),
            q=q,
            type=type,
            account_id=account_id,
            bucket_ids=_parse_optional_ids(bucket_ids, field="bucket_ids"),
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise _goal_error(exc) from exc


@router.post("/savings-goals/{goal_id}/link")
def link_savings_goal_transactions(
    goal_id: int,
    body: SavingsGoalTransactionIds,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return savings_repo.link_transactions(db, goal_id, body.transaction_ids)
    except ValueError as exc:
        raise _goal_error(exc) from exc


@router.post("/savings-goals/{goal_id}/unlink")
def unlink_savings_goal_transactions(
    goal_id: int,
    body: SavingsGoalTransactionIds,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return savings_repo.unlink_transactions(db, goal_id, body.transaction_ids)
    except ValueError as exc:
        raise _goal_error(exc) from exc


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
