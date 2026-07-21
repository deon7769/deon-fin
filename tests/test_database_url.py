from __future__ import annotations

from pathlib import Path

import pytest

from src.storage.database_url import DatabaseKind, parse_database_url


def test_parse_sqlite_url_resolves_project_relative_path(tmp_path: Path):
    parsed = parse_database_url("sqlite:///data/financas.db", project_root=tmp_path)

    assert parsed.kind == DatabaseKind.SQLITE
    assert parsed.sqlite_path == tmp_path / "data" / "financas.db"
    assert parsed.postgres_dsn is None


def test_parse_plain_path_as_sqlite_path(tmp_path: Path):
    parsed = parse_database_url(str(tmp_path / "local.db"), project_root=tmp_path)

    assert parsed.kind == DatabaseKind.SQLITE
    assert parsed.sqlite_path == tmp_path / "local.db"
    assert parsed.postgres_dsn is None


def test_parse_plain_relative_path_anchors_to_project_root(tmp_path: Path):
    parsed = parse_database_url("data/local.db", project_root=tmp_path)

    assert parsed.kind == DatabaseKind.SQLITE
    assert parsed.sqlite_path == tmp_path / "data" / "local.db"
    assert parsed.postgres_dsn is None


def test_parse_empty_raw_defaults_to_sqlite_database(tmp_path: Path):
    parsed = parse_database_url("", project_root=tmp_path)

    assert parsed.kind == DatabaseKind.SQLITE
    assert parsed.raw == "sqlite:///data/financas.db"
    assert parsed.sqlite_path == tmp_path / "data" / "financas.db"
    assert parsed.postgres_dsn is None


def test_parse_postgres_url_keeps_raw_dsn(tmp_path: Path):
    dsn = "postgresql://deon:secret@postgres:5432/deon_fin"

    parsed = parse_database_url(dsn, project_root=tmp_path)

    assert parsed.kind == DatabaseKind.POSTGRES
    assert parsed.sqlite_path is None
    assert parsed.postgres_dsn == dsn


def test_parse_postgres_alias_keeps_raw_dsn(tmp_path: Path):
    dsn = "postgres://deon:secret@postgres:5432/deon_fin"

    parsed = parse_database_url(dsn, project_root=tmp_path)

    assert parsed.kind == DatabaseKind.POSTGRES
    assert parsed.sqlite_path is None
    assert parsed.postgres_dsn == dsn


def test_parse_postgresql_psycopg_alias(tmp_path: Path):
    dsn = "postgresql+psycopg://deon:secret@localhost:5432/deon_fin"

    parsed = parse_database_url(dsn, project_root=tmp_path)

    assert parsed.kind == DatabaseKind.POSTGRES
    assert parsed.postgres_dsn == "postgresql://deon:secret@localhost:5432/deon_fin"


def test_parse_rejects_unsupported_url(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported DATABASE_URL"):
        parse_database_url("mysql://root:secret@localhost/db", project_root=tmp_path)
