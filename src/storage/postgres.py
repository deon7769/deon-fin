from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from alembic import command
from alembic.config import Config

from .database_url import DatabaseKind, parse_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def require_postgres_dsn(database_url: str) -> str:
    try:
        parsed = parse_database_url(database_url, project_root=PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError("PostgreSQL DATABASE_URL required") from exc

    if parsed.kind != DatabaseKind.POSTGRES or parsed.postgres_dsn is None:
        raise ValueError("PostgreSQL DATABASE_URL required")

    return parsed.postgres_dsn


def sqlalchemy_url(database_url: str) -> str:
    dsn = require_postgres_dsn(database_url)
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgres://")
    raise ValueError("PostgreSQL DATABASE_URL required")


@contextmanager
def connect_postgres(database_url: str) -> Iterator[psycopg.Connection[Any]]:
    with psycopg.connect(require_postgres_dsn(database_url)) as conn:
        yield conn


def run_postgres_migrations(database_url: str, *, revision: str = "head") -> None:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url(database_url))
    command.upgrade(config, revision)
