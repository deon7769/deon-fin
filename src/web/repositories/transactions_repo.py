from __future__ import annotations

from datetime import date
from typing import Any

from ...agent.buckets import match_key_for
from ...storage import Database
from ...storage.reference_month import reference_month
from . import buckets_repo, tags_repo


class TransactionNotFoundError(ValueError):
    pass


class BucketNotFoundError(ValueError):
    pass


class TagNotFoundError(ValueError):
    pass


def _parse_posted_at(value: str) -> date:
    return date.fromisoformat(value[:10])


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

        if match_key:
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

            if apply_to_similar and bucket_id is not None:
                cur.execute(
                    """
                    SELECT id, amount, raw_description, description
                      FROM transactions
                     WHERE id != ?
                       AND bucket_id IS NULL
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


def set_tag(db: Database, transaction_id: str, *, tag_id: int | None) -> dict[str, Any]:
    if tag_id is not None and not tags_repo.tag_exists(db, tag_id):
        raise TagNotFoundError(f"tag_id inválido: {tag_id}")

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("SELECT id FROM transactions WHERE id=?", (transaction_id,))
        if cur.fetchone() is None:
            raise TransactionNotFoundError(transaction_id)

        cur.execute(
            "UPDATE transactions SET tag_id=? WHERE id=?",
            (tag_id, transaction_id),
        )

    return {"updated": 1, "tag_id": tag_id}
