from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ...storage import Database
from ..dependencies import get_db
from ..repositories import buckets_repo

router = APIRouter(prefix="/api", tags=["buckets"])


@router.get("/buckets")
def list_buckets(db: Database = Depends(get_db)) -> dict[str, list[dict[str, Any]]]:
    return {"items": buckets_repo.list_buckets(db)}
