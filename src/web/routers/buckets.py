from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ...agent.buckets import apply_buckets_to_database
from ...storage import Database
from ..dependencies import get_db
from ..repositories import buckets_repo

router = APIRouter(prefix="/api", tags=["buckets"])


@router.get("/buckets")
def list_buckets(db: Database = Depends(get_db)) -> dict[str, list[dict[str, Any]]]:
    buckets_repo.seed_buckets(db)
    return {"items": buckets_repo.list_buckets(db)}


@router.post("/buckets/reclassify")
def reclassify_buckets(db: Database = Depends(get_db)) -> dict[str, dict[str, int]]:
    buckets_repo.seed_buckets(db)
    return {"stats": apply_buckets_to_database(db)}
