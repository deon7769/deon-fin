from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from ..pluggy import PluggyClient
from ..storage import Database
from ..web.repositories import portfolio_repo

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PortfolioSyncResult:
    item_id: str
    assets_read: int
    assets_upserted: int
    transactions_read: int
    transactions_upserted: int


def sync_pluggy_investments(
    client: PluggyClient,
    db: Database,
    item_id: str,
) -> PortfolioSyncResult:
    assets_read = assets_upserted = transactions_read = transactions_upserted = 0
    for investment in client.list_investments(item_id):
        assets_read += 1
        try:
            asset_id = portfolio_repo.upsert_pluggy_asset(db, investment)
            assets_upserted += 1
        except Exception:
            log.exception(
                "falha ao sincronizar investimento %s do item %s",
                investment.get("id"),
                item_id,
            )
            continue

        investment_id = investment.get("id")
        if not investment_id:
            continue
        for transaction in _investment_transactions(client, str(investment_id)):
            transactions_read += 1
            try:
                portfolio_repo.upsert_pluggy_transaction(
                    db,
                    asset_id=asset_id,
                    transaction=transaction,
                )
                transactions_upserted += 1
            except Exception:
                log.exception(
                    "falha ao sincronizar movimentação %s do investimento %s",
                    transaction.get("id"),
                    investment_id,
                )

    return PortfolioSyncResult(
        item_id=item_id,
        assets_read=assets_read,
        assets_upserted=assets_upserted,
        transactions_read=transactions_read,
        transactions_upserted=transactions_upserted,
    )


def _investment_transactions(client: PluggyClient, investment_id: str) -> list[dict[str, Any]]:
    try:
        return list(client.list_investment_transactions(investment_id))
    except Exception:
        log.exception("falha ao listar movimentações do investimento %s", investment_id)
        return []
