from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...agent.buckets import apply_buckets_to_database
from ...storage import Database
from ..dependencies import get_db
from ..repositories import buckets_repo, budget_repo

router = APIRouter(prefix="/api", tags=["buckets"])


class BucketPatch(BaseModel):
    name: str | None = None
    color: str | None = None
    planned_kind: str | None = None
    planned_value: float | None = None


class BucketSortRequest(BaseModel):
    order: list[int]


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


@router.get("/buckets")
def list_buckets(db: Database = Depends(get_db)) -> dict[str, list[dict[str, Any]]]:
    buckets_repo.seed_buckets(db)
    return {"items": buckets_repo.list_buckets(db)}


@router.get("/buckets/plan")
def bucket_plan(
    month: str | None = Query(default=None),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    return buckets_repo.bucket_plan(db, _resolve_month_or_422(db, month))


@router.patch("/buckets/sort")
def sort_buckets(
    body: BucketSortRequest,
    db: Database = Depends(get_db),
) -> dict[str, int]:
    buckets_repo.seed_buckets(db)
    try:
        updated = buckets_repo.set_sort(db, body.order)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"updated": updated}


@router.patch("/buckets/{bucket_id}")
def update_bucket(
    bucket_id: int,
    body: BucketPatch,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    buckets_repo.seed_buckets(db)
    fields = _fields_set(body)
    if not fields:
        raise HTTPException(status_code=422, detail="corpo vazio")

    updates: dict[str, Any] = {}
    for field in ("name", "color", "planned_kind", "planned_value"):
        if field in fields:
            updates[field] = getattr(body, field)

    try:
        bucket = buckets_repo.set_planned(db, bucket_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if bucket is None:
        raise HTTPException(status_code=404, detail="bucket não encontrado")
    return bucket


@router.post("/buckets/reclassify")
def reclassify_buckets(db: Database = Depends(get_db)) -> dict[str, dict[str, int]]:
    buckets_repo.seed_buckets(db)
    return {"stats": apply_buckets_to_database(db)}
