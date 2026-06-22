from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import httpx

from ...config import settings
from ...storage import Database


QUOTEABLE_CLASSES = {"acoes_nac", "acoes_int", "fii", "reit", "cripto"}

Quote = dict[str, Any]
QuoteFetcher = Callable[[list[str], str, str | None], dict[str, Quote]]


def _normal_symbol(symbol: str) -> str:
    return str(symbol or "").strip().upper()


def _normal_ts(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    text = str(value or "").strip()
    return text or datetime.utcnow().isoformat(timespec="seconds")


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _brapi_fetcher(symbols: list[str], asset_class: str, token: str | None = None) -> dict[str, Quote]:
    if not symbols:
        return {}
    params: dict[str, str] = {}
    if token:
        params["token"] = token
    url = "https://brapi.dev/api/quote/" + ",".join(symbols)
    resp = httpx.get(url, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    quotes: dict[str, Quote] = {}
    for item in payload.get("results", []):
        symbol = _normal_symbol(item.get("symbol") or item.get("stock"))
        if not symbol:
            continue
        price = item.get("regularMarketPrice") or item.get("close")
        if price is None:
            continue
        currency = item.get("currency") or "BRL"
        ts_raw = item.get("regularMarketTime") or item.get("updatedAt")
        if isinstance(ts_raw, (int, float)):
            ts = datetime.fromtimestamp(ts_raw).isoformat(timespec="seconds")
        else:
            ts = _normal_ts(ts_raw)
        quotes[symbol] = {"price": float(price), "currency": currency, "ts": ts}
    return quotes


def search_ticker(q: str, asset_class: str, *, token: str | None = None) -> list[dict[str, str]]:
    query = str(q or "").strip()
    if len(query) < 2:
        return []
    params = {"search": query}
    brapi_token = settings.brapi_token if token is None else token
    if brapi_token:
        params["token"] = brapi_token
    resp = httpx.get("https://brapi.dev/api/available", params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    raw_items = payload.get("stocks") or payload.get("results") or []
    items: list[dict[str, str]] = []
    for item in raw_items:
        if isinstance(item, str):
            items.append({"ticker": item.upper(), "name": item.upper()})
            continue
        ticker = _normal_symbol(item.get("stock") or item.get("symbol") or item.get("ticker"))
        if not ticker:
            continue
        items.append({"ticker": ticker, "name": str(item.get("name") or ticker)})
    return items[:20]


def get_quotes(
    db: Database,
    symbols: list[str],
    asset_class: str,
    *,
    fetcher: QuoteFetcher | None = None,
    ttl_minutes: int | None = None,
    token: str | None = None,
    now: datetime | None = None,
) -> dict[str, Quote]:
    now_dt = now or datetime.utcnow()
    ttl = ttl_minutes if ttl_minutes is not None else settings.quotes_ttl_min
    normalized = []
    seen: set[str] = set()
    for symbol in symbols:
        normal = _normal_symbol(symbol)
        if normal and normal not in seen:
            normalized.append(normal)
            seen.add(normal)
    if not normalized:
        return {}

    result: dict[str, Quote] = {}
    missing: list[str] = []
    for symbol in normalized:
        row = db._conn.execute(
            """
            SELECT price, currency, fetched_at
              FROM quote_cache
             WHERE symbol=? AND asset_class=?
            """,
            (symbol, asset_class),
        ).fetchone()
        fetched_at = _parse_ts(row["fetched_at"]) if row else None
        if (
            row
            and row["price"] is not None
            and fetched_at is not None
            and now_dt - fetched_at <= timedelta(minutes=ttl)
        ):
            result[symbol] = {
                "price": float(row["price"]),
                "currency": row["currency"] or "BRL",
                "ts": row["fetched_at"],
            }
            continue
        missing.append(symbol)

    if missing:
        active_fetcher = fetcher or _brapi_fetcher
        fetched = active_fetcher(
            missing,
            asset_class,
            settings.brapi_token if token is None else token,
        )
        with db._cursor() as cur:  # type: ignore[attr-defined]
            for symbol in missing:
                quote = fetched.get(symbol) or fetched.get(symbol.upper())
                if not quote or quote.get("price") is None:
                    continue
                price = float(quote["price"])
                currency = str(quote.get("currency") or "BRL")
                fetched_at = now_dt.isoformat(timespec="seconds")
                cur.execute(
                    """
                    INSERT INTO quote_cache (symbol, asset_class, price, currency, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, asset_class) DO UPDATE SET
                        price=excluded.price,
                        currency=excluded.currency,
                        fetched_at=excluded.fetched_at
                    """,
                    (symbol, asset_class, price, currency, fetched_at),
                )
                result[symbol] = {"price": price, "currency": currency, "ts": fetched_at}

    return result


def refresh_prices(
    db: Database,
    *,
    fetcher: QuoteFetcher | None = None,
    ttl_minutes: int | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    from ...web.repositories import portfolio_repo

    assets = portfolio_repo.list_assets(db)
    quoted = updated = skipped = 0
    by_class: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        ticker = asset.get("ticker")
        asset_class = asset.get("asset_class")
        if asset_class in QUOTEABLE_CLASSES and ticker:
            by_class.setdefault(asset_class, []).append(asset)
        else:
            skipped += 1

    for asset_class, class_assets in by_class.items():
        symbols = [asset["ticker"] for asset in class_assets if asset.get("ticker")]
        quotes = get_quotes(
            db,
            symbols,
            asset_class,
            fetcher=fetcher,
            ttl_minutes=ttl_minutes,
            now=now,
        )
        quoted += len(symbols)
        for asset in class_assets:
            quote = quotes.get(asset["ticker"])
            if not quote:
                skipped += 1
                continue
            portfolio_repo.set_price(
                db,
                asset["id"],
                price=float(quote["price"]),
                currency=str(quote.get("currency") or "BRL"),
                price_source="brapi",
                price_updated_at=str(quote.get("ts") or ""),
            )
            updated += 1

    return {"quoted": quoted, "updated": updated, "skipped": skipped}
