from __future__ import annotations

from types import SimpleNamespace

from src.web.dependencies import get_postgres_conn


def test_get_postgres_conn_uses_auth_database_url(monkeypatch):
    calls = []
    fake_conn = object()

    class FakePostgresContext:
        def __enter__(self):
            return fake_conn

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_connect_postgres(database_url):
        calls.append(database_url)
        return FakePostgresContext()

    monkeypatch.setattr(
        "src.web.dependencies.settings",
        SimpleNamespace(
            database_url="sqlite:///data/financas.db",
            auth_database_url="postgresql://auth-user:secret@postgres:5432/auth_db",
        ),
    )
    monkeypatch.setattr("src.web.dependencies.connect_postgres", fake_connect_postgres)

    dependency = get_postgres_conn()
    conn = next(dependency)

    assert conn is fake_conn
    assert calls == ["postgresql://auth-user:secret@postgres:5432/auth_db"]
