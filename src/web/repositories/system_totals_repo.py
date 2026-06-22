from __future__ import annotations

from typing import Any, Iterable

from ...agent.context import (
    CARD_PAYMENT_CATEGORIES,
    FINANCIAL_COST_CATEGORIES,
    INTERNAL_TRANSFER_MATCH_CATEGORIES,
    INVESTMENT_CATEGORIES,
    PIX_TRANSFER_INCOME_CATEGORIES,
    income_value,
    internal_transfer_credit_ids,
    spending_value,
)
from ...storage import Database

MOVEMENT_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"key": "income", "label": "Receitas", "sort_order": 10},
    {"key": "expense", "label": "Despesas", "sort_order": 20},
    {"key": "refund", "label": "Estornos", "sort_order": 30},
    {"key": "internal_transfer", "label": "Transferencias internas", "sort_order": 40},
    {"key": "card_payment", "label": "Pagamento de fatura", "sort_order": 50},
    {"key": "investment", "label": "Investimentos e aportes", "sort_order": 60},
    {"key": "financial_cost", "label": "Juros e tarifas", "sort_order": 70},
    {"key": "other_non_spending", "label": "Outros sem consumo", "sort_order": 80},
)

_KNOWN_MOVEMENTS = {item["key"] for item in MOVEMENT_DEFINITIONS}
_CARD_PAYMENT = {item.lower() for item in CARD_PAYMENT_CATEGORIES}
_FINANCIAL_COST = {item.lower() for item in FINANCIAL_COST_CATEGORIES}
_INTERNAL_TRANSFER = {item.lower() for item in INTERNAL_TRANSFER_MATCH_CATEGORIES}
_INVESTMENT = {item.lower() for item in INVESTMENT_CATEGORIES}
_PIX_TRANSFER_INCOME = {item.lower() for item in PIX_TRANSFER_INCOME_CATEGORIES}


def _as_bool(value: Any) -> bool:
    return bool(int(value or 0))


def _as_int_bool(value: Any) -> int:
    return 1 if bool(value) else 0


def ensure_movement_settings(db: Database, *, commit: bool = True) -> None:
    for item in MOVEMENT_DEFINITIONS:
        db._conn.execute(
            """
            INSERT OR IGNORE INTO movement_total_settings (
                movement_type, label, include_in_totals, sort_order
            )
            VALUES (?, ?, 1, ?)
            """,
            (item["key"], item["label"], item["sort_order"]),
        )
    if commit:
        db._conn.commit()


def list_settings(db: Database) -> dict[str, list[dict[str, Any]]]:
    ensure_movement_settings(db)
    accounts = [
        {
            "id": row["id"],
            "name": row["name"] or row["institution"] or row["id"],
            "institution": row["institution"],
            "type": row["type"],
            "source": row["source"],
            "include_balance": _as_bool(row["include_balance"]),
            "include_transactions": _as_bool(row["include_transactions"]),
        }
        for row in db._conn.execute(
            """
            SELECT a.id,
                   a.name,
                   a.institution,
                   a.type,
                   a.source,
                   COALESCE(s.include_balance, 1) AS include_balance,
                   COALESCE(s.include_transactions, 1) AS include_transactions
              FROM accounts a
              LEFT JOIN account_total_settings s ON s.account_id = a.id
             ORDER BY COALESCE(a.sort_order, 999999), COALESCE(a.institution, ''), COALESCE(a.name, ''), a.id
            """
        ).fetchall()
    ]
    movements = [
        {
            "key": row["movement_type"],
            "label": row["label"],
            "include_in_totals": _as_bool(row["include_in_totals"]),
            "sort_order": int(row["sort_order"] or 0),
        }
        for row in db._conn.execute(
            """
            SELECT movement_type, label, include_in_totals, sort_order
              FROM movement_total_settings
             ORDER BY sort_order, movement_type
            """
        ).fetchall()
    ]
    return {"accounts": accounts, "movements": movements}


def update_account_settings(
    db: Database,
    rows: Iterable[dict[str, Any]],
    *,
    commit: bool = True,
) -> None:
    for row in rows:
        account_id = str(row.get("account_id") or "").strip()
        if not account_id:
            raise ValueError("account_id is required")
        exists = db._conn.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone()
        if exists is None:
            raise ValueError(f"unknown account: {account_id}")
        db._conn.execute(
            """
            INSERT INTO account_total_settings (
                account_id, include_balance, include_transactions, updated_at
            )
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(account_id) DO UPDATE SET
                include_balance=excluded.include_balance,
                include_transactions=excluded.include_transactions,
                updated_at=datetime('now')
            """,
            (
                account_id,
                _as_int_bool(row.get("include_balance", True)),
                _as_int_bool(row.get("include_transactions", True)),
            ),
        )
    if commit:
        db._conn.commit()


def update_movement_settings(
    db: Database,
    rows: Iterable[dict[str, Any]],
    *,
    commit: bool = True,
) -> None:
    ensure_movement_settings(db, commit=False)
    for row in rows:
        movement_type = str(row.get("movement_type") or "").strip()
        if movement_type not in _KNOWN_MOVEMENTS:
            raise ValueError(f"unknown movement type: {movement_type}")
        db._conn.execute(
            """
            UPDATE movement_total_settings
               SET include_in_totals=?,
                   updated_at=datetime('now')
             WHERE movement_type=?
            """,
            (_as_int_bool(row.get("include_in_totals", True)), movement_type),
        )
    if commit:
        db._conn.commit()


def update_settings(
    db: Database,
    *,
    accounts: Iterable[dict[str, Any]],
    movements: Iterable[dict[str, Any]],
) -> None:
    try:
        db._conn.execute("BEGIN IMMEDIATE")
        update_account_settings(db, accounts, commit=False)
        update_movement_settings(db, movements, commit=False)
        db._conn.commit()
    except Exception:
        db._conn.rollback()
        raise


def account_transaction_policy_join(
    transaction_alias: str = "t",
    setting_alias: str = "ats",
) -> str:
    return (
        f"LEFT JOIN account_total_settings {setting_alias} "
        f"ON {setting_alias}.account_id = {transaction_alias}.account_id"
    )


def account_transaction_policy_where(setting_alias: str = "ats") -> str:
    return f"COALESCE({setting_alias}.include_transactions, 1) = 1"


def _row_id(row: Any) -> Any:
    try:
        return row["id"]
    except (KeyError, IndexError, TypeError):
        pass
    if hasattr(row, "get"):
        return row.get("id")
    return None


def classify_movement(
    row: Any,
    *,
    internal_transfer_income_ids: set[Any] | None = None,
) -> str:
    category = str(row["category"] or "").strip().lower()
    amount = float(row["amount"] or 0.0)
    account_type = row["account_type"]

    if category in _CARD_PAYMENT:
        return "card_payment"
    if category in _INVESTMENT:
        return "investment"
    if category in _INTERNAL_TRANSFER:
        if (
            category in _PIX_TRANSFER_INCOME
            and income_value(amount, account_type, row["category"], external_transfer_income=True)
            > 0
        ):
            if internal_transfer_income_ids is not None and _row_id(row) not in internal_transfer_income_ids:
                return "income"
        return "internal_transfer"
    if category in _FINANCIAL_COST:
        return "financial_cost"

    spent = spending_value(amount, account_type, row["category"])
    if spent > 0:
        return "expense"
    if spent < 0:
        return "refund"
    if income_value(amount, account_type, row["category"], external_transfer_income=True) > 0:
        return "income"
    return "other_non_spending"


def included_movement_types(db: Database) -> set[str]:
    ensure_movement_settings(db)
    rows = db._conn.execute(
        """
        SELECT movement_type
          FROM movement_total_settings
         WHERE include_in_totals = 1
        """
    ).fetchall()
    return {str(row["movement_type"]) for row in rows}


def filter_rows_by_movement_policy(db: Database, rows: list[Any]) -> list[Any]:
    included = included_movement_types(db)
    internal_income_ids = internal_transfer_credit_ids(rows)
    return [
        row
        for row in rows
        if classify_movement(row, internal_transfer_income_ids=internal_income_ids) in included
    ]
