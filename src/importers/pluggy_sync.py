from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from ..pluggy import PluggyClient
from ..storage import Account, Database, Transaction
from .base import ImportResult

log = logging.getLogger(__name__)


def sync_pluggy_item(
    client: PluggyClient,
    db: Database,
    item_id: str,
    *,
    since: date | None = None,
) -> list[ImportResult]:
    """Sincroniza todas as contas/transações de um item (conexão) Pluggy.

    Erros em uma conta não interrompem a sincronização das outras.
    """
    results: list[ImportResult] = []
    accounts = client.list_accounts(item_id)
    for acc in accounts:
        try:
            results.append(_sync_account(client, db, acc, since=since))
        except Exception:
            log.exception("falha ao sincronizar conta %s do item %s", acc.get("id"), item_id)
    return results


def _sync_account(
    client: PluggyClient,
    db: Database,
    acc: dict,
    *,
    since: date | None,
) -> ImportResult:
    acc_id = f"pluggy:{acc['id']}"
    bank_data = acc.get("bankData") or {}
    db.upsert_account(
        Account(
            id=acc_id,
            source="pluggy",
            institution=bank_data.get("transferNumber") or acc.get("name"),
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
    return ImportResult(
        account_id=acc_id, inserted=inserted, skipped_duplicates=skipped, total_read=len(txs)
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value.split("T")[0])
