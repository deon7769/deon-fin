from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ..agent.cards import CREDIT_TYPES
from ..pluggy import PluggyClient
from ..storage import Account, Database, Transaction
from ..web.repositories import accounts_repo
from .base import ImportResult
from .pluggy_investments import sync_pluggy_investments

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
    if hasattr(client, "list_investments"):
        try:
            sync_pluggy_investments(client, db, item_id)
        except Exception:
            log.exception("falha ao sincronizar investimentos do item %s", item_id)
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
    item_id = acc.get("itemId")
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
    if item_id:
        accounts_repo.set_account_item(db, acc_id, str(item_id))
    _upsert_account_balance(db, acc_id, acc)

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


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _last4(*values: Any) -> str | None:
    for value in values:
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if len(digits) >= 4:
            return digits[-4:]
    return None


def _upsert_account_balance(db: Database, account_id: str, acc: dict[str, Any]) -> None:
    item_id = acc.get("itemId")
    item = db.get_pluggy_item(str(item_id)) if item_id else None
    account_type = (acc.get("type") or "").upper()
    is_credit = account_type in CREDIT_TYPES
    credit_data = acc.get("creditData") or {}
    limit = _number(credit_data.get("creditLimit") or credit_data.get("credit_limit"))
    available = _number(
        credit_data.get("availableCreditLimit") or credit_data.get("available_credit_limit")
    )
    used = (
        round(limit - available, 2)
        if limit is not None and available is not None
        else _number(credit_data.get("balance") or credit_data.get("used"))
    )
    accounts_repo.upsert_balance(
        db,
        account_id=account_id,
        balance=None if is_credit else _number(acc.get("balance")),
        credit_limit=limit,
        used=used if is_credit else None,
        available=available if is_credit else None,
        brand=credit_data.get("brand") or credit_data.get("network"),
        last4=_last4(acc.get("number"), credit_data.get("last4"), credit_data.get("number")),
        last_sync_at=(
            item["last_synced_at"]
            if item is not None and item["last_synced_at"]
            else datetime.now().isoformat(timespec="seconds")
        ),
        sync_status=item["status"] if item is not None and item["status"] else "UPDATED",
    )
