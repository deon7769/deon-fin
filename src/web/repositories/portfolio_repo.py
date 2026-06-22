from __future__ import annotations

import hashlib
import json
from typing import Any

from ...storage import Database


ASSET_CLASS_LABELS = {
    "acoes_nac": "Ações nacionais",
    "acoes_int": "Ações internacionais",
    "fii": "FIIs",
    "reit": "REITs",
    "cripto": "Cripto",
    "rf": "Renda fixa",
    "rf_int": "Renda fixa internacional",
}

ASSET_CLASS_ORDER = {
    "acoes_nac": 10,
    "fii": 20,
    "rf": 30,
    "cripto": 40,
    "acoes_int": 50,
    "reit": 60,
    "rf_int": 70,
}


def _money(value: Any) -> float:
    return round(float(value or 0.0), 2)


def _number(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return text.split("T")[0]


def classify_pluggy_investment(investment: dict[str, Any]) -> str:
    provider_type = (investment.get("type") or "").upper()
    provider_subtype = (investment.get("subtype") or "").upper()
    ticker = (_text(investment.get("code")) or _text(investment.get("name")) or "").upper()
    if provider_type == "FIXED_INCOME":
        return "rf"
    if provider_type == "CRYPTO":
        return "cripto"
    if provider_type == "EQUITY" and provider_subtype in {"REIT", "REITS"}:
        return "reit"
    if provider_type == "EQUITY" and ticker.endswith("11"):
        return "fii"
    if provider_type == "EQUITY":
        return "acoes_nac"
    return "acoes_nac"


def upsert_pluggy_asset(db: Database, investment: dict[str, Any]) -> int:
    external_id = _text(investment.get("id"))
    if not external_id:
        raise ValueError("investimento Pluggy sem id")
    ticker = (_text(investment.get("code")) or _text(investment.get("name")))
    asset_class = classify_pluggy_investment(investment)
    current_value = _number(investment.get("balance"))
    if current_value is None:
        current_value = _number(investment.get("amount"))
    unit_price = _number(investment.get("value"))
    quantity = _number(investment.get("quantity")) or 0.0
    metadata = {
        key: value
        for key, value in investment.items()
        if key
        not in {
            "id",
            "name",
            "code",
            "quantity",
            "currencyCode",
            "type",
            "subtype",
            "status",
            "date",
            "balance",
            "value",
        }
    }
    with db._cursor() as cur:  # type: ignore[attr-defined]
        row = cur.execute(
            """
            SELECT id
              FROM portfolio_assets
             WHERE source='pluggy'
               AND external_id=?
            """,
            (external_id,),
        ).fetchone()
        values = (
            asset_class,
            ticker.upper() if ticker else None,
            _text(investment.get("name")),
            quantity,
            "pluggy",
            external_id,
            current_value,
            unit_price,
            investment.get("currencyCode") or "BRL",
            _text(investment.get("type")),
            _text(investment.get("subtype")),
            _text(investment.get("status")),
            _date(investment.get("date")),
            json.dumps(metadata, ensure_ascii=False),
        )
        if row:
            cur.execute(
                """
                UPDATE portfolio_assets
                   SET asset_class=?,
                       ticker=?,
                       name=?,
                       quantity=?,
                       source=?,
                       external_id=?,
                       current_value=?,
                       unit_price=?,
                       currency=?,
                       provider_type=?,
                       provider_subtype=?,
                       status=?,
                       as_of_date=?,
                       metadata_json=?,
                       updated_at=datetime('now')
                 WHERE id=?
                """,
                (*values, row["id"]),
            )
            return int(row["id"])
        cur.execute(
            """
            INSERT INTO portfolio_assets (
                asset_class, ticker, name, quantity, source, external_id,
                current_value, unit_price, currency, provider_type, provider_subtype,
                status, as_of_date, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return int(cur.lastrowid)


def upsert_pluggy_transaction(
    db: Database,
    *,
    asset_id: int,
    transaction: dict[str, Any],
) -> str:
    external_id = _text(transaction.get("id"))
    if not external_id:
        seed = json.dumps(transaction, sort_keys=True, ensure_ascii=False)
        external_id = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    tx_id = f"pluggy:{external_id}"
    metadata = {
        key: value
        for key, value in transaction.items()
        if key
        not in {
            "id",
            "type",
            "movementType",
            "tradeDate",
            "date",
            "quantity",
            "value",
            "amount",
            "netAmount",
            "description",
        }
    }
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO portfolio_transactions (
                id, asset_id, source, external_id, type, movement_type,
                trade_date, posted_at, quantity, unit_value, amount, net_amount,
                description, metadata_json
            )
            VALUES (?, ?, 'pluggy', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                asset_id=excluded.asset_id,
                type=excluded.type,
                movement_type=excluded.movement_type,
                trade_date=excluded.trade_date,
                posted_at=excluded.posted_at,
                quantity=excluded.quantity,
                unit_value=excluded.unit_value,
                amount=excluded.amount,
                net_amount=excluded.net_amount,
                description=excluded.description,
                metadata_json=excluded.metadata_json
            """,
            (
                tx_id,
                asset_id,
                external_id,
                _text(transaction.get("type")),
                _text(transaction.get("movementType")),
                _date(transaction.get("tradeDate")),
                _date(transaction.get("date")),
                _number(transaction.get("quantity")),
                _number(transaction.get("value")),
                _number(transaction.get("amount")),
                _number(transaction.get("netAmount")),
                _text(transaction.get("description")),
                json.dumps(metadata, ensure_ascii=False),
            ),
        )
    return tx_id


def _row_to_asset(row: Any) -> dict[str, Any]:
    asset_class = row["asset_class"]
    return {
        "id": int(row["id"]),
        "asset_class": asset_class,
        "asset_class_label": ASSET_CLASS_LABELS.get(asset_class, asset_class),
        "ticker": row["ticker"],
        "name": row["name"],
        "quantity": _money(row["quantity"]),
        "source": row["source"],
        "external_id": row["external_id"],
        "manual_value": _money(row["manual_value"]) if row["manual_value"] is not None else None,
        "current_value": _money(row["current_value"]),
        "unit_price": _money(row["unit_price"]) if row["unit_price"] is not None else None,
        "currency": row["currency"] or "BRL",
        "provider_type": row["provider_type"],
        "provider_subtype": row["provider_subtype"],
        "status": row["status"],
        "as_of_date": row["as_of_date"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_assets(db: Database, *, include_inactive: bool = False) -> list[dict[str, Any]]:
    where = ""
    if not include_inactive:
        where = "WHERE status IS NULL OR status='ACTIVE'"
    rows = db._conn.execute(
        f"""
        SELECT *
          FROM portfolio_assets
          {where}
         ORDER BY
              CASE asset_class
                WHEN 'acoes_nac' THEN 10
                WHEN 'fii' THEN 20
                WHEN 'rf' THEN 30
                WHEN 'cripto' THEN 40
                WHEN 'acoes_int' THEN 50
                WHEN 'reit' THEN 60
                WHEN 'rf_int' THEN 70
                ELSE 999
              END,
              COALESCE(ticker, name, ''),
              id
        """
    ).fetchall()
    return [_row_to_asset(row) for row in rows]


def portfolio_summary(db: Database, *, include_inactive: bool = False) -> dict[str, Any]:
    assets = list_assets(db, include_inactive=include_inactive)
    total_value = _money(sum(asset["current_value"] for asset in assets))
    by_class_map: dict[str, dict[str, Any]] = {}
    for asset in assets:
        key = asset["asset_class"]
        item = by_class_map.setdefault(
            key,
            {
                "asset_class": key,
                "label": ASSET_CLASS_LABELS.get(key, key),
                "count": 0,
                "current_value": 0.0,
                "pct": 0.0,
            },
        )
        item["count"] += 1
        item["current_value"] = _money(item["current_value"] + asset["current_value"])
    by_class = sorted(
        by_class_map.values(),
        key=lambda item: ASSET_CLASS_ORDER.get(item["asset_class"], 999),
    )
    for item in by_class:
        item["pct"] = _money((item["current_value"] / total_value) * 100) if total_value else 0.0
    return {
        "totals": {
            "asset_count": len(assets),
            "current_value": total_value,
        },
        "by_class": by_class,
        "assets": assets,
    }
