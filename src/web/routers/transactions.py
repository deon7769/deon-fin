from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from ...storage import Database
from ..dependencies import get_db
from ..repositories import transactions_repo

router = APIRouter(prefix="/api", tags=["transactions"])


class TransactionPatch(BaseModel):
    bucket_id: int | None = None
    tag_id: int | None = None


class TransactionBucketPost(BaseModel):
    bucket_id: int | None = None
    apply_to_similar: bool = False


def _fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is None:
        fields = getattr(model, "__fields_set__", set())
    return set(fields)


def _set_bucket_or_raise(
    db: Database,
    transaction_id: str,
    *,
    bucket_id: int | None,
    apply_to_similar: bool,
) -> dict:
    try:
        return transactions_repo.set_bucket(
            db,
            transaction_id,
            bucket_id=bucket_id,
            apply_to_similar=apply_to_similar,
        )
    except transactions_repo.TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="transação não encontrada") from exc
    except transactions_repo.BucketNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _set_tag_or_raise(
    db: Database,
    transaction_id: str,
    *,
    tag_id: int | None,
) -> dict:
    try:
        return transactions_repo.set_tag(db, transaction_id, tag_id=tag_id)
    except transactions_repo.TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="transação não encontrada") from exc
    except transactions_repo.TagNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/transactions/{transaction_id}")
def patch_transaction(
    transaction_id: str,
    body: TransactionPatch,
    db: Database = Depends(get_db),
) -> dict:
    fields = _fields_set(body)
    result: dict = {"updated": 0}

    if "bucket_id" in fields:
        result.update(
            _set_bucket_or_raise(
                db,
                transaction_id,
                bucket_id=body.bucket_id,
                apply_to_similar=False,
            )
        )

    if "tag_id" in fields:
        result.update(
            _set_tag_or_raise(
                db,
                transaction_id,
                tag_id=body.tag_id,
            )
        )

    return result


@router.post("/transactions/{transaction_id}/bucket")
def set_transaction_bucket(
    transaction_id: str,
    body: TransactionBucketPost,
    db: Database = Depends(get_db),
) -> dict:
    return _set_bucket_or_raise(
        db,
        transaction_id,
        bucket_id=body.bucket_id,
        apply_to_similar=body.apply_to_similar,
    )
