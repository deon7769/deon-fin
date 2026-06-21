from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ...storage import Database
from ..dependencies import get_db
from ..repositories import tags_repo

router = APIRouter(prefix="/api", tags=["tags"])


@router.get("/tags")
def list_tags(db: Database = Depends(get_db)) -> dict[str, list[dict[str, Any]]]:
    return {"items": tags_repo.list_tags(db)}
