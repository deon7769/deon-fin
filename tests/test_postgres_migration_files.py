from __future__ import annotations

import subprocess
import sys
from pathlib import Path


MIGRATION = Path(
    "src/storage/postgres_migrations/versions/0001_multi_family_foundation.py"
)


def test_alembic_files_exist():
    assert Path("alembic.ini").is_file()
    assert Path("src/storage/postgres_migrations/env.py").is_file()
    assert Path("src/storage/postgres_migrations/script.py.mako").is_file()
    assert MIGRATION.is_file()


def test_foundation_migration_creates_required_tables():
    source = MIGRATION.read_text(encoding="utf-8")

    for table in (
        "users",
        "user_identities",
        "families",
        "family_members",
        "family_people",
        "sessions",
        "login_attempts",
        "user_security_state",
        "provider_connections",
        "accounts",
        "account_people",
        "tags",
        "budget_buckets",
        "savings_goals",
        "transactions",
        "transaction_links",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in source


def test_foundation_migration_creates_required_indexes():
    source = MIGRATION.read_text(encoding="utf-8")

    for index in (
        "idx_family_members_user_family",
        "idx_provider_connections_family_provider_item",
        "idx_accounts_family_source_external",
        "idx_transactions_family_account_posted",
        "idx_transactions_family_reference_month",
        "idx_transaction_links_family_source",
        "idx_login_attempts_email_created",
        "idx_login_attempts_ip_created",
        "idx_sessions_token_hash",
    ):
        assert index in source


def test_foundation_migration_uses_jsonb_and_citext():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS citext" in source
    assert "jsonb" in source
    assert "citext" in source


def test_foundation_migration_enforces_family_scoped_transaction_refs():
    source = MIGRATION.read_text(encoding="utf-8")

    for foreign_key in (
        "FOREIGN KEY (family_id, tag_id) REFERENCES tags(family_id, id)",
        "FOREIGN KEY (family_id, bucket_id) REFERENCES budget_buckets(family_id, id)",
        "FOREIGN KEY (family_id, savings_goal_id) REFERENCES savings_goals(family_id, id)",
    ):
        assert foreign_key in source


def test_alembic_heads_finds_foundation_revision():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "0001_multi_family_foundation" in result.stdout


def test_transactions_keep_legacy_text_primary_key():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "id text PRIMARY KEY" in source
