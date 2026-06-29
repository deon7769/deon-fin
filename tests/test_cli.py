from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from typer.testing import CliRunner

from src import cli
from src.storage import Account, Database, Transaction


def test_pg_migration_dry_run_command_prints_counts(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy-cli.db"
    db = Database(db_path)
    db.upsert_account(Account(id="acc-1", source="csv"))
    db.close()

    monkeypatch.setattr(cli, "settings", SimpleNamespace(database_path=db_path))

    result = CliRunner().invoke(cli.app, ["pg-migration-dry-run"])

    assert result.exit_code == 0
    assert "Família padrão" in result.output
    assert "accounts" in result.output
    assert "1" in result.output


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
            category="Food Delivery",
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
    row = check._conn.execute(
        "SELECT reference_month, tag_id, tag_source FROM transactions"
    ).fetchone()
    tag = check._conn.execute("SELECT name FROM tags WHERE id=?", (row["tag_id"],)).fetchone()
    assert row["reference_month"] == "2026-05"
    assert row["tag_source"] == "auto"
    assert tag["name"] == "Delivery"
    check.close()


def test_bootstrap_auth_command_runs_migrations_and_bootstrap(monkeypatch):
    calls = []

    class FakeConnection:
        pass

    class FakeConnectionContext:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_run_migrations(database_url):
        calls.append(("migrate", database_url))

    def fake_connect(database_url):
        calls.append(("connect", database_url))
        return FakeConnectionContext()

    def fake_bootstrap(conn, data):
        calls.append(("bootstrap", data.email, data.family_slug))
        return SimpleNamespace(user_id="user-1", family_id="family-1", person_id="person-1")

    monkeypatch.setattr(cli, "settings", SimpleNamespace(database_url="postgresql://u:p@localhost/db"))
    monkeypatch.setattr(cli, "run_postgres_migrations", fake_run_migrations)
    monkeypatch.setattr(cli, "connect_postgres", fake_connect)
    monkeypatch.setattr(cli, "bootstrap_admin_family", fake_bootstrap)

    result = CliRunner().invoke(
        cli.app,
        [
            "bootstrap-auth",
            "--email",
            "davi@example.com",
            "--display-name",
            "Davi",
            "--family-name",
            "Familia Principal",
            "--family-slug",
            "familia-principal",
        ],
        input="strong-password\nstrong-password\n",
    )

    assert result.exit_code == 0
    assert "Bootstrap concluído" in result.output
    assert calls == [
        ("migrate", "postgresql://u:p@localhost/db"),
        ("connect", "postgresql://u:p@localhost/db"),
        ("bootstrap", "davi@example.com", "familia-principal"),
    ]
