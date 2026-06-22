from __future__ import annotations

import json
import re
from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from ...agent import maintenance as mnt
from ...agent.cards import CREDIT_TYPES, _EXCLUDE
from ...storage import Database
from ...storage.reference_month import reference_month
from . import profile_repo

_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_PREFIX_INSTALLMENT_RE = re.compile(
    r"\bparc(?:ela)?\.?\s*(\d{1,2})\s*(?:/|\s+de\s+)\s*(\d{1,2})\b",
    re.IGNORECASE,
)
_LOOSE_INSTALLMENT_RE = re.compile(r"\b(\d{1,2})\s*(?:/|\s+de\s+)\s*(\d{1,2})\b", re.IGNORECASE)


def _money(value: float) -> float:
    return round(float(value), 2)


def _valid_year_month(value: str) -> bool:
    if not _YEAR_MONTH_RE.match(value):
        return False
    return 1 <= int(value[5:7]) <= 12


def _today() -> date:
    return date.today()


def _start_day(db: Database) -> int:
    return int(profile_repo.get_profile(db)["financial_month_start_day"] or 1)


def _month_add(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    next_year, next_month = divmod(idx, 12)
    return next_year, next_month + 1


def _clamped_date(year: int, month: int, day: int) -> date:
    return date(year, month, min(max(day, 1), monthrange(year, month)[1]))


def _is_credit_card(account_type: str | None) -> bool:
    return (account_type or "").upper() in CREDIT_TYPES


def _is_purchase(amount: float, category: str | None) -> bool:
    return float(amount) > 0 and (category or "(sem categoria)") not in _EXCLUDE


def _category_label(category: str | None, cat_map: dict[str, str]) -> str:
    name = category or "(sem categoria)"
    return mnt.translate_category(name, cat_map)


def _load_meta(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _extract_last4(meta: dict[str, Any]) -> str | None:
    credit_data = meta.get("creditData") if isinstance(meta.get("creditData"), dict) else {}
    candidates = [
        meta.get("last4"),
        meta.get("lastFourDigits"),
        meta.get("number"),
        credit_data.get("last4"),
        credit_data.get("lastFourDigits"),
        credit_data.get("number"),
    ]
    for candidate in candidates:
        digits = "".join(ch for ch in str(candidate or "") if ch.isdigit())
        if len(digits) >= 4:
            return digits[-4:]
    return None


def _extract_brand(meta: dict[str, Any]) -> str | None:
    credit_data = meta.get("creditData") if isinstance(meta.get("creditData"), dict) else {}
    value = (
        meta.get("brand")
        or meta.get("network")
        or credit_data.get("brand")
        or credit_data.get("network")
    )
    return str(value).strip() if value else None


def _safe_balances(db: Database) -> dict[str, dict[str, Any]]:
    try:
        rows = db._conn.execute(
            "SELECT account_id, credit_limit, available FROM account_balances",
        ).fetchall()
    except Exception:
        return {}
    return {row["account_id"]: dict(row) for row in rows}


def _account_sort_key(row: Any) -> tuple[int, str, str]:
    keys = row.keys() if hasattr(row, "keys") else []
    sort_order = row["sort_order"] if "sort_order" in keys else None
    return (
        int(sort_order) if sort_order is not None else 999_999,
        (row["institution"] or "").lower(),
        (row["name"] or "").lower(),
    )


def list_cards(db: Database) -> list[dict[str, Any]]:
    balances = _safe_balances(db)
    cards: list[dict[str, Any]] = []
    for account in sorted(db.list_accounts(), key=_account_sort_key):
        if not _is_credit_card(account["type"]):
            continue

        meta = _load_meta(account["metadata_json"])
        balance = balances.get(account["id"], {})
        cards.append(
            {
                "id": account["id"],
                "name": account["name"] or "-",
                "brand": _extract_brand(meta),
                "last4": _extract_last4(meta),
                "credit_limit": balance.get("credit_limit"),
                "available": balance.get("available"),
                "currency": account["currency"] or "BRL",
            }
        )
    return cards


def _metadata_installment(meta: dict[str, Any]) -> dict[str, int] | None:
    nested = meta.get("installment") if isinstance(meta.get("installment"), dict) else {}
    credit_data = meta.get("creditData") if isinstance(meta.get("creditData"), dict) else {}
    number = (
        meta.get("installmentNumber")
        or meta.get("installment_number")
        or nested.get("number")
        or nested.get("n")
        or credit_data.get("installmentNumber")
    )
    total = (
        meta.get("totalInstallments")
        or meta.get("total_installments")
        or nested.get("total")
        or nested.get("of")
        or credit_data.get("totalInstallments")
    )
    try:
        n = int(number)
        of = int(total)
    except (TypeError, ValueError):
        return None
    if 1 <= n <= of <= 99:
        return {"n": n, "of": of}
    return None


def _installment_from_match(match: re.Match[str] | None) -> dict[str, int] | None:
    if not match:
        return None
    n, of = int(match.group(1)), int(match.group(2))
    if 1 <= n <= of <= 99:
        return {"n": n, "of": of}
    return None


def _parse_installment(text: str, metadata: dict[str, Any] | None = None) -> dict[str, int] | None:
    structured = _metadata_installment(metadata or {})
    if structured is not None:
        return structured

    prefixed = _installment_from_match(_PREFIX_INSTALLMENT_RE.search(text or ""))
    if prefixed is not None:
        return prefixed

    loose_match = _LOOSE_INSTALLMENT_RE.search(text or "")
    loose = _installment_from_match(loose_match)
    if loose is None:
        return None
    return loose if loose["of"] > 12 else None


def _invoice_dates_and_status(month: str, start_day: int) -> dict[str, Any]:
    year, month_num = (int(part) for part in month.split("-"))
    day = min(max(int(start_day or 1), 1), 28)
    if day <= 1:
        closing = date(year, month_num, monthrange(year, month_num)[1])
    else:
        next_year, next_month = _month_add(year, month_num, 1)
        closing = _clamped_date(next_year, next_month, day) - timedelta(days=1)
    due = closing + timedelta(days=7)
    current_reference = reference_month(_today(), day)
    return {
        "closing_date": closing.isoformat(),
        "due_date": due.isoformat(),
        "paid": month < current_reference,
        "approximate_dates": True,
    }


def resolve_month(db: Database, month: str | None) -> str | None:
    if month is not None:
        return month if _valid_year_month(month) else None
    return reference_month(_today(), _start_day(db))


def _account_by_id(db: Database, account_id: str) -> Any | None:
    for account in db.list_accounts():
        if account["id"] == account_id:
            return account
    return None


def _transaction_rows(db: Database, account_id: str) -> list[Any]:
    return db._conn.execute(
        """
        SELECT t.id,
               t.account_id,
               t.posted_at,
               t.amount,
               t.description,
               t.raw_description,
               t.category,
               t.metadata_json,
               t.bucket_id,
               t.bucket_source,
               t.tag_id,
               t.reference_month,
               COALESCE(t.hidden, 0) AS hidden,
               b.name AS bucket_name,
               b.color AS bucket_color,
               tg.name AS tag_name,
               tg.color AS tag_color
          FROM transactions t
          LEFT JOIN budget_buckets b ON b.id = t.bucket_id
          LEFT JOIN tags tg ON tg.id = t.tag_id
         WHERE t.account_id=?
           AND COALESCE(t.hidden, 0) = 0
         ORDER BY t.posted_at DESC, t.id DESC
        """,
        (account_id,),
    ).fetchall()


def _serialize_item(
    row: Any,
    installment: dict[str, int] | None,
    cat_map: dict[str, str],
) -> dict[str, Any]:
    bucket = None
    if row["bucket_id"] is not None:
        bucket = {
            "id": row["bucket_id"],
            "name": row["bucket_name"],
            "color": row["bucket_color"],
        }

    tag = None
    if row["tag_id"] is not None:
        tag = {
            "id": row["tag_id"],
            "name": row["tag_name"],
            "color": row["tag_color"],
        }

    amount = _money(row["amount"])
    category = row["category"] or "(sem categoria)"
    return {
        "id": row["id"],
        "account_id": row["account_id"],
        "date": str(row["posted_at"])[:10],
        "description": row["description"],
        "amount": amount,
        "signed_value": amount,
        "category": category,
        "category_label": _category_label(category, cat_map),
        "bucket": bucket,
        "bucket_source": row["bucket_source"],
        "tag": tag,
        "installment": installment,
    }


def get_invoice(db: Database, *, account_id: str, month: str) -> dict[str, Any] | None:
    account = _account_by_id(db, account_id)
    if account is None or not _is_credit_card(account["type"]):
        return None

    start_day = _start_day(db)
    cat_map = mnt.load_overrides()["categorias_pt"]
    items: list[dict[str, Any]] = []
    by_category: dict[str, float] = {}
    category_color: dict[str, str | None] = {}

    for row in _transaction_rows(db, account_id):
        row_month = row["reference_month"] or reference_month(row["posted_at"], start_day)
        if row_month != month:
            continue
        amount = float(row["amount"])
        if not _is_purchase(amount, row["category"]):
            continue

        meta = _load_meta(row["metadata_json"])
        item = _serialize_item(
            row,
            _parse_installment(row["raw_description"] or row["description"] or "", meta),
            cat_map,
        )
        items.append(item)
        category = item["category"]
        by_category[category] = by_category.get(category, 0.0) + amount
        if item["bucket"] is not None:
            category_color.setdefault(category, item["bucket"]["color"])

    total = _money(sum(item["amount"] for item in items))
    return {
        "invoice": {
            "account_id": account_id,
            "account_name": account["name"] or "-",
            "reference_month": month,
            "total": total,
            **_invoice_dates_and_status(month, start_day),
            "count": len(items),
        },
        "items": items,
        "by_category": [
            {
                "name": name,
                "label": _category_label(name, cat_map),
                "color": category_color.get(name),
                "total": _money(total),
            }
            for name, total in sorted(by_category.items(), key=lambda item: (-item[1], item[0]))
        ],
    }
