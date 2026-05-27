from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..pluggy import PluggyClient
from ..storage import Account, Database, Transaction
from .base import ImportResult


def sync_pluggy_item(
    client: PluggyClient,
    db: Database,
    item_id: str,
    *,
    since: date | None = None,
) -> list[ImportResult]:
    """Sincroniza todas as contas/transações de um item (conexão) Pluggy."""
    results: list[ImportResult] = []
    accounts = client.list_accounts(item_id)
    for acc in accounts:
        acc_id = f"pluggy:{acc['id']}"
        db.upsert_account(
            Account(
                id=acc_id,
                source="pluggy",
                institution=acc.get("bankData", {}).get("transferNumber") or acc.get("name"),
                name=acc.get("name"),
                type=acc.get("type"),
                currency=acc.get("currencyCode", "BRL"),
                metadata={k: v for k, v in acc.items() if k not in {"id", "name", "type"}},
            )
        )

        txs: list[Transaction] = []
        for tx in client.list_transactions(
            acc["id"],
            from_date=since.isoformat() if since else None,
        ):
            txs.append(
                Transaction(
                    account_id=acc_id,
                    posted_at=_parse_date(tx["date"]),
                    amount=Decimal(str(tx["amount"])),
                    description=tx.get("description") or "(sem descrição)",
                    raw_description=tx.get("descriptionRaw") or tx.get("description"),
                    source="pluggy",
                    external_id=tx["id"],
                    category=tx.get("category"),
                    category_source="pluggy" if tx.get("category") else None,
                    metadata={"type": tx.get("type"), "status": tx.get("status")},
                )
            )
        inserted, skipped = db.insert_transactions(txs)
        results.append(
            ImportResult(account_id=acc_id, inserted=inserted, skipped_duplicates=skipped, total_read=len(txs))
        )
    return results


def _parse_date(value: str) -> date:
    return date.fromisoformat(value.split("T")[0])
