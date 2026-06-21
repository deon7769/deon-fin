from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.web.app import create_app


def _write_next_export(root: Path) -> Path:
    web_dist = root / "web_dist"
    (web_dist / "_next" / "static").mkdir(parents=True)
    (web_dist / "metas").mkdir(parents=True)
    (web_dist / "index.html").write_text(
        """
        <!doctype html>
        <html>
          <head><title>deon-fin</title></head>
          <body data-app="deon-fin-next">
            <div id="__next">Next shell</div>
            <script src="/_next/static/app.js"></script>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (web_dist / "metas" / "index.html").write_text(
        """
        <!doctype html>
        <html>
          <body data-app="deon-fin-next" data-route="metas">
            <div id="__next">Metas export</div>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    (web_dist / "_next" / "static" / "app.js").write_text(
        "window.__DEON_FIN_NEXT__ = true;",
        encoding="utf-8",
    )
    return web_dist


def _client_with_export(tmp_path: Path, monkeypatch) -> TestClient:
    web_dist = _write_next_export(tmp_path)
    monkeypatch.setenv("WEB_DIST_DIR", str(web_dist))
    monkeypatch.delenv("LEGACY_UI", raising=False)
    return TestClient(create_app())


def test_root_serves_next_export_when_available(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert 'data-app="deon-fin-next"' in response.text
    assert "/_next/static/app.js" in response.text
    assert "Pluggy Connect" not in response.text


def test_deep_route_serves_exported_route_or_spa_shell(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    response = client.get("/metas?month=2026-06")

    assert response.status_code == 200
    assert 'data-app="deon-fin-next"' in response.text
    assert "Metas export" in response.text


def test_head_requests_are_supported_for_next_export_routes(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    for path in ["/", "/metas", "/simulador", "/transacoes/?month=2026-06"]:
        response = client.head(path)
        assert response.status_code == 200
        assert response.text == ""


def test_next_asset_is_served_from_export(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    response = client.get("/_next/static/app.js")

    assert response.status_code == 200
    assert "window.__DEON_FIN_NEXT__ = true" in response.text


def test_api_routes_keep_precedence_over_spa_fallback(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    health = client.get("/api/health")
    missing = client.get("/api/does-not-exist")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/json")
    assert missing.json()["error"]["code"] == "not_found"


def test_legacy_static_assets_keep_precedence(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert len(response.text) > 100


def test_legacy_route_renders_old_pluggy_ui(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    response = client.get("/legacy")

    assert response.status_code == 200
    assert "Pluggy Connect" in response.text
    assert 'src="https://cdn.pluggy.ai/pluggy-connect/' in response.text


def test_legacy_ui_toggle_restores_old_root(tmp_path, monkeypatch):
    web_dist = _write_next_export(tmp_path)
    monkeypatch.setenv("WEB_DIST_DIR", str(web_dist))
    monkeypatch.setenv("LEGACY_UI", "1")
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Pluggy Connect" in response.text
    assert 'data-app="deon-fin-next"' not in response.text


def test_root_falls_back_to_legacy_when_export_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("WEB_DIST_DIR", str(tmp_path / "missing-web-dist"))
    monkeypatch.delenv("LEGACY_UI", raising=False)
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Pluggy Connect" in response.text
