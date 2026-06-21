from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...storage import Database
from ..dependencies import get_db
from ..repositories import invoices_repo

router = APIRouter(prefix="/api", tags=["invoices"])


@router.get("/cards")
def cards(db: Database = Depends(get_db)) -> dict:
    return {"items": invoices_repo.list_cards(db)}


@router.get("/invoices")
def invoice(
    account_id: str | None = Query(default=None),
    month: str | None = Query(default=None),
    db: Database = Depends(get_db),
) -> dict:
    if not account_id:
        raise HTTPException(status_code=422, detail="account_id é obrigatório")

    resolved_month = invoices_repo.resolve_month(db, month)
    if resolved_month is None:
        raise HTTPException(status_code=422, detail="month deve ser YYYY-MM")

    result = invoices_repo.get_invoice(db, account_id=account_id, month=resolved_month)
    if result is None:
        raise HTTPException(status_code=404, detail="cartão não encontrado")
    return result
