from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...storage import Database
from ..dependencies import get_db
from ..repositories import painel_repo

router = APIRouter(prefix="/api", tags=["painel"])


def _resolve_month_or_422(db: Database, month: str | None) -> str:
    resolved = painel_repo.resolve_month(db, month)
    if resolved is None:
        raise HTTPException(status_code=422, detail="month deve ser YYYY-MM")
    return resolved


@router.get("/painel/summary")
def painel_summary(
    month: str | None = Query(default=None),
    db: Database = Depends(get_db),
) -> dict:
    return painel_repo.month_summary(db, _resolve_month_or_422(db, month))


@router.get("/painel/history")
def painel_history(
    window: str = Query(default="6m"),
    db: Database = Depends(get_db),
) -> list[dict]:
    return painel_repo.history(db, painel_repo.window_to_months(window))


@router.get("/painel/by-tag")
def painel_by_tag(
    month: str | None = Query(default=None),
    type: str = Query(default="expense"),
    db: Database = Depends(get_db),
) -> dict:
    if type not in {"expense", "income"}:
        raise HTTPException(status_code=422, detail="type inválido")
    return painel_repo.by_tag(db, _resolve_month_or_422(db, month), type)  # type: ignore[arg-type]
