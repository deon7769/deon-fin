from __future__ import annotations

import json
import re
from typing import Any

from ...agent.cards import CREDIT_TYPES
from ...storage import Database
from . import painel_repo

_YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")

_BANK_CODE_NAMES = {
    "001": "Banco do Brasil",
    "033": "Santander",
    "077": "Banco Inter",
    "104": "Caixa",
    "208": "BTG Pactual",
    "237": "Bradesco",
    "260": "Nubank",
    "323": "Mercado Pago",
    "341": "Itaú",
}

_GENERIC_ACCOUNT_NAMES = {
    "conta",
    "conta corrente",
    "conta poupanca",
    "conta poupança",
    "poupanca",
    "poupança",
    "checking account",
    "savings account",
}

_CARD_LEVEL_NAMES = {
    "black",
    "classic",
    "gold",
    "international",
    "internacional",
    "platinum",
    "standard",
    "universal",
}


def _money(value: float) -> float:
    return round(float(value), 2)


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _load_meta(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _valid_year_month(value: str) -> bool:
    if not _YEAR_MONTH_RE.match(value):
        return False
    return 1 <= int(value[5:7]) <= 12


def _is_credit(account_type: str | None) -> bool:
    return (account_type or "").upper() in CREDIT_TYPES


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _display_brand(value: Any) -> str | None:
    text = str(value or "").replace("_", " ").strip()
    return text.title() if text else None


def _bank_code(meta: dict[str, Any], institution: str | None) -> str | None:
    bank_data = meta.get("bankData") if isinstance(meta.get("bankData"), dict) else {}
    raw = str(bank_data.get("transferNumber") or institution or "")
    digits = "".join(ch for ch in raw.split("/", 1)[0] if ch.isdigit())
    return digits[:3] if len(digits) >= 3 else None


def _bank_name(meta: dict[str, Any], institution: str | None) -> str | None:
    return _BANK_CODE_NAMES.get(_bank_code(meta, institution) or "")


def _is_generic_account_name(value: Any) -> bool:
    return _normalized_text(value) in _GENERIC_ACCOUNT_NAMES


def _is_probably_person_name(value: Any) -> bool:
    text = str(value or "").strip()
    if not text or any(ch.isdigit() for ch in text):
        return False
    return len(text.split()) >= 2 and text.upper() == text


def _is_card_level_name(value: Any) -> bool:
    return _normalized_text(value) in _CARD_LEVEL_NAMES


def _item_id(row: Any, meta: dict[str, Any]) -> str | None:
    item_id = row["pluggy_item_id"] or meta.get("itemId") or meta.get("item_id")
    return str(item_id) if item_id else None


def _sort_key(row: Any) -> tuple[int, str, str]:
    sort_order = row["sort_order"]
    return (
        int(sort_order) if sort_order is not None else 999_999,
        (row["institution"] or "").lower(),
        (row["name"] or "").lower(),
    )


def _last4(*values: Any) -> str | None:
    for value in values:
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        if len(digits) >= 4:
            return digits[-4:]
    return None


def _bank_display_name(row: Any, meta: dict[str, Any]) -> str:
    raw_name = row["name"] or row["institution"]
    bank_name = _bank_name(meta, row["institution"])

    if bank_name and _is_generic_account_name(raw_name):
        return f"{bank_name} - {raw_name or _bank_type_label(row['type'])}"

    marketing_name = str(meta.get("marketingName") or "").strip()
    if marketing_name and not raw_name:
        return marketing_name

    return str(raw_name or bank_name or "Conta")


def _item_bank_names(rows: list[Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for row in rows:
        if _is_credit(row["type"]):
            continue
        meta = _load_meta(row["metadata_json"])
        item_id = _item_id(row, meta)
        if not item_id or item_id in names:
            continue
        names[item_id] = _bank_name(meta, row["institution"]) or _bank_display_name(row, meta)
    return names


def _card_display_name(row: Any, meta: dict[str, Any], item_bank_name: str | None) -> str:
    raw_name = row["name"] or row["institution"]
    if raw_name and not (
        _is_generic_account_name(raw_name)
        or _is_probably_person_name(raw_name)
        or _is_card_level_name(raw_name)
    ):
        return str(raw_name)

    credit_data = meta.get("creditData") if isinstance(meta.get("creditData"), dict) else {}
    brand = _display_brand(row["brand"] or credit_data.get("brand"))
    last4 = row["last4"] or _last4(meta.get("number"), raw_name)
    parts = [item_bank_name, brand, f"final {last4}" if last4 else None]
    label = " ".join(str(part) for part in parts if part)
    return label or str(raw_name or "Cartão")


def _bank_parts(meta: dict[str, Any], institution: str | None) -> tuple[str | None, str | None]:
    bank_data = meta.get("bankData") if isinstance(meta.get("bankData"), dict) else {}
    raw = str(bank_data.get("transferNumber") or institution or "").strip()
    parts = [part for part in raw.split("/") if part]
    if len(parts) >= 2:
        return "/".join(parts[:-1]), parts[-1]
    return None, raw or None


def _bank_type_label(account_type: str | None) -> str:
    normalized = (account_type or "").upper()
    if normalized in {"CHECKING", "CHECKING_ACCOUNT"}:
        return "Conta corrente"
    if normalized in {"SAVINGS", "SAVINGS_ACCOUNT"}:
        return "Conta poupança"
    if normalized in {"BANK", "ACCOUNT"}:
        return "Conta bancária"
    return account_type or "Conta bancária"


def _usage_pct(used: float | None, credit_limit: float | None) -> float | None:
    if used is None or not credit_limit or credit_limit <= 0:
        return None
    return _money(used / credit_limit * 100)


def resolve_month(db: Database, month: str | None) -> str | None:
    if month is not None:
        return month if _valid_year_month(month) else None
    return painel_repo.resolve_month(db, None)


def upsert_balance(
    db: Database,
    *,
    account_id: str,
    balance: float | None,
    credit_limit: float | None,
    used: float | None,
    available: float | None,
    brand: str | None,
    last4: str | None,
    last_sync_at: str | None,
    sync_status: str | None,
) -> None:
    db._conn.execute(
        """
        INSERT INTO account_balances (
            account_id, balance, credit_limit, used, available, brand, last4,
            last_sync_at, sync_status, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(account_id) DO UPDATE SET
            balance=excluded.balance,
            credit_limit=excluded.credit_limit,
            used=excluded.used,
            available=excluded.available,
            brand=excluded.brand,
            last4=excluded.last4,
            last_sync_at=excluded.last_sync_at,
            sync_status=excluded.sync_status,
            updated_at=datetime('now')
        """,
        (
            account_id,
            balance,
            credit_limit,
            used,
            available,
            brand,
            last4,
            last_sync_at,
            sync_status,
        ),
    )
    db._conn.commit()


def set_account_item(db: Database, account_id: str, item_id: str | None) -> None:
    db._conn.execute(
        "UPDATE accounts SET pluggy_item_id=? WHERE id=?",
        (item_id, account_id),
    )
    db._conn.commit()


def resolve_item_id(db: Database, account_id: str) -> str | None:
    row = db._conn.execute(
        "SELECT pluggy_item_id, metadata_json FROM accounts WHERE id=?",
        (account_id,),
    ).fetchone()
    if row is None:
        return None
    if row["pluggy_item_id"]:
        return row["pluggy_item_id"]
    meta = _load_meta(row["metadata_json"])
    item_id = meta.get("itemId") or meta.get("item_id")
    return str(item_id) if item_id else None


def set_sort(db: Database, order: list[str]) -> int:
    updated = 0
    for index, account_id in enumerate(order):
        cur = db._conn.execute(
            "UPDATE accounts SET sort_order=? WHERE id=?",
            (index, account_id),
        )
        updated += cur.rowcount
    db._conn.commit()
    return updated


def _accounts_for_item(db: Database, item_id: str) -> list[str]:
    rows = db._conn.execute(
        """
        SELECT id, pluggy_item_id, metadata_json
          FROM accounts
         WHERE pluggy_item_id=?
            OR metadata_json LIKE ?
        """,
        (item_id, f"%{item_id}%"),
    ).fetchall()
    ids: list[str] = []
    for row in rows:
        meta = _load_meta(row["metadata_json"])
        meta_item = meta.get("itemId") or meta.get("item_id")
        if row["pluggy_item_id"] == item_id or meta_item == item_id:
            ids.append(row["id"])
    return sorted(ids)


def disconnect(db: Database, item_id: str) -> dict[str, Any]:
    account_ids = _accounts_for_item(db, item_id)
    db.delete_pluggy_item(item_id)
    for account_id in account_ids:
        db._conn.execute(
            """
            INSERT INTO account_balances (account_id, sync_status, updated_at)
            VALUES (?, 'DISCONNECTED', datetime('now'))
            ON CONFLICT(account_id) DO UPDATE SET
                sync_status='DISCONNECTED',
                updated_at=datetime('now')
            """,
            (account_id,),
        )
    db._conn.commit()
    return {
        "deleted": True,
        "item_id": item_id,
        "kept_transactions": True,
        "accounts_disconnected": account_ids,
    }


def _derived_balance(db: Database, account_id: str) -> float:
    row = db._conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE account_id=?",
        (account_id,),
    ).fetchone()
    return _money(row[0] or 0.0)


def _period_result(db: Database, month: str) -> float:
    return _money(painel_repo.month_summary(db, month)["result"])


def _account_rows(db: Database) -> list[Any]:
    return db._conn.execute(
        """
        SELECT a.id,
               a.source,
               a.institution,
               a.name,
               a.type,
               a.currency,
               a.metadata_json,
               a.sort_order,
               a.pluggy_item_id,
               b.balance,
               b.credit_limit,
               b.used,
               b.available,
               b.brand,
               b.last4,
               b.last_sync_at,
               b.sync_status,
               COALESCE(s.include_balance, 1) AS include_balance_in_totals,
               p.connector_name
          FROM accounts a
          LEFT JOIN account_balances b ON b.account_id = a.id
          LEFT JOIN account_total_settings s ON s.account_id = a.id
          LEFT JOIN pluggy_items p
            ON p.id = COALESCE(
                a.pluggy_item_id,
                json_extract(a.metadata_json, '$.itemId'),
                json_extract(a.metadata_json, '$.item_id')
            )
        """
    ).fetchall()


def list_accounts_overview(db: Database, *, month: str) -> dict[str, Any]:
    banks: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    accounts_balance = 0.0
    card_debt = 0.0
    rows = sorted(_account_rows(db), key=_sort_key)
    item_bank_names = _item_bank_names(rows)

    for row in rows:
        meta = _load_meta(row["metadata_json"])
        item_id = _item_id(row, meta)
        include_balance_in_totals = bool(row["include_balance_in_totals"])
        if _is_credit(row["type"]):
            credit_limit = _number(row["credit_limit"])
            used = _number(row["used"])
            available = _number(row["available"])
            brand = row["brand"]
            last4 = row["last4"] or _last4(meta.get("number"))
            if include_balance_in_totals:
                card_debt += used or 0.0
            cards.append(
                {
                    "id": row["id"],
                    "name": _card_display_name(row, meta, item_bank_names.get(item_id or "")),
                    "last4": last4,
                    "brand": brand,
                    "credit_limit": credit_limit,
                    "used": used,
                    "available": available,
                    "usage_pct": _usage_pct(used, credit_limit),
                    "currency": row["currency"] or "BRL",
                    "pluggy_item_id": item_id,
                    "connector_name": row["connector_name"],
                    "last_sync_at": row["last_sync_at"],
                    "sync_status": row["sync_status"] or "UNKNOWN",
                    "manual": row["source"] != "pluggy",
                }
            )
            continue

        balance = _number(row["balance"])
        status = row["sync_status"]
        if balance is None:
            balance = _derived_balance(db, row["id"])
            status = status or "DERIVED"
        agency, number = _bank_parts(meta, row["institution"])
        if include_balance_in_totals:
            accounts_balance += balance or 0.0
        banks.append(
            {
                "id": row["id"],
                "institution": row["institution"],
                "name": _bank_display_name(row, meta),
                "type": _bank_type_label(row["type"]),
                "agency": agency,
                "number": number,
                "balance": _money(balance or 0.0),
                "currency": row["currency"] or "BRL",
                "pluggy_item_id": item_id,
                "connector_name": row["connector_name"],
                "last_sync_at": row["last_sync_at"],
                "sync_status": status or "UNKNOWN",
                "manual": row["source"] != "pluggy",
            }
        )

    return {
        "banks": banks,
        "cards": cards,
        "totals": {
            "accounts_balance": _money(accounts_balance),
            "card_debt": _money(card_debt),
            "period_result": _period_result(db, month),
        },
    }
