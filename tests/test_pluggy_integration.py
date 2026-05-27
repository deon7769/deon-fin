from __future__ import annotations

import os

import pytest

from src.pluggy import PluggyClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> PluggyClient:
    c = PluggyClient(
        os.environ["PLUGGY_CLIENT_ID"],
        os.environ["PLUGGY_CLIENT_SECRET"],
    )
    yield c
    c.close()


def test_authenticate_returns_apikey(client):
    api_key = client.authenticate()
    assert api_key and api_key.count(".") == 2, "should be a JWT"


def test_list_sandbox_connectors(client):
    connectors = client.list_connectors(sandbox=True, countries=["BR"])
    assert len(connectors) > 0
    sample = connectors[0]
    for field in ("id", "name", "type", "country"):
        assert field in sample, f"missing field {field} in connector payload"


def test_list_categories(client):
    cats = client.list_categories()
    assert isinstance(cats, list)


def test_create_connect_token(client):
    token = client.create_connect_token(client_user_id="test-user-validate")
    assert token and token.count(".") == 2
