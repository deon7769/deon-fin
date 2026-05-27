from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ofxparse import OfxParser

from ..storage import Account, Database, Transaction
from .base import ImportResult


def import_ofx(path: Path | str, db: Database, *, account_id_override: str | None = None) -> ImportResult:
    path = Path(path)
    with open(path, "rb") as f:
        ofx = OfxParser.parse(f)

    if not ofx.accounts:
        raise ValueError(f"OFX sem contas: {path}")

    account = ofx.accounts[0]
    institution = getattr(ofx, "institution", None)
    inst_name = institution.organization if institution else "Unknown"

    acc_id = account_id_override or f"ofx:{inst_name}:{account.account_id}"
    db.upsert_account(
        Account(
            id=acc_id,
            source="ofx",
            institution=inst_name,
            name=account.account_id,
            type=str(account.account_type) if account.account_type else "CHECKING",
        )
    )

    statement = account.statement
    txs: list[Transaction] = []
    for ofx_tx in statement.transactions:
        amount = Decimal(str(ofx_tx.amount))
        txs.append(
            Transaction(
                account_id=acc_id,
                posted_at=ofx_tx.date.date(),
                amount=amount,
                description=(ofx_tx.memo or ofx_tx.payee or "").strip() or "(sem descrição)",
                raw_description=f"{ofx_tx.payee or ''} | {ofx_tx.memo or ''}".strip(" |"),
                source="ofx",
                external_id=str(ofx_tx.id) if ofx_tx.id else None,
                metadata={"type": str(ofx_tx.type)},
            )
        )
    inserted, skipped = db.insert_transactions(txs)
    return ImportResult(account_id=acc_id, inserted=inserted, skipped_duplicates=skipped, total_read=len(txs))
