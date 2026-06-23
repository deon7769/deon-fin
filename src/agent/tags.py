from __future__ import annotations

from typing import Any

from ..storage import Database
from . import maintenance as mnt
from .buckets import CATEGORY_BUCKET_MAP, match_key_for

BLOCKED_CATEGORY_KEYS = {
    key
    for key, bucket_key in CATEGORY_BUCKET_MAP.items()
    if bucket_key is None
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


def _bucket_ids_by_key(db: Database) -> dict[str, int]:
    from ..web.repositories import buckets_repo

    buckets_repo.seed_buckets(db)
    return {bucket["key"]: int(bucket["id"]) for bucket in buckets_repo.list_buckets(db)}


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


def _category_translations() -> dict[str, str]:
    raw = mnt.load_overrides()["categorias_pt"]
    return {
        _norm(key): str(value).strip()
        for key, value in raw.items()
        if _norm(key) and str(value).strip()
    }


def _translated_category_tag(row: Any, cat_map: dict[str, str]) -> tuple[str, str | None] | None:
    category_key = _norm(row["category"])
    if not category_key or category_key in BLOCKED_CATEGORY_KEYS:
        return None

    translated = cat_map.get(category_key)
    if not translated and category_key in CATEGORY_BUCKET_MAP:
        translated = str(row["category"]).strip()
    if not translated:
        return None

    bucket_key = CATEGORY_BUCKET_MAP.get(category_key)
    return translated, bucket_key


def _merchant_tag_name(row: Any) -> str | None:
    raw = _norm(row["raw_description"] or row["description"])
    for needle, tag_name in TAG_MERCHANT_MAP.items():
        if needle in raw:
            return tag_name
    return None


def apply_tags_to_database(db: Database) -> dict[str, int]:
    from ..web.repositories import tags_repo

    tag_ids = _tag_ids_by_name(db)
    bucket_ids = _bucket_ids_by_key(db)
    cat_map = _category_translations()
    rules = _rules(db)
    stats = {
        "by_rule": 0,
        "by_map": 0,
        "unmatched": 0,
        "skipped_manual": 0,
        "created_tags": 0,
    }

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
                category_tag = _translated_category_tag(row, cat_map)
                if category_tag is not None:
                    tag_name, bucket_key = category_tag
                    bucket_id = bucket_ids.get(bucket_key or "")
                    tag, created = tags_repo.get_or_create_tag(
                        db,
                        name=tag_name,
                        color=None,
                        bucket_id=bucket_id,
                    )
                    target_id = int(tag["id"])
                    tag_ids[_norm(tag["name"])] = target_id
                    stats["created_tags"] += 1 if created else 0
                    source = "auto"
                else:
                    tag_name = _merchant_tag_name(row)
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
