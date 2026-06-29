from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest

from src.storage.postgres import (
    require_postgres_dsn,
    run_postgres_migrations,
    sqlalchemy_url,
)


def _load_migration_env():
    sys.modules.pop("src.storage.postgres_migrations.env", None)
    return importlib.import_module("src.storage.postgres_migrations.env")


def test_require_postgres_dsn_accepts_postgresql_url():
    assert (
        require_postgres_dsn("postgresql://u:p@localhost/db")
        == "postgresql://u:p@localhost/db"
    )


def test_require_postgres_dsn_accepts_psycopg_url_as_postgresql_dsn():
    assert (
        require_postgres_dsn("postgresql+psycopg://u:p@localhost/db")
        == "postgresql://u:p@localhost/db"
    )


def test_require_postgres_dsn_rejects_sqlite_url():
    with pytest.raises(ValueError, match="PostgreSQL DATABASE_URL required"):
        require_postgres_dsn("sqlite:///data/financas.db")


def test_sqlalchemy_url_converts_postgres_alias_to_psycopg():
    assert (
        sqlalchemy_url("postgres://u:p@localhost/db")
        == "postgresql+psycopg://u:p@localhost/db"
    )


def test_run_postgres_migrations_passes_config_to_alembic(monkeypatch):
    calls = []

    class FakeConfig:
        def __init__(self, path):
            self.path = str(path)
            self.attributes = {}

        def set_main_option(self, key, value):
            calls.append((key, value))

    def fake_upgrade(config, revision):
        calls.append(("upgrade", revision, config.path))

    monkeypatch.setattr("src.storage.postgres.Config", FakeConfig)
    monkeypatch.setattr(
        "src.storage.postgres.command", SimpleNamespace(upgrade=fake_upgrade)
    )

    run_postgres_migrations("postgresql://u:p@localhost/db")

    assert ("sqlalchemy.url", "postgresql+psycopg://u:p@localhost/db") in calls
    assert any(call[0] == "upgrade" and call[1] == "head" for call in calls)


def test_run_postgres_migrations_passes_revision_to_alembic(monkeypatch):
    calls = []

    class FakeConfig:
        def __init__(self, path):
            self.path = str(path)
            self.attributes = {}

        def set_main_option(self, key, value):
            calls.append((key, value))

    def fake_upgrade(config, revision):
        calls.append(("upgrade", revision, config.path))

    monkeypatch.setattr("src.storage.postgres.Config", FakeConfig)
    monkeypatch.setattr(
        "src.storage.postgres.command", SimpleNamespace(upgrade=fake_upgrade)
    )

    run_postgres_migrations("postgresql://u:p@localhost/db", revision="base")

    assert any(call[0] == "upgrade" and call[1] == "base" for call in calls)


def test_migration_env_database_url_prefers_configured_sqlalchemy_url(monkeypatch):
    env = _load_migration_env()

    class FakeConfig:
        def get_main_option(self, key):
            assert key == "sqlalchemy.url"
            return "postgresql://cfg:p@localhost/config_db"

    monkeypatch.setattr(env, "config", FakeConfig())
    monkeypatch.setenv("DATABASE_URL", "postgresql://env:p@localhost/env_db")

    assert env._database_url() == "postgresql+psycopg://cfg:p@localhost/config_db"


def test_migration_env_database_url_falls_back_to_environment(monkeypatch):
    env = _load_migration_env()

    class FakeConfig:
        def get_main_option(self, key):
            assert key == "sqlalchemy.url"
            return ""

    monkeypatch.setattr(env, "config", FakeConfig())
    monkeypatch.setenv("DATABASE_URL", "postgres://env:p@localhost/env_db")

    assert env._database_url() == "postgresql+psycopg://env:p@localhost/env_db"
