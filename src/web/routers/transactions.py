from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from ...storage import Database
from ..dependencies import get_db
from ..repositories import transactions_repo

router = APIRouter(prefix="/api", tags=["transactions"])


class TransactionBucketPatch(BaseModel):
    bucket_id: int | None = None


class TransactionBucketPost(BaseModel):
    bucket_id: int | None = None
    apply_to_similar: bool = False


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


@router.patch("/transactions/{transaction_id}")
def patch_transaction_bucket(
    transaction_id: str,
    body: TransactionBucketPatch,
    db: Database = Depends(get_db),
) -> dict:
    return _set_bucket_or_raise(
        db,
        transaction_id,
        bucket_id=body.bucket_id,
        apply_to_similar=False,
    )


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
