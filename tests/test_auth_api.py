from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.auth.sessions import AuthSession, LoginResult
from src.web.app import create_app
from src.web.dependencies import get_postgres_conn


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
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


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
    assert "deon_session=" in response.headers["set-cookie"]
