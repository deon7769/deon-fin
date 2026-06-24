from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from ...agent.context import (
    account_owner_aliases,
    income_value,
    internal_transfer_credit_ids,
    internal_transfer_row_ids,
    spending_value,
)
from ...storage import Database
from ...storage.reference_month import reference_month
from . import profile_repo, system_totals_repo

_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_WINDOWS = {"3m": 3, "6m": 6, "1a": 12}


def _money(value: float) -> float:
    return round(float(value), 2)


def _valid_year_month(value: str) -> bool:
    if not _YEAR_MONTH_RE.match(value):
        return False
    month = int(value[5:7])
    return 1 <= month <= 12


def _month_add(ym: str, delta: int) -> str:
    year, month = (int(part) for part in ym.split("-"))
    idx = year * 12 + (month - 1) + delta
    next_year, next_month = divmod(idx, 12)
    return f"{next_year:04d}-{next_month + 1:02d}"


def _last_n_months(anchor: str, count: int) -> list[str]:
    count = max(1, int(count))
    return [_month_add(anchor, offset) for offset in range(-(count - 1), 1)]


def resolve_month(db: Database, month: str | None) -> str | None:
    if month is not None:
        return month if _valid_year_month(month) else None

    profile = profile_repo.get_profile(db)
    start_day = int(profile["financial_month_start_day"] or 1)
    return reference_month(date.today(), start_day)


def window_to_months(window: str | None) -> int:
    return _WINDOWS.get((window or "6m").lower(), 6)


def _visible_transactions_for_months(db: Database, months: list[str]) -> list[Any]:
    if not months:
        return []

    placeholders = ",".join("?" for _ in months)
    rows = db._conn.execute(
        f"""
        SELECT t.id,
               t.account_id,
               t.posted_at,
               t.reference_month,
               t.amount,
               t.description,
               t.raw_description,
               t.category,
               t.tag_id,
               a.type AS account_type,
               tg.name AS tag_name,
               tg.color AS tag_color
          FROM transactions t
          LEFT JOIN accounts a ON a.id = t.account_id
          LEFT JOIN tags tg ON tg.id = t.tag_id
          {system_totals_repo.account_transaction_policy_join("t", "tx_total_settings")}
         WHERE t.reference_month IN ({placeholders})
           AND COALESCE(t.hidden, 0) = 0
           AND {system_totals_repo.account_transaction_policy_where("tx_total_settings")}
        """,
        months,
    ).fetchall()
    return system_totals_repo.filter_rows_by_movement_policy(db, rows)


def _accounts_balance(db: Database) -> tuple[float, bool]:
    rows = db._conn.execute(
        """
        SELECT b.balance
          FROM account_balances b
          LEFT JOIN account_total_settings s ON s.account_id = b.account_id
         WHERE COALESCE(s.include_balance, 1) = 1
        """
    ).fetchall()
    if not rows:
        return 0.0, False
    return _money(sum(float(row["balance"] or 0.0) for row in rows)), True


def month_summary(db: Database, month: str) -> dict[str, Any]:
    income = 0.0
    expense = 0.0

    rows = _visible_transactions_for_months(db, [month])
    owner_names = account_owner_aliases(db.list_accounts())
    internal_transfer_income_ids = internal_transfer_credit_ids(rows)
    internal_transfer_ids = internal_transfer_row_ids(rows, owner_names=owner_names)
    for row in rows:
        amount = float(row["amount"])
        income += income_value(
            amount,
            row["account_type"],
            row["category"],
            external_transfer_income=row["id"] not in internal_transfer_income_ids,
        )
        expense += spending_value(
            amount,
            row["account_type"],
            row["category"],
            description=row["description"],
            raw_description=row["raw_description"],
            owner_names=owner_names,
            external_transfer_spending=row["id"] not in internal_transfer_ids,
        )

    accounts_balance, accounts_balance_available = _accounts_balance(db)
    income = _money(income)
    expense = _money(expense)

    return {
        "month": month,
        "result": _money(income - expense),
        "income": income,
        "expense": expense,
        "accounts_balance": accounts_balance,
        "accounts_balance_available": accounts_balance_available,
    }


def history(db: Database, months: int) -> list[dict[str, Any]]:
    anchor = resolve_month(db, None)
    if anchor is None:
        anchor = reference_month(date.today(), 1)
    month_keys = _last_n_months(anchor, months)
    totals = {
        month: {"month": month, "income": 0.0, "expense": 0.0}
        for month in month_keys
    }

    rows = _visible_transactions_for_months(db, month_keys)
    owner_names = account_owner_aliases(db.list_accounts())
    internal_transfer_income_ids = internal_transfer_credit_ids(rows)
    internal_transfer_ids = internal_transfer_row_ids(rows, owner_names=owner_names)
    for row in rows:
        month = row["reference_month"]
        amount = float(row["amount"])
        totals[month]["income"] += income_value(
            amount,
            row["account_type"],
            row["category"],
            external_transfer_income=row["id"] not in internal_transfer_income_ids,
        )
        totals[month]["expense"] += spending_value(
            amount,
            row["account_type"],
            row["category"],
            description=row["description"],
            raw_description=row["raw_description"],
            owner_names=owner_names,
            external_transfer_spending=row["id"] not in internal_transfer_ids,
        )

    return [
        {
            "month": month,
            "income": _money(totals[month]["income"]),
            "expense": _money(totals[month]["expense"]),
        }
        for month in month_keys
    ]


def by_tag(db: Database, month: str, type: Literal["expense", "income"]) -> dict[str, Any]:
    if type not in {"expense", "income"}:
        raise ValueError("type inválido")

    grouped: dict[int | None, dict[str, Any]] = {}
    rows = _visible_transactions_for_months(db, [month])
    owner_names = account_owner_aliases(db.list_accounts())
    internal_transfer_income_ids = internal_transfer_credit_ids(rows)
    internal_transfer_ids = internal_transfer_row_ids(rows, owner_names=owner_names)
    for row in rows:
        amount = float(row["amount"])
        value = (
            spending_value(
                amount,
                row["account_type"],
                row["category"],
                description=row["description"],
                raw_description=row["raw_description"],
                owner_names=owner_names,
                external_transfer_spending=row["id"] not in internal_transfer_ids,
            )
            if type == "expense"
            else income_value(
                amount,
                row["account_type"],
                row["category"],
                external_transfer_income=row["id"] not in internal_transfer_income_ids,
            )
        )
        if value == 0:
            continue

        tag_id = row["tag_id"]
        current = grouped.setdefault(
            tag_id,
            {
                "tag_id": tag_id,
                "tag_name": row["tag_name"] or "Sem Tags",
                "color": row["tag_color"] if tag_id is not None else None,
                "total": 0.0,
            },
        )
        current["total"] += value

    items = [
        {**item, "total": _money(item["total"])}
        for item in grouped.values()
        if _money(item["total"]) > 0
    ]
    items.sort(key=lambda item: (-item["total"], item["tag_name"]))
    total = _money(sum(item["total"] for item in items))

    return {
        "month": month,
        "type": type,
        "total": total,
        "items": items,
    }
