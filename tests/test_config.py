from __future__ import annotations

from src.config import load_settings


def _base_env(monkeypatch):
    monkeypatch.setenv("PLUGGY_CLIENT_ID", "client")
    monkeypatch.setenv("PLUGGY_CLIENT_SECRET", "secret")
    monkeypatch.delenv("AUTH_DATABASE_URL", raising=False)


def test_auth_database_url_defaults_to_main_database_url(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/financas.db")

    settings = load_settings()

    assert settings.database_url == "sqlite:///data/financas.db"
    assert settings.auth_database_url == "sqlite:///data/financas.db"


def test_auth_database_url_can_point_to_postgres_while_main_database_stays_sqlite(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/financas.db")
    monkeypatch.setenv(
        "AUTH_DATABASE_URL",
        "postgresql://deon_fin:secret@postgres:5432/deon_fin",
    )

    settings = load_settings()

    assert settings.database_url == "sqlite:///data/financas.db"
    assert settings.auth_database_url == "postgresql://deon_fin:secret@postgres:5432/deon_fin"
