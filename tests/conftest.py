from __future__ import annotations

import os
from pathlib import Path

import pytest

# Capture real shell-provided Pluggy credentials before test placeholders are
# installed. Values loaded only from .env should not make integration tests run.
_HAS_REAL_PLUGGY_ENV_CREDS = bool(
    os.environ.get("PLUGGY_CLIENT_ID") and os.environ.get("PLUGGY_CLIENT_SECRET")
)

# src.config loads .env on import with override=False. These values must exist
# before tests import src.web.app, otherwise production .env can leak into unit
# tests and enable Basic Auth/autosync. This does not create another env file;
# it only scopes harmless defaults to the pytest process.
os.environ.setdefault("PLUGGY_CLIENT_ID", "test-client-id")
os.environ.setdefault("PLUGGY_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///data/test-suite.db")
os.environ["APP_PASSWORD"] = ""
os.environ["AUTO_SYNC_ON_START"] = "false"
os.environ["AUTO_SYNC_MINUTES"] = "0"

from src.storage import Database


@pytest.fixture
def tmp_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    yield db
    db.close()


def pytest_collection_modifyitems(config, items):
    if not _HAS_REAL_PLUGGY_ENV_CREDS:
        skip = pytest.mark.skip(reason="Pluggy credentials not configured")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
