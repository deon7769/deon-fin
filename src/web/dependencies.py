from __future__ import annotations

from collections.abc import Generator

from fastapi import HTTPException

from ..config import settings
from ..pluggy import PluggyClient
from ..storage import Database
from ..storage.postgres import connect_postgres


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


def get_postgres_conn():
    try:
        with connect_postgres(settings.database_url) as conn:
            yield conn
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL DATABASE_URL required for session authentication",
        ) from exc
