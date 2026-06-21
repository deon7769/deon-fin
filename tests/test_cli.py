from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from typer.testing import CliRunner

from src import cli
from src.storage import Account, Database, Transaction


def test_recompute_reference_month_command_uses_profile_start_day(tmp_path, monkeypatch):
    db_path = tmp_path / "cli.db"
    db = Database(db_path)
    db.upsert_account(Account(id="acc-1", source="csv", type="CHECKING"))
    db.insert_transactions(
        [
            Transaction(
                account_id="acc-1",
                posted_at=date(2026, 6, 14),
                amount=Decimal("-10.00"),
                description="Before cycle",
                source="csv",
            ),
            Transaction(
                account_id="acc-1",
                posted_at=date(2026, 6, 15),
                amount=Decimal("-20.00"),
                description="Cycle start",
                source="csv",
            ),
        ]
    )
    db._conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")
    db._conn.execute(
        "UPDATE profile SET financial_month_start_day=15 WHERE id=1"
    )
    db._conn.commit()
    db.close()

    monkeypatch.setattr(cli, "settings", SimpleNamespace(database_path=db_path))

    result = CliRunner().invoke(cli.app, ["recompute-reference-month"])

    assert result.exit_code == 0
    assert "2 transação(ões)" in result.output

    check = Database(db_path)
    rows = check._conn.execute(
        "SELECT posted_at, reference_month FROM transactions ORDER BY posted_at"
    ).fetchall()
    assert [(row[0], row[1]) for row in rows] == [
        ("2026-06-14", "2026-05"),
        ("2026-06-15", "2026-06"),
    ]
    check.close()


def test_categorize_command_fills_missing_reference_months(tmp_path, monkeypatch):
    db_path = tmp_path / "categorize.db"
    db = Database(db_path)
    db.upsert_account(Account(id="acc-1", source="csv", type="CHECKING"))
    db.insert_transactions([
        Transaction(
            account_id="acc-1",
            posted_at=date(2026, 6, 14),
            amount=Decimal("-10.00"),
            description="Before cycle",
            source="csv",
        )
    ])
    db._conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")
    db._conn.execute(
        "UPDATE profile SET financial_month_start_day=15 WHERE id=1"
    )
    db._conn.commit()
    db.close()

    class FakeCategorizer:
        def apply_to_database(self, db):
            return {"updated": 0}

    monkeypatch.setattr(cli, "settings", SimpleNamespace(database_path=db_path))
    monkeypatch.setattr(cli, "Categorizer", FakeCategorizer)

    result = CliRunner().invoke(cli.app, ["categorize"])

    assert result.exit_code == 0

    check = Database(db_path)
    value = check._conn.execute(
        "SELECT reference_month FROM transactions"
    ).fetchone()[0]
    assert value == "2026-05"
    check.close()
