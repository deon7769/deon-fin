from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ..storage import Account, Database, Transaction
from .base import ImportResult


@dataclass
class CSVMapping:
    date_col: str
    amount_col: str
    description_col: str
    date_format: str = "%Y-%m-%d"
    decimal_separator: str = "."
    thousands_separator: str | None = None
    encoding: str = "utf-8"
    sep: str = ","
    # If the bank uses separate debit/credit columns, set these instead of amount_col:
    debit_col: str | None = None
    credit_col: str | None = None


def import_csv(
    path: Path | str,
    db: Database,
    *,
    mapping: CSVMapping,
    account_id: str,
    institution: str | None = None,
    account_type: str = "CHECKING",
) -> ImportResult:
    path = Path(path)
    df = pd.read_csv(path, sep=mapping.sep, encoding=mapping.encoding, dtype=str).fillna("")

    db.upsert_account(
        Account(
            id=account_id,
            source="csv",
            institution=institution,
            name=path.stem,
            type=account_type,
        )
    )

    txs: list[Transaction] = []
    for _, row in df.iterrows():
        posted = datetime.strptime(row[mapping.date_col].strip(), mapping.date_format).date()
        amount = _parse_amount(row, mapping)
        desc = row[mapping.description_col].strip() or "(sem descrição)"
        txs.append(
            Transaction(
                account_id=account_id,
                posted_at=posted,
                amount=amount,
                description=desc,
                raw_description=desc,
                source="csv",
            )
        )
    inserted, skipped = db.insert_transactions(txs)
    return ImportResult(account_id=account_id, inserted=inserted, skipped_duplicates=skipped, total_read=len(txs))


def _parse_amount(row: "pd.Series[str]", m: CSVMapping) -> Decimal:
    def to_decimal(text: str) -> Decimal:
        text = text.strip()
        if not text:
            return Decimal("0")
        if m.thousands_separator:
            text = text.replace(m.thousands_separator, "")
        if m.decimal_separator != ".":
            text = text.replace(m.decimal_separator, ".")
        return Decimal(text)

    if m.debit_col and m.credit_col:
        debit = to_decimal(row[m.debit_col]) if row[m.debit_col] else Decimal("0")
        credit = to_decimal(row[m.credit_col]) if row[m.credit_col] else Decimal("0")
        return credit - debit
    return to_decimal(row[m.amount_col])
