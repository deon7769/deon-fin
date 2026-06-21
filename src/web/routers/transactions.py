from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ...storage import Database
from ..dependencies import get_db
from ..repositories import transactions_repo

router = APIRouter(prefix="/api", tags=["transactions"])
_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class TransactionPatch(BaseModel):
    bucket_id: int | None = None
    tag_id: int | None = None
    hidden: bool | None = None
    note: str | None = None
    reference_month: str | None = None


class TransactionBucketPost(BaseModel):
    bucket_id: int | None = None
    apply_to_similar: bool = False


class TransactionCreate(BaseModel):
    account_id: str
    posted_at: str
    amount: float
    type: Literal["income", "expense"]
    description: str
    bucket_id: int | None = None
    tag_id: int | None = None
    note: str | None = None
    reference_month: str | None = None


class BulkTransactionPatch(BaseModel):
    ids: list[str]
    patch: TransactionPatch


def _fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is None:
        fields = getattr(model, "__fields_set__", set())
    return set(fields)


def _validate_year_month(value: str | None, *, field: str = "month") -> str | None:
    if value is None:
        return None
    if not _YEAR_MONTH_RE.match(value):
        raise HTTPException(status_code=422, detail=f"{field} inválido")
    month = int(value[5:7])
    if month < 1 or month > 12:
        raise HTTPException(status_code=422, detail=f"{field} inválido")
    return value


def _parse_date(value: str | None, *, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field} inválido") from exc


def _parse_optional_ids(value: str | None, *, field: str) -> list[int | None] | None:
    if value is None or value.strip() == "":
        return None

    parsed: list[int | None] = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if token == "none":
            parsed.append(None)
            continue
        try:
            parsed.append(int(token))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{field} inválido") from exc
    return parsed or None


def _patch_kwargs(body: TransactionPatch) -> dict:
    fields = _fields_set(body)
    if not fields:
        raise HTTPException(status_code=422, detail="corpo vazio")
    if "reference_month" in fields and body.reference_month is not None:
        _validate_year_month(body.reference_month, field="reference_month")

    kwargs: dict = {}
    if "bucket_id" in fields:
        kwargs["bucket_id"] = body.bucket_id
    if "tag_id" in fields:
        kwargs["tag_id"] = body.tag_id
    if "hidden" in fields:
        kwargs["hidden"] = bool(body.hidden)
    if "note" in fields:
        kwargs["note"] = body.note
    if "reference_month" in fields:
        kwargs["reference_month"] = body.reference_month
    return kwargs


def _update_or_raise(db: Database, transaction_id: str, **kwargs) -> dict:
    try:
        return transactions_repo.update_transaction(db, transaction_id, **kwargs)
    except transactions_repo.TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="transação não encontrada") from exc
    except (transactions_repo.BucketNotFoundError, transactions_repo.TagNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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


@router.get("/transactions")
def get_transactions(
    month: str | None = None,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = None,
    q: str | None = None,
    type: Literal["income", "expense"] | None = None,
    min: float | None = Query(default=None),
    max: float | None = Query(default=None),
    account_id: str | None = None,
    bucket_ids: str | None = None,
    tag_ids: str | None = None,
    hidden: Literal["exclude", "include", "only"] = "exclude",
    page: int = 1,
    page_size: int = 25,
    db: Database = Depends(get_db),
) -> dict:
    if min is not None and max is not None and min > max:
        raise HTTPException(status_code=422, detail="faixa de valor inválida")

    return transactions_repo.list_transactions(
        db,
        month=_validate_year_month(month),
        date_from=_parse_date(from_, field="from"),
        date_to=_parse_date(to, field="to"),
        q=q,
        type=type,
        amount_min=min,
        amount_max=max,
        account_id=account_id,
        bucket_ids=_parse_optional_ids(bucket_ids, field="bucket_ids"),
        tag_ids=_parse_optional_ids(tag_ids, field="tag_ids"),
        hidden=hidden,
        page=page,
        page_size=page_size,
    )


@router.post("/transactions")
def create_transaction(
    body: TransactionCreate,
    response: Response,
    db: Database = Depends(get_db),
) -> dict:
    if body.amount <= 0:
        raise HTTPException(status_code=422, detail="valor deve ser positivo")
    description = " ".join(body.description.split())
    if not description:
        raise HTTPException(status_code=422, detail="descrição obrigatória")
    posted_at = _parse_date(body.posted_at, field="posted_at")
    if posted_at is None:
        raise HTTPException(status_code=422, detail="posted_at obrigatório")
    if body.reference_month is not None:
        _validate_year_month(body.reference_month, field="reference_month")

    try:
        result = transactions_repo.create_manual_transaction(
            db,
            account_id=body.account_id,
            posted_at=posted_at,
            amount=body.amount,
            type=body.type,
            description=description,
            bucket_id=body.bucket_id,
            tag_id=body.tag_id,
            note=body.note,
            reference_month_override=body.reference_month,
        )
    except transactions_repo.AccountNotFoundError as exc:
        raise HTTPException(status_code=422, detail="conta inválida") from exc
    except (transactions_repo.BucketNotFoundError, transactions_repo.TagNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response.status_code = 200 if result["duplicate"] else 201
    return result


@router.patch("/transactions/bulk")
def bulk_update_transactions(
    body: BulkTransactionPatch,
    db: Database = Depends(get_db),
) -> dict:
    if not body.ids:
        raise HTTPException(status_code=422, detail="ids obrigatórios")
    kwargs = _patch_kwargs(body.patch)
    try:
        return transactions_repo.bulk_update_transactions(db, body.ids, **kwargs)
    except (transactions_repo.BucketNotFoundError, transactions_repo.TagNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/transactions/{transaction_id}")
def patch_transaction(
    transaction_id: str,
    body: TransactionPatch,
    db: Database = Depends(get_db),
) -> dict:
    return _update_or_raise(db, transaction_id, **_patch_kwargs(body))


@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    db: Database = Depends(get_db),
) -> dict:
    try:
        deleted_id = transactions_repo.delete_transaction(db, transaction_id)
    except transactions_repo.TransactionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="transação não encontrada") from exc
    return {"deleted_id": deleted_id}


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
