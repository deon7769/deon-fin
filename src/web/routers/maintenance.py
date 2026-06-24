from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...agent import maintenance as mnt
from ...agent import tags as tag_agent
from ...agent.buckets import CATEGORY_BUCKET_MAP, apply_buckets_to_database
from ...agent.tags import apply_tags_to_database
from ...storage import Database
from ..dependencies import get_db
from ..repositories import (
    buckets_repo,
    classification_audit_repo,
    system_totals_repo,
    tags_repo,
    transactions_repo,
)

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


class ClassificationRulePatch(BaseModel):
    kind: Literal["tag", "bucket"]
    match_key: str
    target_id: int | None = None


class ClassificationApplyRequest(BaseModel):
    kind: Literal["tag", "bucket"]
    transaction_id: str
    target_id: int | None = None
    apply_to_similar: bool = False


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


def _clean_match_key(value: str) -> str:
    match_key = " ".join((value or "").split())
    if not match_key:
        raise HTTPException(status_code=422, detail="match_key obrigatório")
    return match_key


def _classification_rules_response(db: Database) -> dict[str, list[dict[str, Any]]]:
    tag_rows = tags_repo.list_rules_with_targets(db)
    bucket_rows = buckets_repo.list_rules_with_targets(db)
    return {
        "tag_rules": [
            {
                "kind": "tag",
                "match_key": row["match_key"],
                "target_id": row["target_id"],
                "target_name": row["target_name"],
                "target_color": row["target_color"],
            }
            for row in tag_rows
        ],
        "bucket_rules": [
            {
                "kind": "bucket",
                "match_key": row["match_key"],
                "target_id": row["target_id"],
                "target_name": row["target_name"],
                "target_color": row["target_color"],
            }
            for row in bucket_rows
        ],
    }


def _save_classification_rule(db: Database, body: ClassificationRulePatch) -> dict[str, Any]:
    match_key = _clean_match_key(body.match_key)
    if body.target_id is None:
        if body.kind == "tag":
            tags_repo.delete_rule(db, match_key)
        else:
            buckets_repo.delete_rule(db, match_key)
        return {
            "action": "rule_delete",
            "kind": body.kind,
            "target_id": None,
            "target_name": None,
            "match_key": match_key,
        }

    target_name = _target_name(db, body.kind, body.target_id)
    if body.kind == "tag":
        tags_repo.upsert_rule(db, match_key, body.target_id)
    else:
        buckets_repo.upsert_rule(db, match_key, body.target_id)
    return {
        "action": "rule_update",
        "kind": body.kind,
        "target_id": body.target_id,
        "target_name": target_name,
        "match_key": match_key,
    }


def _apply_classification_response(db: Database, body: ClassificationApplyRequest) -> dict[str, Any]:
    target_name = _target_name(db, body.kind, body.target_id) if body.target_id is not None else None
    try:
        if body.kind == "tag":
            result = transactions_repo.set_tag(
                db,
                body.transaction_id,
                tag_id=body.target_id,
                apply_to_similar=body.apply_to_similar,
            )
        else:
            result = transactions_repo.set_bucket(
                db,
                body.transaction_id,
                bucket_id=body.target_id,
                apply_to_similar=body.apply_to_similar,
            )
    except transactions_repo.TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="transaÃ§Ã£o nÃ£o encontrada") from exc
    except (transactions_repo.TagNotFoundError, transactions_repo.BucketNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    affected_transaction_ids = [body.transaction_id, *result.get("similar_ids", [])]
    action = "similar_apply" if body.apply_to_similar else "single_apply"
    classification_audit_repo.record(
        db,
        action=action,
        kind=body.kind,
        target_id=body.target_id,
        target_name=target_name,
        match_key=result.get("match_key"),
        affected_count=len(affected_transaction_ids),
        preview_total=len(affected_transaction_ids),
        metadata={
            "transaction_id": body.transaction_id,
            "affected_transaction_ids": affected_transaction_ids,
            "similar_affected": int(result.get("similar_affected", 0) or 0),
        },
    )
    return {
        "kind": body.kind,
        "transaction_id": body.transaction_id,
        "target_id": body.target_id,
        "target_name": target_name,
        "match_key": result.get("match_key"),
        "affected_count": len(affected_transaction_ids),
        "affected_transaction_ids": affected_transaction_ids,
        "similar_affected": int(result.get("similar_affected", 0) or 0),
    }


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


def _bucket_suggestion(bucket: dict[str, Any] | None, bucket_key: str | None) -> dict[str, Any] | None:
    if bucket is None:
        if not bucket_key:
            return None
        return {
            "id": None,
            "key": bucket_key,
            "name": bucket_key,
            "color": None,
        }
    return {
        "id": bucket["id"],
        "key": bucket["key"],
        "name": bucket["name"],
        "color": bucket["color"],
    }


def _suggested_tag(
    db: Database,
    item: dict[str, Any],
    cat_map: dict[str, str],
    buckets_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    category = str(item.get("category") or "").strip()
    category_key = category.lower()
    tag_name: str | None = None
    bucket_key: str | None = None
    source: str | None = None

    if category_key and category_key not in tag_agent.BLOCKED_CATEGORY_KEYS:
        translated = cat_map.get(category_key)
        if not translated and category_key in CATEGORY_BUCKET_MAP:
            translated = category
        if translated:
            tag_name = translated
            bucket_key = CATEGORY_BUCKET_MAP.get(category_key)
            source = "category"

    if tag_name is None:
        raw_text = str(item.get("raw_description") or item.get("description") or "").lower()
        for needle, merchant_tag in tag_agent.TAG_MERCHANT_MAP.items():
            if needle in raw_text:
                tag_name, bucket_key = merchant_tag
                source = "merchant"
                break

    if tag_name is None:
        return None

    existing = tags_repo.find_tag_by_name(db, tag_name)
    bucket = buckets_by_key.get(bucket_key or "")
    return {
        "id": existing["id"] if existing else None,
        "name": existing["name"] if existing else tag_name,
        "color": existing["color"] if existing else tags_repo.default_tag_color(tag_name),
        "bucket_id": existing["bucket_id"] if existing else (bucket["id"] if bucket else None),
        "bucket_key": existing["bucket_key"] if existing else bucket_key,
        "bucket_name": existing["bucket_name"] if existing else (bucket["name"] if bucket else None),
        "source": source,
    }


def _classification_suggestions_response(db: Database, month: str | None) -> dict[str, Any]:
    month = _validate_year_month(month)
    buckets_repo.seed_buckets(db)
    tags_repo.seed_tags_if_empty(db)
    cat_map = mnt.load_overrides()["categorias_pt"]
    buckets_by_key = {bucket["key"]: bucket for bucket in buckets_repo.list_buckets(db)}
    groups: dict[str, dict[str, Any]] = {}

    for kind in ("tag", "bucket"):
        for item in _classification_candidates(db, kind=kind, month=month):
            raw_category = item.get("category") or "(sem categoria)"
            group_key = str(raw_category).strip().lower()
            group = groups.setdefault(
                group_key,
                {
                    "raw_category": raw_category,
                    "category_label": item.get("category_label") or raw_category,
                    "sample": item,
                    "ids": set(),
                    "missing_tag_ids": set(),
                    "missing_bucket_ids": set(),
                    "total_abs_by_id": {},
                    "examples": [],
                },
            )
            group["ids"].add(item["id"])
            if kind == "tag":
                group["missing_tag_ids"].add(item["id"])
            else:
                group["missing_bucket_ids"].add(item["id"])
            amount_abs = round(abs(float(item.get("display_value", item.get("amount", 0.0)) or 0.0)), 2)
            group["total_abs_by_id"][item["id"]] = amount_abs
            if len(group["examples"]) < 5 and item["id"] not in {row["id"] for row in group["examples"]}:
                group["examples"].append(_preview_item(item))

    items: list[dict[str, Any]] = []
    for group in groups.values():
        sample = group["sample"]
        category_key = str(group["raw_category"] or "").strip().lower()
        bucket_key = CATEGORY_BUCKET_MAP.get(category_key)
        tag = _suggested_tag(db, sample, cat_map, buckets_by_key)
        if bucket_key is None and tag is not None:
            bucket_key = tag.get("bucket_key")
        bucket = _bucket_suggestion(buckets_by_key.get(bucket_key or ""), bucket_key)
        translated = mnt.translate_category(str(group["raw_category"]), cat_map)
        items.append(
            {
                "raw_category": group["raw_category"],
                "category_label": group["category_label"],
                "suggested_translation": translated,
                "transaction_count": len(group["ids"]),
                "missing_tag_count": len(group["missing_tag_ids"]),
                "missing_bucket_count": len(group["missing_bucket_ids"]),
                "total_abs": round(sum(group["total_abs_by_id"].values()), 2),
                "suggested_tag": tag,
                "suggested_bucket": bucket,
                "examples": group["examples"],
            }
        )

    items.sort(key=lambda row: (-int(row["transaction_count"]), str(row["raw_category"]).lower()))
    return {"month": month, "total": len(items), "items": items}


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


@router.get("/classification/suggestions")
def list_classification_suggestions(
    month: str | None = None,
    db: Database = Depends(get_db),
) -> dict:
    return _classification_suggestions_response(db, month)


@router.post("/classification/bulk-apply")
def apply_classification_bulk(
    body: ClassificationBulkRequest,
    db: Database = Depends(get_db),
) -> dict:
    preview = _bulk_preview_response(db, body)
    ids = [item["id"] for item in _classification_candidates(db, kind=body.kind, month=preview["month"])]
    patch = {"tag_id": body.target_id} if body.kind == "tag" else {"bucket_id": body.target_id}
    result = transactions_repo.bulk_update_transactions(db, ids, **patch)
    classification_audit_repo.record(
        db,
        action="bulk_apply",
        kind=body.kind,
        target_id=body.target_id,
        target_name=preview["target_name"],
        affected_count=int(result["updated"]),
        preview_total=int(preview["total"]),
        metadata={"month": preview["month"], "not_found": result["not_found"]},
    )
    return {
        "kind": body.kind,
        "target_id": body.target_id,
        "target_name": preview["target_name"],
        "month": preview["month"],
        "preview_total": preview["total"],
        "updated": result["updated"],
        "not_found": result["not_found"],
    }


@router.post("/classification/apply")
def apply_classification(
    body: ClassificationApplyRequest,
    db: Database = Depends(get_db),
) -> dict:
    return _apply_classification_response(db, body)


@router.get("/classification/rules")
def list_classification_rules(db: Database = Depends(get_db)) -> dict:
    return _classification_rules_response(db)


@router.get("/classification/audit")
def list_classification_audit(
    limit: int = 20,
    db: Database = Depends(get_db),
) -> dict:
    return {"items": classification_audit_repo.list_recent(db, limit=limit)}


@router.patch("/classification/rules")
def save_classification_rule(
    body: ClassificationRulePatch,
    db: Database = Depends(get_db),
) -> dict:
    audit = _save_classification_rule(db, body)
    classification_audit_repo.record(db, **audit)
    return _classification_rules_response(db)
