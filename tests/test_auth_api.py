from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.auth.account import AccountUpdateResult
from src.auth.sessions import AuthSession, LoginResult
from src.web.app import create_app
from src.web.dependencies import get_postgres_conn
from src.web.routers import auth as auth_router


class FakeAuthConnection:
    pass


def _override_postgres_conn():
    yield FakeAuthConnection()


def test_login_endpoint_sets_httponly_session_cookie(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn

    def fake_authenticate(conn, data):
        assert isinstance(conn, FakeAuthConnection)
        assert data.email == "davi@example.com"
        assert data.password == "secret"
        assert data.pepper == "pepper"
        return LoginResult(
            session_id="session-1",
            session_token="raw-token",
            user_id="user-1",
            email="davi@example.com",
            display_name="Davi",
            family_id="family-1",
            family_name="Familia Principal",
            family_role="owner",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(auth_pepper="pepper"),
    )
    monkeypatch.setattr("src.web.routers.auth.authenticate_login", fake_authenticate)

    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"email": "davi@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "davi@example.com"
    assert response.json()["family"]["id"] == "family-1"
    cookie = response.headers["set-cookie"]
    assert "deon_session=raw-token" in cookie
    assert "deon_session_present=1" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_login_endpoint_blocks_multi_family_session_mode_while_financial_data_is_sqlite(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn

    def fake_authenticate(conn, data):
        return LoginResult(
            session_id="session-1",
            session_token="raw-token",
            user_id="user-1",
            email=data.email,
            display_name="Davi",
            family_id="family-2",
            family_name="Outra Familia",
            family_role="owner",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

    def fake_guard(conn, *, financial_database_url, requested_family_slug=None):
        assert financial_database_url == "sqlite:///data/financas.db"
        raise auth_router.MultiFamilySQLiteGuardError(
            "Modo multi-familia bloqueado enquanto os dados financeiros usam SQLite."
        )

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(
            auth_pepper="pepper",
            database_url="sqlite:///data/financas.db",
            auth_database_url="postgresql://u:p@localhost/auth_db",
        ),
    )
    monkeypatch.setattr("src.web.routers.auth.authenticate_login", fake_authenticate)
    monkeypatch.setattr("src.web.routers.auth.enforce_sqlite_single_family_mode", fake_guard)

    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"email": "davi@example.com", "password": "secret"},
    )

    assert response.status_code == 503
    assert "SQLite" in response.json()["error"]["message"]


def test_login_endpoint_ignores_forwarded_for_from_untrusted_client(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn
    seen = []

    def fake_authenticate(conn, data):
        seen.append(data.ip_address)
        return LoginResult(
            session_id="session-1",
            session_token="raw-token",
            user_id="user-1",
            email=data.email,
            display_name="Davi",
            family_id="family-1",
            family_name="Familia Principal",
            family_role="owner",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(
            auth_pepper="pepper",
            database_url="postgresql://u:p@localhost/auth_db",
            trusted_proxy_ips=[],
        ),
    )
    monkeypatch.setattr("src.web.routers.auth.authenticate_login", fake_authenticate)

    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": "203.0.113.10"},
        json={"email": "davi@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert seen == ["testclient"]


def test_login_endpoint_trusts_forwarded_for_from_configured_proxy(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn
    seen = []

    def fake_authenticate(conn, data):
        seen.append(data.ip_address)
        return LoginResult(
            session_id="session-1",
            session_token="raw-token",
            user_id="user-1",
            email=data.email,
            display_name="Davi",
            family_id="family-1",
            family_name="Familia Principal",
            family_role="owner",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(
            auth_pepper="pepper",
            database_url="postgresql://u:p@localhost/auth_db",
            trusted_proxy_ips=["testclient"],
        ),
    )
    monkeypatch.setattr("src.web.routers.auth.authenticate_login", fake_authenticate)

    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": "203.0.113.10, 198.51.100.7"},
        json={"email": "davi@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert seen == ["203.0.113.10"]


def test_auth_login_bypasses_legacy_basic_auth(monkeypatch):
    monkeypatch.setattr(
        "src.web.app.settings",
        SimpleNamespace(
            cors_origins=["http://localhost:3000"],
            app_user="familia",
            app_password="legacy-secret",
            auto_sync_on_start=False,
            auto_sync_minutes=0,
        ),
    )
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn

    def fake_authenticate(conn, data):
        return LoginResult(
            session_id="session-1",
            session_token="raw-token",
            user_id="user-1",
            email=data.email,
            display_name="Davi",
            family_id="family-1",
            family_name="Familia Principal",
            family_role="owner",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(auth_pepper="pepper"),
    )
    monkeypatch.setattr("src.web.routers.auth.authenticate_login", fake_authenticate)

    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"email": "davi@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def test_me_endpoint_reads_session_cookie(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn

    def fake_current_session(token, *, pepper, now=None):
        assert token == "raw-token"
        assert pepper == "pepper"
        return AuthSession(
            session_id="session-1",
            user_id="user-1",
            email="davi@example.com",
            display_name="Davi",
            family_id="family-1",
            family_name="Familia Principal",
            family_role="owner",
        )

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(auth_pepper="pepper"),
    )
    monkeypatch.setattr("src.web.routers.auth._current_session_for_token", fake_current_session)

    client = TestClient(app)
    response = client.get("/api/auth/me", cookies={"deon_session": "raw-token"})

    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.json()["user"]["id"] == "user-1"
    assert response.json()["family"]["role"] == "owner"


def test_update_account_endpoint_uses_session_and_returns_updated_user(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn
    calls = []

    def fake_current_session(token, *, pepper, now=None):
        assert token == "raw-token"
        assert pepper == "pepper"
        return AuthSession(
            session_id="session-1",
            user_id="user-1",
            email="davi@example.com",
            display_name="Davi",
            family_id="family-1",
            family_name="Familia Principal",
            family_role="owner",
        )

    def fake_update_account(user_id, payload, *, now=None):
        calls.append((user_id, payload.email, payload.current_password, payload.new_password))
        return AccountUpdateResult(
            user_id="user-1",
            email="novo@example.com",
            display_name="Davi",
        )

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(auth_pepper="pepper"),
    )
    monkeypatch.setattr("src.web.routers.auth._current_session_for_token", fake_current_session)
    monkeypatch.setattr("src.web.routers.auth._update_account_credentials", fake_update_account)

    client = TestClient(app)
    response = client.patch(
        "/api/auth/me",
        cookies={"deon_session": "raw-token"},
        json={
            "email": " Novo@Example.COM ",
            "current_password": "senha atual",
            "new_password": "senha nova forte",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "novo@example.com"
    assert response.json()["family"]["id"] == "family-1"
    assert calls == [("user-1", " Novo@Example.COM ", "senha atual", "senha nova forte")]


def test_logout_endpoint_revokes_session_and_clears_cookie(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_postgres_conn] = _override_postgres_conn
    calls = []

    def fake_revoke_session(token, *, pepper, now=None):
        calls.append((token, pepper))

    monkeypatch.setattr(
        "src.web.routers.auth.settings",
        SimpleNamespace(auth_pepper="pepper"),
    )
    monkeypatch.setattr("src.web.routers.auth._revoke_session_token", fake_revoke_session)

    client = TestClient(app)
    response = client.post("/api/auth/logout", cookies={"deon_session": "raw-token"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls == [("raw-token", "pepper")]
    cookie = response.headers["set-cookie"]
    assert "deon_session=" in cookie
    assert "deon_session_present=" in cookie


def test_auth_session_helpers_use_auth_database_url(monkeypatch):
    calls = []

    class FakePostgresContext:
        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_connect_postgres(database_url):
        calls.append(("connect", database_url))
        return FakePostgresContext()

    def fake_current_session(conn, token, *, pepper, now=None):
        calls.append(("current", token, pepper))
        return None

    def fake_revoke_session(conn, token, *, pepper, now=None):
        calls.append(("revoke", token, pepper))

    monkeypatch.setattr(
        auth_router,
        "settings",
        SimpleNamespace(
            database_url="sqlite:///data/financas.db",
            auth_database_url="postgresql://auth-user:secret@postgres:5432/auth_db",
        ),
    )
    monkeypatch.setattr(auth_router, "connect_postgres", fake_connect_postgres)
    monkeypatch.setattr(auth_router, "current_session", fake_current_session)
    monkeypatch.setattr(auth_router, "revoke_session", fake_revoke_session)

    auth_router._current_session_for_token("raw-token", pepper="pepper", now=datetime.now(UTC))
    auth_router._revoke_session_token("raw-token", pepper="pepper", now=datetime.now(UTC))

    assert calls == [
        ("connect", "postgresql://auth-user:secret@postgres:5432/auth_db"),
        ("current", "raw-token", "pepper"),
        ("connect", "postgresql://auth-user:secret@postgres:5432/auth_db"),
        ("revoke", "raw-token", "pepper"),
    ]
