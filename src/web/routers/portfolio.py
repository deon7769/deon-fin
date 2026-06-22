from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from ...storage import Database
from ..dependencies import get_db
from ..repositories import portfolio_repo

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/investments")
def investments_summary(
    include_inactive: bool = Query(default=False),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    return portfolio_repo.portfolio_summary(db, include_inactive=include_inactive)
