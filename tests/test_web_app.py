from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app, get_db, get_pluggy


@pytest.fixture
def client(tmp_db, monkeypatch):
    # Por padrão, neutraliza o sync em background pra evitar chamadas reais ao
    # Pluggy nos testes. Testes que quiserem checar o agendamento podem
    # patchar src.web.app._background_sync localmente.
    monkeypatch.setattr("src.web.app._background_sync", lambda *a, **kw: None)

    app = create_app()

    def _override_db():
        yield tmp_db

    class FakePluggy:
        def create_connect_token(self, *, client_user_id=None, item_id=None):
            return "fake.connect.token"

        def delete_item(self, item_id):
            return None

        def close(self):
            return None

    fake = FakePluggy()

    def _override_pluggy():
        yield fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_index_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Pluggy Connect" in r.text
    assert 'src="https://cdn.pluggy.ai/pluggy-connect/' in r.text


def test_create_connect_token(client):
    r = client.post("/api/connect-token", json={"client_user_id": "u1"})
    assert r.status_code == 200
    assert r.json() == {"accessToken": "fake.connect.token"}


def test_register_item_schedules_sync(client, monkeypatch):
    from unittest.mock import MagicMock
    spy = MagicMock(return_value=None)
    monkeypatch.setattr("src.web.app._background_sync", spy)

    r = client.post("/api/items", json={
        "item_id": "item-123",
        "connector_id": 201,
        "connector_name": "Nubank",
        "status": "UPDATED",
    })
    assert r.status_code == 200
    assert r.json()["sync_scheduled"] is True
    spy.assert_called_once_with("item-123", 90)

    items = client.get("/api/items").json()
    assert any(i["id"] == "item-123" for i in items)


def test_sync_unknown_item_returns_404(client):
    r = client.post("/api/items/missing/sync", json={"days": 30})
    assert r.status_code == 404


def test_delete_item(client):
    client.post("/api/items", json={"item_id": "item-del", "connector_name": "X"})
    r = client.delete("/api/items/item-del")
    assert r.status_code == 200
    assert client.get("/api/items").json() == []


def test_summary_empty(client):
    s = client.get("/api/summary?days=30").json()
    assert s["transactions"] == 0
    assert s["inflow"] == 0.0
    assert s["outflow"] == 0.0
    assert s["by_category"] == []
