from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ...storage import Database
from ..dependencies import get_db
from ..repositories import profile_repo

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile")
def get_profile(db: Database = Depends(get_db)) -> dict[str, Any]:
    return profile_repo.get_profile(db)
