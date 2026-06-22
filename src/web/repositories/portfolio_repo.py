from __future__ import annotations

import hashlib
import json
from typing import Any

from ...agent.portfolio.aporte import calcular_aporte
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

VALID_ASSET_CLASSES = set(ASSET_CLASS_LABELS)

INVESTMENT_PROFILES: dict[str, dict[str, Any]] = {
    "conservador": {
        "key": "conservador",
        "label": "Conservador",
        "description": "Prioriza renda fixa e baixa volatilidade.",
        "targets": {
            "rf": 60.0,
            "rf_int": 10.0,
            "acoes_nac": 10.0,
            "acoes_int": 5.0,
            "fii": 13.0,
            "reit": 2.0,
            "cripto": 0.0,
        },
    },
    "moderado": {
        "key": "moderado",
        "label": "Moderado",
        "description": "Equilibra renda fixa, bolsa, FIIs e exposição internacional.",
        "targets": {
            "rf": 35.0,
            "rf_int": 5.0,
            "acoes_nac": 20.0,
            "acoes_int": 15.0,
            "fii": 15.0,
            "reit": 5.0,
            "cripto": 5.0,
        },
    },
    "arrojado": {
        "key": "arrojado",
        "label": "Arrojado",
        "description": "Aumenta renda variável, exterior e cripto.",
        "targets": {
            "rf": 10.0,
            "rf_int": 0.0,
            "acoes_nac": 30.0,
            "acoes_int": 25.0,
            "fii": 15.0,
            "reit": 10.0,
            "cripto": 10.0,
        },
    },
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


def _validate_asset_class(asset_class: str) -> str:
    value = str(asset_class or "").strip()
    if value not in VALID_ASSET_CLASSES:
        raise ValueError("classe de ativo inválida")
    return value


def _ordered_asset_classes() -> list[str]:
    return sorted(VALID_ASSET_CLASSES, key=lambda value: ASSET_CLASS_ORDER.get(value, 999))


def _targets_sum(targets: dict[str, float]) -> float:
    return round(sum(float(targets.get(asset_class, 0.0)) for asset_class in VALID_ASSET_CLASSES), 2)


def _profile_for_targets(targets: dict[str, float]) -> str:
    for key, profile in INVESTMENT_PROFILES.items():
        preset = profile["targets"]
        if all(abs(float(targets.get(asset_class, 0.0)) - float(preset.get(asset_class, 0.0))) < 0.001 for asset_class in VALID_ASSET_CLASSES):
            return key
    return "custom"


def _ticker(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _non_negative(value: Any, field: str) -> float:
    number = _number(value)
    if number is None or number < 0:
        raise ValueError(f"{field} inválido")
    return number


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
                       manually_adjusted=0,
                       manual_adjusted_at=NULL,
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


def create_manual_asset(
    db: Database,
    *,
    asset_class: str,
    ticker: str | None = None,
    name: str | None = None,
    quantity: float | None = None,
    manual_value: float | None = None,
    unit_price: float | None = None,
    price_source: str | None = None,
    price_updated_at: str | None = None,
) -> dict[str, Any]:
    normalized_class = _validate_asset_class(asset_class)
    normalized_ticker = _ticker(ticker)
    qty = _non_negative(quantity if quantity is not None else 0.0, "quantity")
    value = _number(manual_value)
    if value is not None and value < 0:
        raise ValueError("manual_value inválido")
    price = _number(unit_price)
    if price is not None and price < 0:
        raise ValueError("unit_price inválido")
    if normalized_class not in {"rf", "rf_int"} and not normalized_ticker:
        raise ValueError("ticker obrigatório")
    current_value = value if value is not None else (qty * price if price is not None else 0.0)
    source = price_source or ("manual" if value is not None else None)

    with db._cursor() as cur:  # type: ignore[attr-defined]
        row = None
        if normalized_ticker:
            row = cur.execute(
                """
                SELECT id
                  FROM portfolio_assets
                 WHERE source='manual'
                   AND asset_class=?
                   AND ticker=?
                """,
                (normalized_class, normalized_ticker),
            ).fetchone()
        if row:
            cur.execute(
                """
                UPDATE portfolio_assets
                   SET name=?,
                       quantity=?,
                       manual_value=?,
                       current_value=?,
                       unit_price=?,
                       price_source=?,
                       price_updated_at=?,
                       status='ACTIVE',
                       updated_at=datetime('now')
                 WHERE id=?
                """,
                (
                    _text(name) or normalized_ticker,
                    qty,
                    value,
                    _money(current_value),
                    price,
                    source,
                    price_updated_at,
                    row["id"],
                ),
            )
            asset_id = int(row["id"])
        else:
            cur.execute(
                """
                INSERT INTO portfolio_assets (
                    asset_class, ticker, name, quantity, source, manual_value,
                    current_value, unit_price, currency, status, price_source,
                    price_updated_at
                )
                VALUES (?, ?, ?, ?, 'manual', ?, ?, ?, 'BRL', 'ACTIVE', ?, ?)
                """,
                (
                    normalized_class,
                    normalized_ticker,
                    _text(name) or normalized_ticker,
                    qty,
                    value,
                    _money(current_value),
                    price,
                    source,
                    price_updated_at,
                ),
            )
            asset_id = int(cur.lastrowid)
    asset = get_asset(db, asset_id)
    if asset is None:
        raise RuntimeError("ativo não foi criado")
    return asset


def get_asset(db: Database, asset_id: int) -> dict[str, Any] | None:
    row = db._conn.execute(
        "SELECT * FROM portfolio_assets WHERE id=?",
        (asset_id,),
    ).fetchone()
    return _row_to_asset(row) if row else None


def update_asset(db: Database, asset_id: int, **updates: Any) -> dict[str, Any] | None:
    current = db._conn.execute(
        "SELECT * FROM portfolio_assets WHERE id=?",
        (asset_id,),
    ).fetchone()
    if current is None:
        return None

    asset_class = current["asset_class"]
    if "asset_class" in updates and updates["asset_class"] is not None:
        asset_class = _validate_asset_class(updates["asset_class"])
    ticker = current["ticker"]
    if "ticker" in updates:
        ticker = _ticker(updates["ticker"])
    name = current["name"]
    if "name" in updates:
        name = _text(updates["name"])
    quantity = float(current["quantity"] or 0.0)
    quantity_changed = False
    if "quantity" in updates and updates["quantity"] is not None:
        new_quantity = _non_negative(updates["quantity"], "quantity")
        quantity_changed = abs(new_quantity - quantity) > 0.0000001
        quantity = new_quantity
    manual_value = _number(current["manual_value"])
    if "manual_value" in updates:
        manual_value = _number(updates["manual_value"])
        if manual_value is not None and manual_value < 0:
            raise ValueError("manual_value inválido")
    unit_price = _number(current["unit_price"])
    price_source = current["price_source"]
    if "manual_value" in updates and manual_value is not None:
        current_value = manual_value
        price_source = "manual"
    elif unit_price is not None:
        current_value = quantity * unit_price
    else:
        current_value = _number(current["current_value"]) or 0.0
    manual_adjust_sql = ""
    if quantity_changed:
        manual_adjust_sql = ", manually_adjusted=1, manual_adjusted_at=datetime('now')"

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            f"""
            UPDATE portfolio_assets
               SET asset_class=?,
                   ticker=?,
                   name=?,
                   quantity=?,
                   manual_value=?,
                   current_value=?,
                   price_source=?,
                   updated_at=datetime('now')
                   {manual_adjust_sql}
             WHERE id=?
            """,
            (
                asset_class,
                ticker,
                name,
                quantity,
                manual_value,
                _money(current_value),
                price_source,
                asset_id,
            ),
        )
    return get_asset(db, asset_id)


def delete_asset(db: Database, asset_id: int) -> dict[str, int] | None:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("DELETE FROM portfolio_assets WHERE id=?", (asset_id,))
        if cur.rowcount == 0:
            return None
    return {"deleted_id": asset_id}


def set_price(
    db: Database,
    asset_id: int,
    *,
    price: float,
    currency: str = "BRL",
    price_source: str = "brapi",
    price_updated_at: str | None = None,
) -> dict[str, Any] | None:
    current = db._conn.execute(
        "SELECT quantity FROM portfolio_assets WHERE id=?",
        (asset_id,),
    ).fetchone()
    if current is None:
        return None
    value = float(current["quantity"] or 0.0) * float(price)
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            UPDATE portfolio_assets
               SET unit_price=?,
                   current_value=?,
                   currency=?,
                   price_source=?,
                   price_updated_at=?,
                   updated_at=datetime('now')
             WHERE id=?
            """,
            (
                float(price),
                _money(value),
                currency or "BRL",
                price_source,
                price_updated_at,
                asset_id,
            ),
        )
    return get_asset(db, asset_id)


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
        "manually_adjusted": bool(row["manually_adjusted"] or 0),
        "manual_adjusted_at": row["manual_adjusted_at"],
        "price_source": row["price_source"],
        "price_updated_at": row["price_updated_at"],
        "pct_carteira": 0.0,
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
    assets = [_row_to_asset(row) for row in rows]
    from . import score_repo

    for asset in assets:
        asset["nota"] = score_repo.compute_nota(db, asset["id"])["nota"]
    return assets


def portfolio_summary(db: Database, *, include_inactive: bool = False) -> dict[str, Any]:
    assets = list_assets(db, include_inactive=include_inactive)
    total_value = _money(sum(asset["current_value"] for asset in assets))
    for asset in assets:
        asset["pct_carteira"] = (
            _money((asset["current_value"] / total_value) * 100) if total_value else 0.0
        )
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


def seed_allocation_targets(db: Database) -> None:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        for asset_class in _ordered_asset_classes():
            cur.execute(
                """
                INSERT OR IGNORE INTO allocation_targets (asset_class, target_pct)
                VALUES (?, 0)
                """,
                (asset_class,),
            )
        cur.execute(
            """
            INSERT OR IGNORE INTO investment_profile (id, perfil)
            VALUES (1, 'custom')
            """
        )


def get_investment_profiles() -> dict[str, Any]:
    return {
        "profiles": [INVESTMENT_PROFILES[key] for key in ("conservador", "moderado", "arrojado")]
    }


def _targets_response(db: Database) -> dict[str, Any]:
    seed_allocation_targets(db)
    rows = db._conn.execute(
        "SELECT asset_class, target_pct FROM allocation_targets"
    ).fetchall()
    targets = {asset_class: 0.0 for asset_class in _ordered_asset_classes()}
    for row in rows:
        asset_class = row["asset_class"]
        if asset_class in VALID_ASSET_CLASSES:
            targets[asset_class] = _money(row["target_pct"])
    profile = db._conn.execute(
        "SELECT perfil, ultimo_aporte, updated_at FROM investment_profile WHERE id=1"
    ).fetchone()
    sum_pct = _targets_sum(targets)
    classes = [
        {
            "asset_class": asset_class,
            "label": ASSET_CLASS_LABELS[asset_class],
            "target_pct": targets[asset_class],
        }
        for asset_class in _ordered_asset_classes()
    ]
    return {
        "targets": targets,
        "classes": classes,
        "perfil": profile["perfil"] if profile else "custom",
        "ultimo_aporte": _money(profile["ultimo_aporte"]) if profile and profile["ultimo_aporte"] is not None else None,
        "sum_pct": sum_pct,
        "valid": abs(sum_pct - 100.0) < 0.001,
    }


def get_allocation_targets(db: Database) -> dict[str, Any]:
    return _targets_response(db)


def save_allocation_targets(
    db: Database,
    targets: dict[str, Any],
    *,
    perfil: str | None = None,
) -> dict[str, Any]:
    normalized = {asset_class: 0.0 for asset_class in _ordered_asset_classes()}
    for asset_class, value in targets.items():
        normalized_class = _validate_asset_class(asset_class)
        pct = _number(value)
        if pct is None or pct < 0 or pct > 100:
            raise ValueError("percentual inválido")
        normalized[normalized_class] = round(float(pct), 2)
    if abs(_targets_sum(normalized) - 100.0) >= 0.001:
        raise ValueError("targets_sum")

    detected_profile = _profile_for_targets(normalized)

    with db._cursor() as cur:  # type: ignore[attr-defined]
        for asset_class, target_pct in normalized.items():
            cur.execute(
                """
                INSERT INTO allocation_targets (asset_class, target_pct)
                VALUES (?, ?)
                ON CONFLICT(asset_class) DO UPDATE SET target_pct=excluded.target_pct
                """,
                (asset_class, target_pct),
            )
        cur.execute(
            """
            INSERT INTO investment_profile (id, perfil, updated_at)
            VALUES (1, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                perfil=excluded.perfil,
                updated_at=datetime('now')
            """,
            (detected_profile,),
        )
    return _targets_response(db)


def _asset_to_aporte_input(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": asset["id"],
        "asset_class": asset["asset_class"],
        "ticker": asset["ticker"] or asset["name"],
        "nota": asset.get("nota"),
        "valor_atual": asset["current_value"],
        "preco": asset["unit_price"] or 0.0,
        "fracionavel": asset["asset_class"] in {"acoes_int", "reit", "cripto"},
    }


def calculate_aporte(db: Database, aporte: float) -> dict[str, Any]:
    targets_response = get_allocation_targets(db)
    if not targets_response["valid"]:
        raise ValueError("targets_sum")
    assets = list_assets(db)
    return calcular_aporte(
        aporte,
        [_asset_to_aporte_input(asset) for asset in assets],
        targets_response["targets"],
    )


def add_asset_quantity(db: Database, asset_id: int, quantity: float) -> dict[str, Any] | None:
    if quantity <= 0:
        raise ValueError("quantidade inválida")
    current = db._conn.execute(
        "SELECT * FROM portfolio_assets WHERE id=?",
        (asset_id,),
    ).fetchone()
    if current is None:
        return None
    current_quantity = float(current["quantity"] or 0.0)
    unit_price = _number(current["unit_price"])
    current_value = _number(current["current_value"]) or 0.0
    new_quantity = current_quantity + float(quantity)
    if unit_price is not None and unit_price > 0:
        new_value = new_quantity * unit_price
        manual_value = current["manual_value"]
    else:
        new_value = current_value + float(quantity)
        manual_value = new_value if current["asset_class"] in {"rf", "rf_int"} else current["manual_value"]
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            UPDATE portfolio_assets
               SET quantity=?,
                   manual_value=?,
                   current_value=?,
                   manually_adjusted=1,
                   manual_adjusted_at=datetime('now'),
                   updated_at=datetime('now')
             WHERE id=?
            """,
            (new_quantity, manual_value, _money(new_value), asset_id),
        )
    return get_asset(db, asset_id)


def confirm_aporte(
    db: Database,
    *,
    compras: list[dict[str, Any]],
    aporte: float | None = None,
) -> dict[str, Any]:
    total_aporte = 0.0
    for compra in compras:
        asset_id = int(compra["asset_id"])
        quantidade = float(compra["quantidade"])
        asset = db._conn.execute(
            "SELECT unit_price FROM portfolio_assets WHERE id=?",
            (asset_id,),
        ).fetchone()
        if asset is None:
            raise ValueError("ativo não encontrado")
        unit_price = _number(asset["unit_price"])
        total_aporte += quantidade * unit_price if unit_price is not None and unit_price > 0 else quantidade
        if add_asset_quantity(db, asset_id, quantidade) is None:
            raise ValueError("ativo não encontrado")

    ultimo_aporte = _money(aporte if aporte is not None else total_aporte)
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO investment_profile (id, perfil, ultimo_aporte, updated_at)
            VALUES (1, 'custom', ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                ultimo_aporte=excluded.ultimo_aporte,
                updated_at=datetime('now')
            """,
            (ultimo_aporte,),
        )
    return portfolio_summary(db)
