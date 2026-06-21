from __future__ import annotations

from collections.abc import Generator

from ..config import settings
from ..pluggy import PluggyClient
from ..storage import Database


def get_db() -> Generator[Database, None, None]:
    db = Database(settings.database_path)
    try:
        yield db
    finally:
        db.close()


def get_pluggy() -> Generator[PluggyClient, None, None]:
    client = PluggyClient(settings.client_id, settings.client_secret)
    try:
        yield client
    finally:
        client.close()
