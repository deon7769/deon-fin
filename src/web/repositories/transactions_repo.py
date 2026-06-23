from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from ...agent import maintenance as mnt
from ...agent.context import (
    CREDIT_TYPES,
    INTERNAL_TRANSFER_MATCH_CATEGORIES,
    PIX_TRANSFER_INCOME_CATEGORIES,
    account_owner_aliases,
    income_value,
    internal_transfer_credit_ids,
    is_own_account_transfer_like,
    spending_value,
)
from ...agent.buckets import CATEGORY_BUCKET_MAP, match_key_for
from ...storage import Database, Transaction
from ...storage.reference_month import reference_month
from . import buckets_repo, profile_repo, savings_repo, tags_repo


class TransactionNotFoundError(ValueError):
    pass


class BucketNotFoundError(ValueError):
    pass


class TagNotFoundError(ValueError):
    pass


class SavingsGoalNotFoundError(ValueError):
    pass


class AccountNotFoundError(ValueError):
    pass


_UNSET = object()
_HIDDEN_VALUES = {"exclude", "include", "only"}
_BLOCKED_CLASSIFICATION_CATEGORY_KEYS = {
    key for key, bucket_key in CATEGORY_BUCKET_MAP.items() if bucket_key is None
}
_INTERNAL_TRANSFER_CATEGORY_KEYS = {
    value.strip().lower() for value in INTERNAL_TRANSFER_MATCH_CATEGORIES
}
_PIX_TRANSFER_INCOME_CATEGORY_KEYS = {
    value.strip().lower() for value in PIX_TRANSFER_INCOME_CATEGORIES
}

SELECT_COLS = """
  SELECT t.id, t.account_id, t.posted_at, t.amount, t.description,
         t.raw_description, t.category, t.category_source, t.source,
         t.external_id, t.metadata_json, t.created_at,
         t.bucket_id, t.bucket_source, t.tag_id, t.tag_source, t.reference_month,
         t.savings_goal_id, COALESCE(t.hidden, 0) AS hidden, t.note,
         a.name AS account_name, a.type AS account_type,
         b.name AS bucket_name, b.color AS bucket_color,
         tg.name AS tag_name, tg.color AS tag_color,
         sg.name AS savings_goal_name
    FROM transactions t
    LEFT JOIN accounts a ON a.id = t.account_id
    LEFT JOIN budget_buckets b ON b.id = t.bucket_id
    LEFT JOIN tags tg ON tg.id = t.tag_id
    LEFT JOIN savings_goals sg ON sg.id = t.savings_goal_id
"""


def _parse_posted_at(value: str) -> date:
    return date.fromisoformat(value[:10])


def _is_credit(account_type: str | None) -> bool:
    return (account_type or "").upper() in CREDIT_TYPES


def _is_non_credit(account_type: str | None) -> bool:
    return not _is_credit(account_type)


def _row_date(row: Any) -> date | None:
    try:
        return date.fromisoformat(str(row["posted_at"])[:10])
    except (TypeError, ValueError):
        return None


def _display_type(amount: float, account_type: str | None) -> Literal["income", "expense"]:
    if _is_credit(account_type):
        return "expense" if amount > 0 else "income"
    return "income" if amount > 0 else "expense"


def _signed_value(
    amount: float,
    account_type: str | None,
    category: str | None,
    *,
    external_transfer_income: bool = False,
    description: str | None = None,
    raw_description: str | None = None,
    owner_names: list[str] | tuple[str, ...] | None = None,
) -> float:
    income = income_value(
        amount,
        account_type,
        category,
        external_transfer_income=external_transfer_income,
    )
    expense = spending_value(
        amount,
        account_type,
        category,
        description=description,
        raw_description=raw_description,
        owner_names=owner_names,
    )
    return round(income - expense, 2)


def _display_value(amount: float, account_type: str | None) -> float:
    if _is_credit(account_type):
        return round(-float(amount), 2)
    return round(float(amount), 2)


def _row_signed_value(
    row: Any,
    internal_transfer_income_ids: set[Any],
    owner_names: list[str] | tuple[str, ...] | None = None,
) -> float:
    return _signed_value(
        float(row["amount"]),
        row["account_type"],
        row["category"],
        external_transfer_income=row["id"] not in internal_transfer_income_ids,
        description=row["description"],
        raw_description=row["raw_description"],
        owner_names=owner_names,
    )


def _matches_type_filter(
    row: Any,
    type: Literal["income", "expense"] | None,
    internal_transfer_income_ids: set[Any],
    owner_names: list[str] | tuple[str, ...] | None = None,
) -> bool:
    if type is None:
        return True
    signed = _row_signed_value(row, internal_transfer_income_ids, owner_names)
    return signed > 0 if type == "income" else signed < 0


def _is_actionable_spending_row(
    row: Any,
    owner_names: list[str] | tuple[str, ...] | None = None,
) -> bool:
    return (
        spending_value(
            float(row["amount"] or 0.0),
            row["account_type"],
            row["category"],
            description=row["description"],
            raw_description=row["raw_description"],
            owner_names=owner_names,
        )
        > 0
    )


def _is_bucket_actionable_row(
    row: Any,
    owner_names: list[str] | tuple[str, ...] | None = None,
) -> bool:
    if not _is_actionable_spending_row(row, owner_names):
        return False
    return str(row["category"] or "").strip().lower() not in _BLOCKED_CLASSIFICATION_CATEGORY_KEYS


def _matches_quality_filter(
    row: Any,
    quality: Literal["missing_tag", "missing_bucket"] | None,
    owner_names: list[str] | tuple[str, ...] | None = None,
) -> bool:
    if quality is None:
        return True
    if quality == "missing_tag":
        return row["tag_id"] is None and _is_actionable_spending_row(row, owner_names)
    if quality == "missing_bucket":
        return row["bucket_id"] is None and _is_bucket_actionable_row(row, owner_names)
    raise ValueError("quality inválido")


def _is_internal_transfer_debit_candidate(
    row: Any,
    owner_names: list[str] | tuple[str, ...] | None = None,
) -> bool:
    amount = float(row["amount"] or 0.0)
    if amount >= 0 or not _is_non_credit(row["account_type"]):
        return False
    category_key = str(row["category"] or "").strip().lower()
    if category_key in _INTERNAL_TRANSFER_CATEGORY_KEYS:
        return True
    return is_own_account_transfer_like(
        amount,
        row["account_type"],
        row["category"],
        description=row["description"],
        raw_description=row["raw_description"],
        owner_names=owner_names,
    )


def _internal_transfer_row_ids(
    rows: list[Any],
    owner_names: list[str] | tuple[str, ...] | None = None,
    *,
    day_window: int = 2,
) -> set[Any]:
    credits: list[dict[str, Any]] = []
    debits: list[dict[str, Any]] = []
    own_transfer_debits: set[Any] = set()

    for row in rows:
        row_id = row["id"]
        account_id = row["account_id"]
        posted = _row_date(row)
        if row_id is None or account_id is None or posted is None:
            continue
        amount = float(row["amount"] or 0.0)
        if not _is_non_credit(row["account_type"]):
            continue

        category_key = str(row["category"] or "").strip().lower()
        payload = {
            "id": row_id,
            "account_id": str(account_id),
            "posted": posted,
            "amount_abs": round(abs(amount), 2),
        }
        if amount > 0 and category_key in _PIX_TRANSFER_INCOME_CATEGORY_KEYS:
            credits.append(payload)
            continue
        if amount < 0 and category_key in _INTERNAL_TRANSFER_CATEGORY_KEYS:
            debits.append(payload)
            continue
        if _is_internal_transfer_debit_candidate(row, owner_names):
            own_transfer_debits.add(row_id)

    matched: set[Any] = set(own_transfer_debits)
    for credit in credits:
        for debit in debits:
            if credit["account_id"] == debit["account_id"]:
                continue
            if abs(credit["amount_abs"] - debit["amount_abs"]) > 0.01:
                continue
            if abs((credit["posted"] - debit["posted"]).days) > day_window:
                continue
            matched.add(credit["id"])
            matched.add(debit["id"])
            break
    return matched


def _matches_internal_transfer_filter(
    row: Any,
    internal_transfer: Literal["only", "exclude"] | None,
    internal_transfer_ids: set[Any],
) -> bool:
    if internal_transfer is None:
        return True
    is_internal = row["id"] in internal_transfer_ids
    if internal_transfer == "only":
        return is_internal
    if internal_transfer == "exclude":
        return not is_internal
    raise ValueError("internal_transfer inválido")


def _category_label(category: str | None, cat_map: dict[str, str] | None = None) -> str:
    name = category or "(sem categoria)"
    mapping = cat_map if cat_map is not None else mnt.load_overrides()["categorias_pt"]
    return mnt.translate_category(name, mapping)


def _serialize_item(
    row: Any,
    *,
    external_transfer_income: bool = False,
    cat_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    amount = float(row["amount"])
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

    return {
        "id": row["id"],
        "account_id": row["account_id"],
        "posted_at": row["posted_at"],
        "amount": amount,
        "description": row["description"],
        "raw_description": row["raw_description"],
        "category": row["category"],
        "category_label": _category_label(row["category"], cat_map),
        "category_source": row["category_source"],
        "source": row["source"],
        "external_id": row["external_id"],
        "bucket_id": row["bucket_id"],
        "bucket_source": row["bucket_source"],
        "bucket": bucket,
        "tag_id": row["tag_id"],
        "tag_source": row["tag_source"],
        "tag": tag,
        "savings_goal_id": row["savings_goal_id"],
        "savings_goal_name": row["savings_goal_name"],
        "reference_month": row["reference_month"],
        "hidden": bool(row["hidden"]),
        "note": row["note"],
        "account_name": row["account_name"],
        "account_type": row["account_type"],
        "signed_value": _signed_value(
            amount,
            row["account_type"],
            row["category"],
            external_transfer_income=external_transfer_income,
        ),
        "display_value": _display_value(amount, row["account_type"]),
        "type": _display_type(amount, row["account_type"]),
    }


def _build_null_aware_filter(
    column: str,
    values: list[int | None] | None,
    params: list[Any],
) -> str | None:
    if not values:
        return None

    ids = [value for value in values if value is not None]
    parts: list[str] = []
    if ids:
        parts.append(f"{column} IN ({','.join('?' for _ in ids)})")
        params.extend(ids)
    if any(value is None for value in values):
        parts.append(f"{column} IS NULL")
    if not parts:
        return None
    return "(" + " OR ".join(parts) + ")"


def _build_where(
    *,
    month: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    type: Literal["income", "expense"] | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    account_id: str | None = None,
    account_ids: list[str] | None = None,
    bucket_ids: list[int | None] | None = None,
    tag_ids: list[int | None] | None = None,
    savings_goal_ids: list[int | None] | None = None,
    quality: Literal["missing_tag", "missing_bucket"] | None = None,
    internal_transfer: Literal["only", "exclude"] | None = None,
    hidden: Literal["exclude", "include", "only"] = "exclude",
) -> tuple[str, list[Any]]:
    clauses = ["1=1"]
    params: list[Any] = []

    if month:
        clauses.append("t.reference_month = ?")
        params.append(month)
    if date_from:
        clauses.append("t.posted_at >= ?")
        params.append(date_from.isoformat())
    if date_to:
        clauses.append("t.posted_at <= ?")
        params.append(date_to.isoformat())

    normalized_q = (q or "").strip().lower()
    if normalized_q:
        clauses.append(
            "(LOWER(COALESCE(t.description, '')) LIKE ? "
            "OR LOWER(COALESCE(t.raw_description, '')) LIKE ?)"
        )
        like = f"%{normalized_q}%"
        params.extend([like, like])

    credit_sql = "UPPER(COALESCE(a.type, '')) IN ('CREDIT', 'CREDIT_CARD')"
    if type == "income":
        clauses.append(f"(({credit_sql} AND t.amount < 0) OR (NOT {credit_sql} AND t.amount > 0))")
    elif type == "expense":
        clauses.append(f"(({credit_sql} AND t.amount > 0) OR (NOT {credit_sql} AND t.amount < 0))")

    if amount_min is not None:
        clauses.append("ABS(t.amount) >= ?")
        params.append(amount_min)
    if amount_max is not None:
        clauses.append("ABS(t.amount) <= ?")
        params.append(amount_max)
    if account_id:
        clauses.append("t.account_id = ?")
        params.append(account_id)
    if account_ids:
        clauses.append(f"t.account_id IN ({','.join('?' for _ in account_ids)})")
        params.extend(account_ids)

    bucket_filter = _build_null_aware_filter("t.bucket_id", bucket_ids, params)
    if bucket_filter:
        clauses.append(bucket_filter)

    tag_filter = _build_null_aware_filter("t.tag_id", tag_ids, params)
    if tag_filter:
        clauses.append(tag_filter)

    savings_goal_filter = _build_null_aware_filter("t.savings_goal_id", savings_goal_ids, params)
    if savings_goal_filter:
        clauses.append(savings_goal_filter)

    if hidden == "exclude":
        clauses.append("COALESCE(t.hidden, 0) = 0")
    elif hidden == "only":
        clauses.append("COALESCE(t.hidden, 0) = 1")
    elif hidden != "include":
        raise ValueError("hidden inválido")

    return " AND ".join(clauses), params


def _compute_summary(
    db: Database,
    *,
    month: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    type: Literal["income", "expense"] | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    account_id: str | None = None,
    account_ids: list[str] | None = None,
    bucket_ids: list[int | None] | None = None,
    tag_ids: list[int | None] | None = None,
    savings_goal_ids: list[int | None] | None = None,
    quality: Literal["missing_tag", "missing_bucket"] | None = None,
    internal_transfer: Literal["only", "exclude"] | None = None,
    hidden: Literal["exclude", "include", "only"] = "exclude",
) -> dict[str, float]:
    where, params = _build_where(
        month=month,
        date_from=date_from,
        date_to=date_to,
        q=q,
        type=None,
        amount_min=amount_min,
        amount_max=amount_max,
        account_id=account_id,
        account_ids=account_ids,
        bucket_ids=bucket_ids,
        tag_ids=tag_ids,
        savings_goal_ids=savings_goal_ids,
        quality=quality,
        internal_transfer=internal_transfer,
        hidden=hidden,
    )
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
               t.tag_id,
               a.type AS account_type
          FROM transactions t
          LEFT JOIN accounts a ON a.id = t.account_id
         WHERE {where}
        """,
        params,
    ).fetchall()

    income = 0.0
    expense = 0.0
    internal_transfer_income_ids = internal_transfer_credit_ids(rows)
    owner_names = account_owner_aliases(db.list_accounts())
    internal_transfer_ids = _internal_transfer_row_ids(rows, owner_names)
    for row in rows:
        if not _matches_type_filter(row, type, internal_transfer_income_ids, owner_names):
            continue
        if not _matches_quality_filter(row, quality, owner_names):
            continue
        if not _matches_internal_transfer_filter(row, internal_transfer, internal_transfer_ids):
            continue
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
        )

    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "balance": round(income - expense, 2),
    }


def get_transaction(db: Database, transaction_id: str) -> dict[str, Any] | None:
    row = db._conn.execute(
        f"{SELECT_COLS} WHERE t.id = ?",
        (transaction_id,),
    ).fetchone()
    return _serialize_item(row) if row else None


def list_transactions(
    db: Database,
    *,
    month: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    type: Literal["income", "expense"] | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    account_id: str | None = None,
    account_ids: list[str] | None = None,
    bucket_ids: list[int | None] | None = None,
    tag_ids: list[int | None] | None = None,
    savings_goal_ids: list[int | None] | None = None,
    quality: Literal["missing_tag", "missing_bucket"] | None = None,
    internal_transfer: Literal["only", "exclude"] | None = None,
    hidden: Literal["exclude", "include", "only"] = "exclude",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    offset = (page - 1) * page_size

    filters = {
        "month": month,
        "date_from": date_from,
        "date_to": date_to,
        "q": q,
        "type": type,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "account_id": account_id,
        "account_ids": account_ids,
        "bucket_ids": bucket_ids,
        "tag_ids": tag_ids,
        "savings_goal_ids": savings_goal_ids,
        "quality": quality,
        "internal_transfer": internal_transfer,
        "hidden": hidden,
    }
    sql_filters = {**filters, "type": None}
    where, params = _build_where(**sql_filters)
    all_rows = db._conn.execute(
        f"{SELECT_COLS} WHERE {where} ORDER BY t.posted_at DESC, t.id DESC",
        params,
    ).fetchall()
    internal_transfer_income_ids = internal_transfer_credit_ids(all_rows)
    owner_names = account_owner_aliases(db.list_accounts())
    internal_transfer_ids = _internal_transfer_row_ids(all_rows, owner_names)
    filtered_rows = [
        row
        for row in all_rows
        if _matches_type_filter(row, type, internal_transfer_income_ids, owner_names)
        and _matches_quality_filter(row, quality, owner_names)
        and _matches_internal_transfer_filter(row, internal_transfer, internal_transfer_ids)
    ]
    rows = filtered_rows[offset : offset + page_size]
    cat_map = mnt.load_overrides()["categorias_pt"]

    return {
        "items": [
            _serialize_item(
                row,
                external_transfer_income=row["id"] not in internal_transfer_income_ids,
                cat_map=cat_map,
            )
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": len(filtered_rows),
        "summary": _compute_summary(db, **filters),
    }


def _account_row(db: Database, account_id: str) -> Any | None:
    return db._conn.execute(
        "SELECT id, type FROM accounts WHERE id=?",
        (account_id,),
    ).fetchone()


def _stored_manual_amount(amount: float, tx_type: Literal["income", "expense"], account_type: str | None) -> Decimal:
    value = Decimal(str(abs(float(amount)))).quantize(Decimal("0.01"))
    if tx_type == "expense":
        return value if _is_credit(account_type) else -value
    return -value if _is_credit(account_type) else value


def create_manual_transaction(
    db: Database,
    *,
    account_id: str,
    posted_at: date,
    amount: float,
    type: Literal["income", "expense"],
    description: str,
    bucket_id: int | None = None,
    tag_id: int | None = None,
    note: str | None = None,
    reference_month_override: str | None = None,
) -> dict[str, Any]:
    account = _account_row(db, account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    if bucket_id is not None and not buckets_repo.bucket_exists(db, bucket_id):
        raise BucketNotFoundError(f"bucket_id inválido: {bucket_id}")
    if tag_id is not None and not tags_repo.tag_exists(db, tag_id):
        raise TagNotFoundError(f"tag_id inválido: {tag_id}")

    tx = Transaction(
        account_id=account_id,
        posted_at=posted_at,
        amount=_stored_manual_amount(amount, type, account["type"]),
        description=description.strip(),
        raw_description=description.strip(),
        source="manual",
    )
    inserted, skipped = db.insert_transactions([tx])
    duplicate = inserted == 0 and skipped == 1

    if not duplicate:
        start_day = int(profile_repo.get_profile(db)["financial_month_start_day"] or 1)
        ref_month = reference_month_override or reference_month(posted_at, start_day)
        with db._cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                """
                UPDATE transactions
                   SET reference_month=?,
                       bucket_id=?,
                       bucket_source=?,
                       tag_id=?,
                       tag_source=?,
                       note=?
                 WHERE id=?
                """,
                (
                    ref_month,
                    bucket_id,
                    "manual" if bucket_id is not None else None,
                    tag_id,
                    "manual" if tag_id is not None else None,
                    note,
                    tx.id,
                ),
            )

    item = get_transaction(db, tx.id)
    if item is None:
        raise TransactionNotFoundError(tx.id)
    return {"duplicate": duplicate, "transaction": item}


def update_transaction(
    db: Database,
    transaction_id: str,
    *,
    bucket_id: int | None | object = _UNSET,
    tag_id: int | None | object = _UNSET,
    savings_goal_id: int | None | object = _UNSET,
    hidden: bool | object = _UNSET,
    note: str | None | object = _UNSET,
    reference_month: str | object = _UNSET,
) -> dict[str, Any]:
    if get_transaction(db, transaction_id) is None:
        raise TransactionNotFoundError(transaction_id)

    if bucket_id is not _UNSET and bucket_id is not None and not buckets_repo.bucket_exists(db, int(bucket_id)):
        raise BucketNotFoundError(f"bucket_id inválido: {bucket_id}")
    if tag_id is not _UNSET and tag_id is not None and not tags_repo.tag_exists(db, int(tag_id)):
        raise TagNotFoundError(f"tag_id inválido: {tag_id}")
    if (
        savings_goal_id is not _UNSET
        and savings_goal_id is not None
        and savings_repo.get_goal(db, int(savings_goal_id)) is None
    ):
        raise SavingsGoalNotFoundError(f"savings_goal_id inválido: {savings_goal_id}")

    assignments: list[str] = []
    params: list[Any] = []

    if bucket_id is not _UNSET:
        assignments.extend(["bucket_id=?", "bucket_source='manual'"])
        params.append(bucket_id)
    if tag_id is not _UNSET:
        assignments.extend(["tag_id=?", "tag_source='manual'"])
        params.append(tag_id)
    if savings_goal_id is not _UNSET:
        assignments.append("savings_goal_id=?")
        params.append(savings_goal_id)
    if hidden is not _UNSET:
        assignments.append("hidden=?")
        params.append(1 if hidden else 0)
    if note is not _UNSET:
        assignments.append("note=?")
        params.append(note)
    if reference_month is not _UNSET:
        assignments.append("reference_month=?")
        params.append(reference_month)

    if assignments:
        with db._cursor() as cur:  # type: ignore[attr-defined]
            cur.execute(
                f"UPDATE transactions SET {', '.join(assignments)} WHERE id=?",
                (*params, transaction_id),
            )

    if bucket_id is not _UNSET:
        set_bucket(
            db,
            transaction_id,
            bucket_id=bucket_id if bucket_id is None else int(bucket_id),
            apply_to_similar=False,
        )

    item = get_transaction(db, transaction_id)
    if item is None:
        raise TransactionNotFoundError(transaction_id)
    return {"updated": 1, **item}


def delete_transaction(db: Database, transaction_id: str) -> str:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
        if cur.rowcount == 0:
            raise TransactionNotFoundError(transaction_id)
    return transaction_id


def bulk_update_transactions(
    db: Database,
    transaction_ids: list[str],
    **patch: Any,
) -> dict[str, Any]:
    updated = 0
    not_found: list[str] = []
    for transaction_id in transaction_ids:
        try:
            update_transaction(db, transaction_id, **patch)
            updated += 1
        except TransactionNotFoundError:
            not_found.append(transaction_id)
    return {"updated": updated, "not_found": not_found}


def recompute_reference_months(db: Database, start_day: int) -> int:
    rows = db._conn.execute("SELECT id, posted_at FROM transactions").fetchall()
    for row in rows:
        db._conn.execute(
            "UPDATE transactions SET reference_month=? WHERE id=?",
            (reference_month(_parse_posted_at(row["posted_at"]), start_day), row["id"]),
        )
    db._conn.commit()
    return len(rows)


def fill_missing_reference_months(db: Database, start_day: int) -> int:
    rows = db._conn.execute(
        """
        SELECT id, posted_at
          FROM transactions
         WHERE reference_month IS NULL
        """
    ).fetchall()
    for row in rows:
        db._conn.execute(
            "UPDATE transactions SET reference_month=? WHERE id=?",
            (reference_month(_parse_posted_at(row["posted_at"]), start_day), row["id"]),
        )
    db._conn.commit()
    return len(rows)


def set_bucket(
    db: Database,
    transaction_id: str,
    *,
    bucket_id: int | None,
    apply_to_similar: bool = False,
) -> dict[str, Any]:
    if bucket_id is not None and not buckets_repo.bucket_exists(db, bucket_id):
        raise BucketNotFoundError(f"bucket_id inválido: {bucket_id}")

    rule_upserted = False
    rule_deleted = False
    similar_ids: list[str] = []

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            SELECT id, amount, raw_description, description
              FROM transactions
             WHERE id=?
            """,
            (transaction_id,),
        )
        target = cur.fetchone()
        if target is None:
            raise TransactionNotFoundError(transaction_id)

        match_key = match_key_for(
            target["raw_description"] or target["description"],
            float(target["amount"]),
        )

        cur.execute(
            """
            UPDATE transactions
               SET bucket_id=?, bucket_source='manual'
             WHERE id=?
            """,
            (bucket_id, transaction_id),
        )

        if apply_to_similar and match_key:
            if bucket_id is None:
                cur.execute("DELETE FROM bucket_rules WHERE match_key=?", (match_key,))
                rule_deleted = cur.rowcount > 0
            else:
                cur.execute(
                    """
                    INSERT INTO bucket_rules (match_key, bucket_id)
                    VALUES (?, ?)
                    ON CONFLICT(match_key) DO UPDATE SET bucket_id=excluded.bucket_id
                    """,
                    (match_key, bucket_id),
                )
                rule_upserted = True

            if bucket_id is not None:
                cur.execute(
                    """
                    SELECT id, amount, raw_description, description
                      FROM transactions
                     WHERE id != ?
                       AND (bucket_source IS NULL OR bucket_source != 'manual')
                    """,
                    (transaction_id,),
                )
                candidates = cur.fetchall()
                for row in candidates:
                    candidate_key = match_key_for(
                        row["raw_description"] or row["description"],
                        float(row["amount"]),
                    )
                    if candidate_key != match_key:
                        continue

                    cur.execute(
                        """
                        UPDATE transactions
                           SET bucket_id=?, bucket_source='rule'
                         WHERE id=?
                        """,
                        (bucket_id, row["id"]),
                    )
                    similar_ids.append(row["id"])

    return {
        "updated": 1,
        "bucket_id": bucket_id,
        "bucket_source": "manual",
        "match_key": match_key,
        "rule_upserted": rule_upserted,
        "rule_deleted": rule_deleted,
        "similar_affected": len(similar_ids),
        "similar_ids": similar_ids,
    }


def set_tag(
    db: Database,
    transaction_id: str,
    *,
    tag_id: int | None,
    apply_to_similar: bool = False,
) -> dict[str, Any]:
    if tag_id is not None and not tags_repo.tag_exists(db, tag_id):
        raise TagNotFoundError(f"tag_id inválido: {tag_id}")

    rule_upserted = False
    rule_deleted = False
    similar_ids: list[str] = []

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            SELECT id, amount, raw_description, description
              FROM transactions
             WHERE id=?
            """,
            (transaction_id,),
        )
        target = cur.fetchone()
        if target is None:
            raise TransactionNotFoundError(transaction_id)

        match_key = match_key_for(
            target["raw_description"] or target["description"],
            float(target["amount"]),
        )

        cur.execute(
            "UPDATE transactions SET tag_id=?, tag_source='manual' WHERE id=?",
            (tag_id, transaction_id),
        )

        if apply_to_similar and match_key:
            if tag_id is None:
                cur.execute("DELETE FROM tag_rules WHERE match_key=?", (match_key,))
                rule_deleted = cur.rowcount > 0
            else:
                cur.execute(
                    """
                    INSERT INTO tag_rules (match_key, tag_id)
                    VALUES (?, ?)
                    ON CONFLICT(match_key) DO UPDATE SET
                        tag_id=excluded.tag_id,
                        updated_at=datetime('now')
                    """,
                    (match_key, tag_id),
                )
                rule_upserted = True

            if tag_id is not None:
                cur.execute(
                    """
                    SELECT id, amount, raw_description, description
                      FROM transactions
                     WHERE id != ?
                       AND (tag_source IS NULL OR tag_source != 'manual')
                    """,
                    (transaction_id,),
                )
                candidates = cur.fetchall()
                for row in candidates:
                    candidate_key = match_key_for(
                        row["raw_description"] or row["description"],
                        float(row["amount"]),
                    )
                    if candidate_key != match_key:
                        continue

                    cur.execute(
                        """
                        UPDATE transactions
                           SET tag_id=?, tag_source='rule'
                         WHERE id=?
                        """,
                        (tag_id, row["id"]),
                    )
                    similar_ids.append(row["id"])

    return {
        "updated": 1,
        "tag_id": tag_id,
        "tag_source": "manual",
        "match_key": match_key,
        "rule_upserted": rule_upserted,
        "rule_deleted": rule_deleted,
        "similar_affected": len(similar_ids),
        "similar_ids": similar_ids,
    }
