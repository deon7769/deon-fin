from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...agent.buckets import apply_buckets_to_database
from ...agent.tags import apply_tags_to_database
from ...storage import Database
from ..dependencies import get_db
from ..repositories import buckets_repo, system_totals_repo, tags_repo, transactions_repo

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class AccountTotalSettingInput(BaseModel):
    account_id: str
    include_balance: bool = True
    include_transactions: bool = True


class MovementTotalSettingInput(BaseModel):
    movement_type: str
    include_in_totals: bool = True


class SystemTotalsSettingsPatch(BaseModel):
    accounts: list[AccountTotalSettingInput] = []
    movements: list[MovementTotalSettingInput] = []


class ClassificationBulkRequest(BaseModel):
    kind: Literal["tag", "bucket"]
    target_id: int
    month: str | None = None


def _validate_year_month(value: str | None) -> str | None:
    if value is None:
        return None
    if not _YEAR_MONTH_RE.match(value):
        raise HTTPException(status_code=422, detail="month inválido")
    month = int(value[5:7])
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail="month inválido")
    return value


def _bulk_quality(kind: Literal["tag", "bucket"]) -> Literal["missing_tag", "missing_bucket"]:
    return "missing_tag" if kind == "tag" else "missing_bucket"


def _target_name(db: Database, kind: Literal["tag", "bucket"], target_id: int) -> str:
    if kind == "tag":
        row = tags_repo.get_tag(db, target_id)
        if row is None:
            raise HTTPException(status_code=422, detail=f"tag_id inválido: {target_id}")
        return str(row["name"])

    if not buckets_repo.bucket_exists(db, target_id):
        raise HTTPException(status_code=422, detail=f"bucket_id inválido: {target_id}")
    bucket = next(
        bucket for bucket in buckets_repo.list_buckets(db) if int(bucket["id"]) == target_id
    )
    return str(bucket["name"])


def _preview_item(item: dict[str, Any]) -> dict[str, Any]:
    amount = item.get("display_value", item.get("amount", 0.0))
    return {
        "id": item["id"],
        "date": str(item.get("posted_at") or "")[:10],
        "description": item.get("description"),
        "account_name": item.get("account_name") or item.get("account_id"),
        "category": item.get("category"),
        "category_label": item.get("category_label") or item.get("category"),
        "amount_abs": round(abs(float(amount or 0.0)), 2),
    }


def _classification_candidates(
    db: Database,
    *,
    kind: Literal["tag", "bucket"],
    month: str | None,
) -> list[dict[str, Any]]:
    quality = _bulk_quality(kind)
    page = 1
    items: list[dict[str, Any]] = []
    total = 0
    while True:
        result = transactions_repo.list_transactions(
            db,
            month=month,
            quality=quality,
            hidden="exclude",
            page=page,
            page_size=100,
        )
        total = int(result["total"])
        items.extend(result["items"])
        if len(items) >= total or not result["items"]:
            break
        page += 1
    return items


def _bulk_preview_response(
    db: Database,
    body: ClassificationBulkRequest,
) -> dict[str, Any]:
    month = _validate_year_month(body.month)
    target_name = _target_name(db, body.kind, body.target_id)
    candidates = _classification_candidates(db, kind=body.kind, month=month)
    preview_items = [_preview_item(item) for item in candidates]
    return {
        "kind": body.kind,
        "target_id": body.target_id,
        "target_name": target_name,
        "month": month,
        "total": len(preview_items),
        "total_abs": round(sum(item["amount_abs"] for item in preview_items), 2),
        "items": preview_items[:10],
    }


@router.get("/system-totals")
def get_system_totals(db: Database = Depends(get_db)) -> dict:
    return system_totals_repo.list_settings(db)


@router.patch("/system-totals")
def update_system_totals(
    payload: SystemTotalsSettingsPatch,
    db: Database = Depends(get_db),
) -> dict:
    try:
        system_totals_repo.update_settings(
            db,
            accounts=[item.model_dump() for item in payload.accounts],
            movements=[item.model_dump() for item in payload.movements],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return system_totals_repo.list_settings(db)


@router.post("/classification/reprocess")
def reprocess_classification(db: Database = Depends(get_db)) -> dict:
    bucket_stats = apply_buckets_to_database(db)
    tag_stats = apply_tags_to_database(db)
    changed = (
        int(bucket_stats.get("by_rule", 0))
        + int(bucket_stats.get("by_map", 0))
        + int(tag_stats.get("by_rule", 0))
        + int(tag_stats.get("by_map", 0))
    )
    return {
        "changed": changed,
        "bucket": bucket_stats,
        "tag": tag_stats,
    }


@router.post("/classification/bulk-preview")
def preview_classification_bulk(
    body: ClassificationBulkRequest,
    db: Database = Depends(get_db),
) -> dict:
    return _bulk_preview_response(db, body)


@router.post("/classification/bulk-apply")
def apply_classification_bulk(
    body: ClassificationBulkRequest,
    db: Database = Depends(get_db),
) -> dict:
    preview = _bulk_preview_response(db, body)
    ids = [item["id"] for item in _classification_candidates(db, kind=body.kind, month=preview["month"])]
    patch = {"tag_id": body.target_id} if body.kind == "tag" else {"bucket_id": body.target_id}
    result = transactions_repo.bulk_update_transactions(db, ids, **patch)
    return {
        "kind": body.kind,
        "target_id": body.target_id,
        "target_name": preview["target_name"],
        "month": preview["month"],
        "preview_total": preview["total"],
        "updated": result["updated"],
        "not_found": result["not_found"],
    }
