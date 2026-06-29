from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DatabaseKind(StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"


@dataclass(frozen=True)
class ParsedDatabaseUrl:
    kind: DatabaseKind
    raw: str
    sqlite_path: Path | None = None
    postgres_dsn: str | None = None


def parse_database_url(raw: str, *, project_root: Path) -> ParsedDatabaseUrl:
    value = (raw or "").strip()
    if not value:
        value = "sqlite:///data/financas.db"

    if value.startswith("sqlite:///"):
        suffix = value.removeprefix("sqlite:///")
        path = Path(suffix)
        if not path.is_absolute():
            path = project_root / path
        return ParsedDatabaseUrl(
            kind=DatabaseKind.SQLITE,
            raw=value,
            sqlite_path=path,
        )

    if value.startswith("postgresql+psycopg://"):
        dsn = "postgresql://" + value.removeprefix("postgresql+psycopg://")
        return ParsedDatabaseUrl(
            kind=DatabaseKind.POSTGRES,
            raw=value,
            postgres_dsn=dsn,
        )

    if value.startswith("postgresql://") or value.startswith("postgres://"):
        return ParsedDatabaseUrl(
            kind=DatabaseKind.POSTGRES,
            raw=value,
            postgres_dsn=value,
        )

    if "://" not in value:
        return ParsedDatabaseUrl(
            kind=DatabaseKind.SQLITE,
            raw=value,
            sqlite_path=Path(value),
        )

    raise ValueError(f"Unsupported DATABASE_URL: {value}")
