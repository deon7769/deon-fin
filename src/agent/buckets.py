from __future__ import annotations

from typing import Any

from ..storage import Database
from .context import _merchant_key

LIBERDADE = "liberdade_financeira"
FIXOS = "custos_fixos"
CONFORTO = "conforto"
METAS = "metas"
PRAZERES = "prazeres"
CONHECIMENTO = "conhecimento"

CATEGORY_BUCKET_MAP: dict[str, str | None] = {
    "moradia - aluguel": FIXOS,
    "moradia - contas": FIXOS,
    "saúde - plano/consulta": FIXOS,
    "transporte - app": FIXOS,
    "transporte - combustível": FIXOS,
    "transporte - estacionamento": FIXOS,
    "services": FIXOS,
    "electricity": FIXOS,
    "water": FIXOS,
    "housing": FIXOS,
    "rent": FIXOS,
    "telecommunications": FIXOS,
    "internet": FIXOS,
    "utilities": FIXOS,
    "insurance": FIXOS,
    "vehicle insurance": FIXOS,
    "healthcare": FIXOS,
    "hospital clinics and labs": FIXOS,
    "automotive": FIXOS,
    "taxi and ride-hailing": FIXOS,
    "transport": FIXOS,
    "parking": FIXOS,
    "gas stations": FIXOS,
    "income taxes": FIXOS,
    "optometry": FIXOS,
    "alimentação - mercado": CONFORTO,
    "alimentação - restaurante": CONFORTO,
    "saúde - farmácia": CONFORTO,
    "groceries": CONFORTO,
    "food and drinks": CONFORTO,
    "eating out": CONFORTO,
    "food delivery": CONFORTO,
    "pharmacy": CONFORTO,
    "clothing": CONFORTO,
    "houseware": CONFORTO,
    "wellness and fitness": CONFORTO,
    "gyms and fitness centers": CONFORTO,
    "assinaturas - streaming": PRAZERES,
    "lazer - cinema/show": PRAZERES,
    "compras - e-commerce": PRAZERES,
    "shopping": PRAZERES,
    "online shopping": PRAZERES,
    "leisure": PRAZERES,
    "tickets": PRAZERES,
    "entertainment": PRAZERES,
    "video streaming": PRAZERES,
    "music streaming": PRAZERES,
    "digital services": PRAZERES,
    "travel": PRAZERES,
    "accomodation": PRAZERES,
    "electronics": PRAZERES,
    "donations": PRAZERES,
    "educação": CONHECIMENTO,
    "assinaturas - software": CONHECIMENTO,
    "education": CONHECIMENTO,
    "bookstore": CONHECIMENTO,
    "office supplies": CONHECIMENTO,
    "investimentos": LIBERDADE,
    "investments": LIBERDADE,
    "savings": LIBERDADE,
    "loans and financing": LIBERDADE,
    "tarifas bancárias": None,
    "credit card fees": None,
    "interests charged": None,
    "tax on financial operations": None,
    "bank fees": None,
    "financial expenses": None,
    "transferências - pix": None,
    "transferências - ted/doc": None,
    "transfer - pix": None,
    "transfers": None,
    "same person transfer": None,
    "transfer - bank slip": None,
    "credit card payment": None,
    "pagamento de fatura": None,
    "renda - salário": None,
    "income": None,
    "salary": None,
}


def classify_bucket(category: str | None) -> str | None:
    return CATEGORY_BUCKET_MAP.get((category or "").lower().strip())


def match_key_for(raw: str | None, amount: float) -> str:
    merchant_key = _merchant_key(raw or "")
    if not merchant_key:
        return ""
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{merchant_key}"


def apply_buckets_to_database(db: Database) -> dict[str, int]:
    from ..web.repositories import buckets_repo

    buckets_repo.seed_buckets(db)
    buckets = {bucket["key"]: bucket["id"] for bucket in buckets_repo.list_buckets(db)}
    rules = {rule["match_key"]: rule["bucket_id"] for rule in buckets_repo.list_rules(db)}
    stats = {"by_rule": 0, "by_map": 0, "unmatched": 0, "skipped_manual": 0}

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            SELECT id, amount, category, raw_description, description, bucket_id, bucket_source
              FROM transactions
            """
        )
        rows: list[Any] = cur.fetchall()

        for row in rows:
            if row["bucket_source"] == "manual":
                stats["skipped_manual"] += 1
                continue

            target_id: int | None = None
            source: str | None = None
            match_key = match_key_for(
                row["raw_description"] or row["description"],
                float(row["amount"]),
            )
            if match_key and match_key in rules:
                target_id = int(rules[match_key])
                source = "rule"
            else:
                bucket_key = classify_bucket(row["category"])
                if bucket_key and bucket_key in buckets:
                    target_id = int(buckets[bucket_key])
                    source = "auto"

            if target_id is None or source is None:
                stats["unmatched"] += 1
                continue

            if row["bucket_id"] == target_id and row["bucket_source"] == source:
                continue

            cur.execute(
                "UPDATE transactions SET bucket_id=?, bucket_source=? WHERE id=?",
                (target_id, source, row["id"]),
            )
            stats["by_rule" if source == "rule" else "by_map"] += 1

    return stats
