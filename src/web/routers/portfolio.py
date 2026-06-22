from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...agent.portfolio import quotes
from ...storage import Database
from ..dependencies import get_db
from ..repositories import portfolio_repo

router = APIRouter(prefix="/api", tags=["portfolio"])


class AssetCreateRequest(BaseModel):
    asset_class: str
    ticker: str | None = None
    name: str | None = None
    quantity: float | None = None
    manual_value: float | None = None


class AssetPatchRequest(BaseModel):
    asset_class: str | None = None
    ticker: str | None = None
    name: str | None = None
    quantity: float | None = None
    manual_value: float | None = None


def _fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is None:
        fields = getattr(model, "__fields_set__", set())
    return set(fields)


def _repo_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/investments")
def investments_summary(
    include_inactive: bool = Query(default=False),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    return portfolio_repo.portfolio_summary(db, include_inactive=include_inactive)


@router.get("/investments/ticker-search")
def ticker_search(
    q: str = Query(default=""),
    classe: str = Query(default="acoes_nac"),
) -> dict[str, Any]:
    try:
        return {"items": quotes.search_ticker(q, classe)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/investments/assets", status_code=201)
def create_asset(
    body: AssetCreateRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    unit_price = None
    price_updated_at = None
    price_source = None
    ticker = body.ticker.upper() if body.ticker else None
    if ticker and body.asset_class in quotes.QUOTEABLE_CLASSES:
        try:
            quote = quotes.get_quotes(db, [ticker], body.asset_class).get(ticker)
        except Exception:
            quote = None
        if quote:
            unit_price = float(quote["price"])
            price_updated_at = str(quote.get("ts") or "")
            price_source = "brapi"
    try:
        return portfolio_repo.create_manual_asset(
            db,
            asset_class=body.asset_class,
            ticker=ticker,
            name=body.name,
            quantity=body.quantity,
            manual_value=body.manual_value,
            unit_price=unit_price,
            price_source=price_source,
            price_updated_at=price_updated_at,
        )
    except ValueError as exc:
        raise _repo_error(exc) from exc


@router.patch("/investments/assets/{asset_id}")
def update_asset(
    asset_id: int,
    body: AssetPatchRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    fields = _fields_set(body)
    if not fields:
        raise HTTPException(status_code=422, detail="corpo vazio")
    updates = {field: getattr(body, field) for field in fields}
    try:
        asset = portfolio_repo.update_asset(db, asset_id, **updates)
    except ValueError as exc:
        raise _repo_error(exc) from exc
    if asset is None:
        raise HTTPException(status_code=404, detail="ativo não encontrado")
    return asset


@router.delete("/investments/assets/{asset_id}")
def delete_asset(asset_id: int, db: Database = Depends(get_db)) -> dict[str, int]:
    result = portfolio_repo.delete_asset(db, asset_id)
    if result is None:
        raise HTTPException(status_code=404, detail="ativo não encontrado")
    return result


@router.post("/investments/refresh-quotes")
def refresh_quotes(db: Database = Depends(get_db)) -> dict[str, int]:
    try:
        return quotes.refresh_prices(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
