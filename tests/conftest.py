from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.storage import Database


@pytest.fixture
def tmp_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    yield db
    db.close()


def pytest_collection_modifyitems(config, items):
    if not (os.environ.get("PLUGGY_CLIENT_ID") and os.environ.get("PLUGGY_CLIENT_SECRET")):
        skip = pytest.mark.skip(reason="Pluggy credentials not configured")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
