from __future__ import annotations

from typing import Any

from ..storage import Database
from .buckets import match_key_for

TAG_CATEGORY_MAP: dict[str, str | None] = {
    "groceries": "Alimentação",
    "food and drinks": "Alimentação",
    "eating out": "Alimentação",
    "food delivery": "Alimentação",
    "alimentação - mercado": "Alimentação",
    "alimentação - restaurante": "Alimentação",
    "alimentaÃ§Ã£o - mercado": "Alimentação",
    "alimentaÃ§Ã£o - restaurante": "Alimentação",
    "pharmacy": "Saúde",
    "healthcare": "Saúde",
    "hospital clinics and labs": "Saúde",
    "taxi and ride-hailing": "Transporte",
    "transport": "Transporte",
    "parking": "Transporte",
    "gas stations": "Transporte",
    "video streaming": "Lazer",
    "music streaming": "Lazer",
    "entertainment": "Lazer",
    "leisure": "Lazer",
    "tickets": "Lazer",
    "education": "Educação",
    "bookstore": "Educação",
    "office supplies": "Educação",
    "clothing": "Vestuário",
    "credit card payment": None,
    "transfer - pix": None,
    "transfers": None,
    "same person transfer": None,
    "income": None,
    "salary": None,
}

TAG_MERCHANT_MAP: dict[str, str] = {
    "ifood": "Alimentação",
    "mercado": "Alimentação",
    "supermercado": "Alimentação",
    "uber": "Transporte",
    "posto": "Transporte",
    "netflix": "Lazer",
    "spotify": "Lazer",
    "microsoft": "Educação",
    "openai": "Educação",
}


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _tag_ids_by_name(db: Database) -> dict[str, int]:
    from ..web.repositories import tags_repo

    tags_repo.seed_tags(db)
    return {_norm(tag["name"]): int(tag["id"]) for tag in tags_repo.list_tags(db)}


def _rules(db: Database) -> dict[str, int | None]:
    rows = db._conn.execute(
        """
        SELECT match_key, tag_id
          FROM tag_rules
         ORDER BY match_key
        """
    ).fetchall()
    return {
        row["match_key"]: int(row["tag_id"]) if row["tag_id"] is not None else None
        for row in rows
    }


def _heuristic_tag_name(row: Any) -> str | None:
    category_key = _norm(row["category"])
    if category_key in TAG_CATEGORY_MAP:
        return TAG_CATEGORY_MAP[category_key]

    raw = _norm(row["raw_description"] or row["description"])
    for needle, tag_name in TAG_MERCHANT_MAP.items():
        if needle in raw:
            return tag_name
    return None


def apply_tags_to_database(db: Database) -> dict[str, int]:
    tag_ids = _tag_ids_by_name(db)
    rules = _rules(db)
    stats = {"by_rule": 0, "by_map": 0, "unmatched": 0, "skipped_manual": 0}

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            SELECT id, amount, category, raw_description, description, tag_id, tag_source
              FROM transactions
            """
        )
        rows: list[Any] = cur.fetchall()

        for row in rows:
            if row["tag_source"] == "manual":
                stats["skipped_manual"] += 1
                continue

            target_id: int | None = None
            source: str | None = None
            match_key = match_key_for(
                row["raw_description"] or row["description"],
                float(row["amount"]),
            )
            if match_key and match_key in rules and rules[match_key] is not None:
                target_id = int(rules[match_key])
                source = "rule"
            else:
                tag_name = _heuristic_tag_name(row)
                if tag_name:
                    target_id = tag_ids.get(_norm(tag_name))
                    source = "auto" if target_id is not None else None

            if target_id is None or source is None:
                stats["unmatched"] += 1
                continue

            if row["tag_id"] == target_id and row["tag_source"] == source:
                continue

            cur.execute(
                "UPDATE transactions SET tag_id=?, tag_source=? WHERE id=?",
                (target_id, source, row["id"]),
            )
            stats["by_rule" if source == "rule" else "by_map"] += 1

    return stats
