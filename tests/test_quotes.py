from __future__ import annotations

from datetime import datetime, timedelta

from src.agent.portfolio import quotes
from src.web.repositories import portfolio_repo


def test_get_quotes_uses_cache_until_ttl_expires(tmp_db):
    calls: list[list[str]] = []
    now = datetime(2026, 6, 22, 10, 0, 0)

    def fetcher(symbols, asset_class, token=None):
        calls.append(list(symbols))
        return {
            "WEGE3": {
                "price": 42.5,
                "currency": "BRL",
                "ts": now.isoformat(timespec="seconds"),
            }
        }

    first = quotes.get_quotes(
        tmp_db,
        ["wege3"],
        "acoes_nac",
        fetcher=fetcher,
        ttl_minutes=15,
        now=now,
    )
    second = quotes.get_quotes(
        tmp_db,
        ["WEGE3"],
        "acoes_nac",
        fetcher=fetcher,
        ttl_minutes=15,
        now=now + timedelta(minutes=10),
    )

    assert calls == [["WEGE3"]]
    assert first == second == {
        "WEGE3": {
            "price": 42.5,
            "currency": "BRL",
            "ts": "2026-06-22T10:00:00",
        }
    }

    quotes.get_quotes(
        tmp_db,
        ["WEGE3"],
        "acoes_nac",
        fetcher=fetcher,
        ttl_minutes=15,
        now=now + timedelta(minutes=16),
    )

    assert calls == [["WEGE3"], ["WEGE3"]]


def test_refresh_prices_updates_quoted_assets_and_preserves_fixed_income(tmp_db):
    portfolio_repo.upsert_pluggy_asset(
        tmp_db,
        {
            "id": "inv-wege",
            "name": "WEGE3",
            "code": "WEGE3",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 10,
            "value": 40,
            "balance": 400,
            "status": "ACTIVE",
            "date": "2026-06-21T03:00:00.000Z",
        },
    )
    portfolio_repo.create_manual_asset(
        tmp_db,
        asset_class="rf",
        name="Tesouro Selic",
        manual_value=1200.0,
    )

    def fetcher(symbols, asset_class, token=None):
        assert symbols == ["WEGE3"]
        return {
            "WEGE3": {
                "price": 45.25,
                "currency": "BRL",
                "ts": "2026-06-22T10:00:00",
            }
        }

    summary = quotes.refresh_prices(
        tmp_db,
        fetcher=fetcher,
        ttl_minutes=15,
        now=datetime(2026, 6, 22, 10, 0, 0),
    )

    assert summary == {"quoted": 1, "updated": 1, "skipped": 1}
    assets = portfolio_repo.list_assets(tmp_db)
    wege = next(asset for asset in assets if asset["ticker"] == "WEGE3")
    rf = next(asset for asset in assets if asset["asset_class"] == "rf")
    assert wege["unit_price"] == 45.25
    assert wege["current_value"] == 452.5
    assert wege["price_source"] == "brapi"
    assert wege["price_updated_at"] == "2026-06-22T10:00:00"
    assert rf["current_value"] == 1200.0
    assert rf["price_source"] == "manual"
