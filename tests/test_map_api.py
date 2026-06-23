from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.web.app import create_app, get_db, get_pluggy


def _client(tmp_db, monkeypatch) -> TestClient:
    monkeypatch.setattr("src.web.app._background_sync", lambda *a, **kw: None)
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.mnt.load_family_profile",
        lambda: None,
    )

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

    def _override_pluggy():
        yield FakePluggy()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    return TestClient(app)


def test_investment_map_lists_light_country_payload(tmp_db, monkeypatch):
    client = _client(tmp_db, monkeypatch)

    response = client.get("/api/investments/map")

    assert response.status_code == 200
    countries = response.json()
    by_code = {country["code"]: country for country in countries}
    assert {"BR", "US", "DE", "IN", "RU"} <= set(by_code)
    assert by_code["BR"] == {
        "code": "BR",
        "name": "Brasil",
        "name_intl": "Brazil",
        "main_index": "Ibovespa",
        "tier": "medium",
        "tier_label": "Médio Risco",
        "color": "#F59E0B",
    }
    assert by_code["DE"]["tier"] == "top"
    assert set(by_code["US"]) == {
        "code",
        "name",
        "name_intl",
        "main_index",
        "tier",
        "tier_label",
        "color",
    }


def test_investment_map_country_detail_is_case_insensitive(tmp_db, monkeypatch):
    client = _client(tmp_db, monkeypatch)

    response = client.get("/api/investments/map/br")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "BR"
    assert body["name"] == "Brasil"
    assert body["name_intl"] == "Brazil"
    assert body["main_index"] == "Ibovespa"
    assert body["ratings"] == {"sp": "BB", "moody": "Ba2", "fitch": "BB-"}
    assert body["tier"] == "medium"
    assert body["tier_label"] == "Médio Risco"
    assert body["color"] == "#F59E0B"
    assert body["empresas"][0]["ticker"] == "VALE3"
    assert body["etfs"][0]["ticker"] == "BOVA11"


def test_investment_map_unknown_country_uses_error_envelope(tmp_db, monkeypatch):
    client = _client(tmp_db, monkeypatch)

    response = client.get("/api/investments/map/zz")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
