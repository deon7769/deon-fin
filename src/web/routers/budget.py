from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...storage import Database
from ..dependencies import get_db
from ..repositories import budget_repo

router = APIRouter(prefix="/api", tags=["budget"])


def _resolve_month_or_422(db: Database, month: str | None) -> str:
    resolved = budget_repo.resolve_month(db, month)
    if resolved is None:
        raise HTTPException(status_code=422, detail="month deve ser YYYY-MM")
    return resolved


@router.get("/budget")
def budget(
    month: str | None = Query(default=None),
    db: Database = Depends(get_db),
) -> dict:
    return budget_repo.budget_for_month(db, _resolve_month_or_422(db, month))
