from __future__ import annotations

import base64
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.auth.sessions import SESSION_COOKIE_NAME, AuthSession
from src.web.app import create_app, get_db, get_pluggy


def _settings(*, session_auth_enabled: bool):
    return SimpleNamespace(
        app_user="familia",
        app_password="legacy-secret",
        auth_pepper="pepper",
        session_auth_enabled=session_auth_enabled,
        database_url="postgresql://deon_fin:test@postgres:5432/deon_fin",
        cors_origins=["http://localhost:3000"],
        auto_sync_on_start=False,
        auto_sync_minutes=0,
    )


def _basic_header() -> dict[str, str]:
    token = base64.b64encode(b"familia:legacy-secret").decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _client(monkeypatch, tmp_db, settings):
    monkeypatch.setattr("src.web.app.settings", settings)
    app = create_app()

    def _override_db():
        yield tmp_db

    class FakePluggy:
        def close(self):
            return None

    def _override_pluggy():
        yield FakePluggy()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    return TestClient(app)


def test_legacy_basic_auth_remains_default_when_session_auth_is_disabled(monkeypatch, tmp_db):
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=False))

    denied = client.get("/api/profile")
    allowed = client.get("/api/profile", headers=_basic_header())

    assert denied.status_code == 401
    assert denied.headers["www-authenticate"] == 'Basic realm="Raio-X Financeiro"'
    assert denied.json()["error"]["code"] == "unauthorized"
    assert allowed.status_code == 200


def test_session_auth_requires_valid_cookie_for_data_apis(monkeypatch, tmp_db):
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    missing = client.get("/api/profile")
    basic_only = client.get("/api/profile", headers=_basic_header())

    assert missing.status_code == 401
    assert "www-authenticate" not in missing.headers
    assert missing.json()["error"]["code"] == "session_required"
    assert basic_only.status_code == 401
    assert basic_only.json()["error"]["code"] == "session_required"


def test_session_auth_allows_data_api_with_valid_cookie(monkeypatch, tmp_db):
    def fake_session_from_request(request):
        if request.cookies.get(SESSION_COOKIE_NAME) != "raw-token":
            return None
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
        "src.web.app._session_from_request",
        fake_session_from_request,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.get("/api/profile", cookies={SESSION_COOKIE_NAME: "raw-token"})

    assert response.status_code == 200
    assert response.json()["initials"] == "?"


def test_session_auth_reports_configuration_error(monkeypatch, tmp_db):
    settings = _settings(session_auth_enabled=True)
    settings.auth_pepper = None
    client = _client(monkeypatch, tmp_db, settings)

    response = client.get("/api/profile", cookies={SESSION_COOKIE_NAME: "raw-token"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "session_auth_unavailable"


def test_session_auth_allows_login_page_without_legacy_basic_auth(
    monkeypatch,
    tmp_path,
    tmp_db,
):
    web_dist = tmp_path / "web_dist"
    login_dir = web_dist / "login"
    login_dir.mkdir(parents=True)
    (web_dist / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
    (login_dir / "index.html").write_text("<html>login marker</html>", encoding="utf-8")
    monkeypatch.setenv("WEB_DIST_DIR", str(web_dist))

    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.get("/login")

    assert response.status_code == 200
    assert "login marker" in response.text


def test_session_auth_redirects_protected_html_to_login(monkeypatch, tmp_path, tmp_db):
    web_dist = tmp_path / "web_dist"
    web_dist.mkdir()
    (web_dist / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
    monkeypatch.setenv("WEB_DIST_DIR", str(web_dist))
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.get("/metas", follow_redirects=False)

    assert response.status_code in {303, 307}
    assert response.headers["location"] == "/login"


def test_session_auth_allows_protected_html_with_valid_cookie(monkeypatch, tmp_path, tmp_db):
    def fake_session_from_request(request):
        if request.cookies.get(SESSION_COOKIE_NAME) != "raw-token":
            return None
        return AuthSession(
            session_id="session-1",
            user_id="user-1",
            email="davi@example.com",
            display_name="Davi",
            family_id="family-1",
            family_name="Familia Principal",
            family_role="owner",
        )

    web_dist = tmp_path / "web_dist"
    metas_dir = web_dist / "metas"
    metas_dir.mkdir(parents=True)
    (web_dist / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
    (metas_dir / "index.html").write_text("<html>metas marker</html>", encoding="utf-8")
    monkeypatch.setenv("WEB_DIST_DIR", str(web_dist))
    monkeypatch.setattr(
        "src.web.app._session_from_request",
        fake_session_from_request,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.get("/metas", cookies={SESSION_COOKIE_NAME: "raw-token"})

    assert response.status_code == 200
    assert "metas marker" in response.text


def test_session_auth_keeps_static_assets_public(monkeypatch, tmp_path, tmp_db):
    calls = []

    def fail_if_called(request):
        calls.append(request.url.path)
        return None

    web_dist = tmp_path / "web_dist"
    web_dist.mkdir()
    (web_dist / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
    (web_dist / "world.geo.json").write_text('{"type":"FeatureCollection"}', encoding="utf-8")
    monkeypatch.setenv("WEB_DIST_DIR", str(web_dist))
    monkeypatch.setattr(
        "src.web.app._session_from_request",
        fail_if_called,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.get("/world.geo.json")

    assert response.status_code == 200
    assert calls == []


def test_session_auth_keeps_auth_me_route_owned(monkeypatch, tmp_db):
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "unauthorized",
        "message": "Not authenticated",
    }


def test_session_auth_allows_options_preflight(monkeypatch, tmp_db):
    calls = []

    def fail_if_called(request):
        calls.append(request.url.path)
        return None

    monkeypatch.setattr(
        "src.web.app._session_from_request",
        fail_if_called,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.options(
        "/api/profile",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert calls == []


def test_session_auth_rejects_unsafe_request_without_origin(monkeypatch, tmp_db):
    def fake_session_from_request(request):
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
        "src.web.app._session_from_request",
        fake_session_from_request,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.put(
        "/api/profile",
        cookies={SESSION_COOKIE_NAME: "raw-token"},
        json={
            "name": "Davi Alves",
            "email": "davi@example.com",
            "monthly_income": 1000,
            "financial_month_start_day": 1,
            "goals_text": "",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_origin"


def test_session_auth_rejects_foreign_origin_for_unsafe_request(monkeypatch, tmp_db):
    def fake_session_from_request(request):
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
        "src.web.app._session_from_request",
        fake_session_from_request,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.put(
        "/api/profile",
        headers={"Origin": "https://evil.example"},
        cookies={SESSION_COOKIE_NAME: "raw-token"},
        json={
            "name": "Davi Alves",
            "email": "davi@example.com",
            "monthly_income": 1000,
            "financial_month_start_day": 1,
            "goals_text": "",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_origin"


def test_session_auth_allows_configured_origin_for_unsafe_request(monkeypatch, tmp_db):
    def fake_session_from_request(request):
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
        "src.web.app._session_from_request",
        fake_session_from_request,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.put(
        "/api/profile",
        headers={"Origin": "http://localhost:3000"},
        cookies={SESSION_COOKIE_NAME: "raw-token"},
        json={
            "name": "Davi Alves",
            "email": "davi@example.com",
            "monthly_income": 1000,
            "financial_month_start_day": 1,
            "goals_text": "",
        },
    )

    assert response.status_code == 200
    assert response.json()["saved"] is True


def test_session_auth_allows_same_origin_referer_for_unsafe_request(monkeypatch, tmp_db):
    def fake_session_from_request(request):
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
        "src.web.app._session_from_request",
        fake_session_from_request,
        raising=False,
    )
    client = _client(monkeypatch, tmp_db, _settings(session_auth_enabled=True))

    response = client.put(
        "/api/profile",
        headers={"Referer": "http://testserver/perfil"},
        cookies={SESSION_COOKIE_NAME: "raw-token"},
        json={
            "name": "Davi Alves",
            "email": "davi@example.com",
            "monthly_income": 1000,
            "financial_month_start_day": 1,
            "goals_text": "",
        },
    )

    assert response.status_code == 200
    assert response.json()["saved"] is True
