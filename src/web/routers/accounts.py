from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from pydantic import BaseModel

from ...pluggy import PluggyAPIError, PluggyClient
from ...storage import Database
from ..dependencies import get_db, get_pluggy
from ..repositories import accounts_repo

router = APIRouter(prefix="/api", tags=["accounts"])


class SyncRequest(BaseModel):
    days: int = 365


class SortRequest(BaseModel):
    order: list[str]


def _item_or_404(db: Database, account_id: str) -> str:
    item_id = accounts_repo.resolve_item_id(db, account_id)
    if not item_id or not db.get_pluggy_item(item_id):
        raise HTTPException(status_code=404, detail="conta sem conexão Pluggy ativa")
    return item_id


def _sync_snapshot() -> dict[str, Any]:
    from .. import app as web_app

    return {
        **web_app._sync_state,
        "auto_sync_minutes": web_app.settings.auto_sync_minutes,
    }


@router.get("/accounts")
def list_accounts(
    month: str | None = Query(default=None),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    resolved = accounts_repo.resolve_month(db, month)
    if resolved is None:
        raise HTTPException(status_code=422, detail="month deve ser YYYY-MM")
    return {
        **accounts_repo.list_accounts_overview(db, month=resolved),
        "sync": _sync_snapshot(),
    }


@router.post("/accounts/{account_id}/sync")
def sync_account(
    account_id: str,
    bg: BackgroundTasks,
    body: SyncRequest | None = Body(default=None),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    from .. import app as web_app

    item_id = _item_or_404(db, account_id)
    days = web_app._normalized_days(body.days if body else None)
    if web_app._sync_state["running"]:
        return {
            "account_id": account_id,
            "item_id": item_id,
            "sync_scheduled": False,
            "detail": "já em andamento",
            "days": days,
        }
    bg.add_task(web_app._background_sync, item_id, days)
    return {
        "account_id": account_id,
        "item_id": item_id,
        "sync_scheduled": True,
        "days": days,
    }


@router.post("/accounts/{account_id}/credentials")
def account_credentials(
    account_id: str,
    db: Database = Depends(get_db),
    pc: PluggyClient = Depends(get_pluggy),
) -> dict[str, str]:
    item_id = _item_or_404(db, account_id)
    try:
        token = pc.create_connect_token(item_id=item_id)
    except PluggyAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"accessToken": token}


@router.delete("/accounts/{account_id}")
def delete_account_connection(
    account_id: str,
    db: Database = Depends(get_db),
    pc: PluggyClient = Depends(get_pluggy),
) -> dict[str, Any]:
    item_id = _item_or_404(db, account_id)
    try:
        pc.delete_item(item_id)
    except PluggyAPIError as exc:
        if exc.status != 404:
            raise HTTPException(status_code=502, detail=str(exc))
    return accounts_repo.disconnect(db, item_id)


@router.patch("/accounts/sort")
def sort_accounts(
    body: SortRequest,
    db: Database = Depends(get_db),
) -> dict[str, int]:
    return {"updated": accounts_repo.set_sort(db, body.order)}
