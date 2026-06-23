from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from ...agent import maintenance as mnt
from ...agent.context import income_value, internal_transfer_credit_ids, spending_value
from ...config import settings
from ...storage import Database
from ...storage.reference_month import reference_month
from . import buckets_repo, profile_repo, system_totals_repo

IncomeSource = Literal["transactions", "profile", "settings", "family_profile", "none"]

_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _money(value: float) -> float:
    return round(float(value), 2)


def _pct(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return round((float(numerator) / float(denominator)) * 100, 2)


def _valid_year_month(value: str) -> bool:
    if not _YEAR_MONTH_RE.match(value):
        return False
    month = int(value[5:7])
    return 1 <= month <= 12


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _stored_profile_income(db: Database) -> float | None:
    row = db._conn.execute(
        "SELECT monthly_income FROM profile WHERE id=1",
    ).fetchone()
    if row is None:
        return None
    return _positive_float(row["monthly_income"])


def resolve_month(db: Database, month: str | None) -> str | None:
    if month is not None:
        return month if _valid_year_month(month) else None

    profile = profile_repo.get_profile(db)
    start_day = int(profile["financial_month_start_day"] or 1)
    return reference_month(date.today(), start_day)


def _visible_transactions_for_month(db: Database, month: str) -> list[Any]:
    rows = db._conn.execute(
        f"""
        SELECT t.id,
               t.account_id,
               t.posted_at,
               t.amount,
               t.description,
               t.raw_description,
               t.category,
               t.bucket_id,
               a.type AS account_type
          FROM transactions t
          LEFT JOIN accounts a ON a.id = t.account_id
          {system_totals_repo.account_transaction_policy_join("t", "tx_total_settings")}
         WHERE t.reference_month = ?
           AND COALESCE(t.hidden, 0) = 0
           AND {system_totals_repo.account_transaction_policy_where("tx_total_settings")}
         ORDER BY t.posted_at DESC, t.id DESC
        """,
        (month,),
    ).fetchall()
    return system_totals_repo.filter_rows_by_movement_policy(db, rows)


def _income_from_fallbacks(db: Database) -> tuple[float, IncomeSource]:
    profile_income = _stored_profile_income(db)
    if profile_income is not None:
        return _money(profile_income), "profile"

    settings_income = _positive_float(getattr(settings, "monthly_income", None))
    if settings_income is not None:
        return _money(settings_income), "settings"

    family_income = _positive_float(mnt.income_from_profile(mnt.load_family_profile()))
    if family_income is not None:
        return _money(family_income), "family_profile"

    return 0.0, "none"


def _resolve_income(db: Database, rows: list[Any]) -> tuple[float, IncomeSource]:
    total = 0.0
    internal_transfer_income_ids = internal_transfer_credit_ids(rows)
    for row in rows:
        total += income_value(
            float(row["amount"]),
            row["account_type"],
            row["category"],
            external_transfer_income=row["id"] not in internal_transfer_income_ids,
        )
    total = _money(total)
    if total > 0:
        return total, "transactions"
    return _income_from_fallbacks(db)


def _planned_amount(bucket: dict[str, Any], income: float) -> float:
    value = float(bucket["planned_value"] or 0.0)
    if bucket["planned_kind"] == "amount":
        return _money(value)
    return _money(income * value / 100)


def _category_item(bucket: dict[str, Any], income: float, spent: float, tx_count: int) -> dict[str, Any]:
    planned = _planned_amount(bucket, income)
    spent = _money(spent)
    used_pct = _pct(spent, planned)
    exceeded = spent > planned if planned > 0 else spent > 0

    return {
        "id": bucket["id"],
        "key": bucket["key"],
        "name": bucket["name"],
        "color": bucket["color"],
        "planned_kind": bucket["planned_kind"],
        "planned_value": _money(bucket["planned_value"] or 0.0),
        "planned": planned,
        "spent": spent,
        "remaining": _money(planned - spent),
        "used_pct": used_pct,
        "exceeded": exceeded,
        "tx_count": tx_count,
    }


def budget_for_month(db: Database, month: str) -> dict[str, Any]:
    buckets_repo.seed_buckets(db)
    buckets = buckets_repo.list_buckets(db)
    bucket_ids = {int(bucket["id"]) for bucket in buckets}
    aggregates = {int(bucket["id"]): {"spent": 0.0, "tx_count": 0} for bucket in buckets}
    rows = _visible_transactions_for_month(db, month)
    income, income_source = _resolve_income(db, rows)

    spent = 0.0
    uncategorized: list[dict[str, Any]] = []

    for row in rows:
        value = spending_value(
            float(row["amount"]),
            row["account_type"],
            row["category"],
            description=row["description"],
            raw_description=row["raw_description"],
        )
        if value == 0:
            continue

        spent += value
        bucket_id = row["bucket_id"]
        if bucket_id is not None and int(bucket_id) in bucket_ids:
            current = aggregates[int(bucket_id)]
            current["spent"] += value
            if value > 0:
                current["tx_count"] += 1
            continue

        if bucket_id is None and value > 0:
            uncategorized.append(
                {
                    "id": row["id"],
                    "description": row["description"],
                    "date": str(row["posted_at"])[:10],
                    "amount": _money(value),
                }
            )

    spent = _money(spent)
    categories = [
        _category_item(
            bucket,
            income,
            float(aggregates[int(bucket["id"])]["spent"]),
            int(aggregates[int(bucket["id"])]["tx_count"]),
        )
        for bucket in buckets
    ]

    return {
        "month": month,
        "income": income,
        "spent": spent,
        "remaining": _money(income - spent),
        "used_pct": _pct(spent, income),
        "income_source": income_source,
        "categories": categories,
        "uncategorized": uncategorized,
    }
