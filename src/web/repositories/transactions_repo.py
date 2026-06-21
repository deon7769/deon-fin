from __future__ import annotations

from datetime import date

from ...storage import Database
from ...storage.reference_month import reference_month


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
