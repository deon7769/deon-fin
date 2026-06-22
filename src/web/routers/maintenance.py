from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...storage import Database
from ..dependencies import get_db
from ..repositories import system_totals_repo

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


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
