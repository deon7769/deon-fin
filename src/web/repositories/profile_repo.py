from __future__ import annotations

from typing import Any

from ...storage import Database


def get_profile(db: Database) -> dict[str, Any]:
    db._conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")
    db._conn.commit()
    row = db._conn.execute(
        """
        SELECT id, name, email, monthly_income, financial_month_start_day,
               goals_text, updated_at
          FROM profile
         WHERE id = 1
        """
    ).fetchone()
    return dict(row)
