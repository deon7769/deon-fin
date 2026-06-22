from __future__ import annotations

from src.importers.pluggy_investments import sync_pluggy_investments
from src.storage import Database
from src.web.repositories import portfolio_repo


class FakePluggyInvestments:
    def list_investments(self, item_id, page_size=500):
        assert item_id == "item-btg"
        return [
            {
                "id": "inv-wege",
                "itemId": "item-btg",
                "name": "WEGE3",
                "code": "WEGE3",
                "type": "EQUITY",
                "subtype": "STOCK",
                "currencyCode": "BRL",
                "quantity": 10,
                "value": 42.1,
                "balance": 421.0,
                "amount": 400.0,
                "date": "2026-06-21T03:00:00.000Z",
                "status": "ACTIVE",
            },
            {
                "id": "inv-mxrf",
                "itemId": "item-btg",
                "name": "MXRF11",
                "code": "MXRF11",
                "type": "EQUITY",
                "subtype": "STOCK",
                "currencyCode": "BRL",
                "quantity": 20,
                "value": 10.0,
                "balance": 200.0,
                "amount": 190.0,
                "date": "2026-06-21T03:00:00.000Z",
                "status": "ACTIVE",
            },
            {
                "id": "inv-auvp",
                "itemId": "item-btg",
                "name": "AUVP11",
                "code": "AUVP11",
                "type": "EQUITY",
                "subtype": "STOCK",
                "currencyCode": "BRL",
                "quantity": 3,
                "value": 109.0,
                "balance": 327.0,
                "amount": 327.0,
                "date": "2026-06-21T03:00:00.000Z",
                "status": "ACTIVE",
            },
            {
                "id": "inv-cdb",
                "itemId": "item-btg",
                "name": "CDB - BANCO BTG PACTUAL S.A.",
                "code": "CDB123",
                "type": "FIXED_INCOME",
                "subtype": "CDB",
                "currencyCode": "BRL",
                "quantity": 1,
                "value": 1000.0,
                "balance": 1000.0,
                "amountOriginal": 950.0,
                "date": "2026-06-20T00:00:00.000Z",
                "dueDate": "2028-03-21T03:00:00.000Z",
                "rateType": "CDI",
                "rate": 102.0,
                "status": "ACTIVE",
            },
        ]

    def list_investment_transactions(self, investment_id, page_size=500):
        if investment_id == "inv-wege":
            return [
                {
                    "id": "mov-wege-buy",
                    "type": "BUY",
                    "movementType": "CREDIT",
                    "tradeDate": "2026-06-01T00:00:00.000Z",
                    "date": "2026-06-01T00:00:00.000Z",
                    "quantity": 10,
                    "value": 40.0,
                    "amount": 400.0,
                    "netAmount": 400.0,
                }
            ]
        return []


def test_sync_pluggy_investments_upserts_assets_and_transactions(tmp_db: Database):
    result = sync_pluggy_investments(FakePluggyInvestments(), tmp_db, "item-btg")

    assert result.assets_read == 4
    assert result.assets_upserted == 4
    assert result.transactions_read == 1
    assert result.transactions_upserted == 1

    assets = portfolio_repo.list_assets(tmp_db, include_inactive=True)
    assert [(asset["ticker"], asset["asset_class"]) for asset in assets] == [
        ("WEGE3", "acoes_nac"),
        ("AUVP11", "etf"),
        ("MXRF11", "fii"),
        ("CDB123", "rf"),
    ]
    assert assets[0]["current_value"] == 421.0
    assert assets[0]["unit_price"] == 42.1
    assert assets[0]["source"] == "pluggy"
    assert assets[0]["external_id"] == "inv-wege"

    tx = tmp_db._conn.execute(
        """
        SELECT pt.type, pt.movement_type, pt.quantity, pt.unit_value, pt.amount,
               pa.ticker
          FROM portfolio_transactions pt
          JOIN portfolio_assets pa ON pa.id = pt.asset_id
         WHERE pt.external_id='mov-wege-buy'
        """
    ).fetchone()
    assert dict(tx) == {
        "type": "BUY",
        "movement_type": "CREDIT",
        "quantity": 10.0,
        "unit_value": 40.0,
        "amount": 400.0,
        "ticker": "WEGE3",
    }


def test_sync_pluggy_investments_is_idempotent_and_updates_values(tmp_db: Database):
    fake = FakePluggyInvestments()
    sync_pluggy_investments(fake, tmp_db, "item-btg")
    fake.list_investments = lambda item_id, page_size=500: [
        {
            "id": "inv-wege",
            "itemId": "item-btg",
            "name": "WEGE3",
            "code": "WEGE3",
            "type": "EQUITY",
            "subtype": "STOCK",
            "currencyCode": "BRL",
            "quantity": 11,
            "value": 43.0,
            "balance": 473.0,
            "amount": 440.0,
            "date": "2026-06-22T03:00:00.000Z",
            "status": "ACTIVE",
        }
    ]
    fake.list_investment_transactions = lambda investment_id, page_size=500: []

    result = sync_pluggy_investments(fake, tmp_db, "item-btg")

    assert result.assets_read == 1
    assert result.assets_upserted == 1
    assets = portfolio_repo.list_assets(tmp_db, include_inactive=True)
    assert len(assets) == 4
    wege = next(asset for asset in assets if asset["ticker"] == "WEGE3")
    assert wege["quantity"] == 11.0
    assert wege["current_value"] == 473.0
