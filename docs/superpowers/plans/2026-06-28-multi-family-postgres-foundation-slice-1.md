# Multi-Family Postgres Foundation Slice 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-invasive PostgreSQL foundation for multi-family data, including schema migrations, first admin/family bootstrap, and SQLite migration dry-run checks.

**Architecture:** Keep the current SQLite runtime intact while adding a PostgreSQL path beside it. The first slice creates Postgres infrastructure, Alembic migrations, URL parsing, password hashing primitives, a closed bootstrap command, and migration audit utilities. HTTP login, session middleware, and repository-wide `family_id` enforcement are handled by the next plans after this foundation exists.

**Tech Stack:** FastAPI, Typer, SQLite legacy storage, PostgreSQL 16, psycopg 3, Alembic, SQLAlchemy migration context, Argon2id via argon2-cffi, pytest.

---

## Scope Check

The design spec spans four subsystems:

1. PostgreSQL infrastructure and schema.
2. First-party auth/session security.
3. Family isolation across repositories and API routes.
4. SQLite-to-PostgreSQL production migration.

This plan covers subsystem 1 plus the bootstrap and dry-run pieces needed to make subsystem 2 and 4 possible. It deliberately does not replace Basic Auth or rewrite existing repositories. The next plan should cover first-party HTTP login, session cookies, brute-force tables, and same-origin protection using the schema introduced here.

## File Structure

- Create `src/storage/database_url.py`: parse `DATABASE_URL` into SQLite or PostgreSQL connection details.
- Create `src/storage/postgres.py`: open psycopg connections and run Alembic migrations from code.
- Create `alembic.ini`: Alembic config for this repo.
- Create `src/storage/postgres_migrations/env.py`: Alembic environment that reads `DATABASE_URL`.
- Create `src/storage/postgres_migrations/script.py.mako`: Alembic revision template.
- Create `src/storage/postgres_migrations/versions/0001_multi_family_foundation.py`: first PostgreSQL schema migration.
- Create `src/auth/__init__.py`: auth package marker.
- Create `src/auth/passwords.py`: email normalization, Argon2id hashing, password verification.
- Create `src/auth/bootstrap.py`: create the first admin user, default family, owner membership, and primary family person.
- Create `src/storage/migrate_sqlite_to_postgres.py`: count/audit SQLite data and produce a dry-run migration report.
- Modify `src/cli.py`: add `bootstrap-auth` and `pg-migration-dry-run` commands.
- Modify `requirements.txt`: add PostgreSQL, Alembic, and password hashing dependencies.
- Modify `.env.example`: document PostgreSQL and bootstrap variables without changing current SQLite default.
- Modify `docker-compose.yml`: add an optional `postgres` service under a Compose profile so current deploys do not start it by default.
- Create `tests/test_database_url.py`: URL parsing tests.
- Create `tests/test_postgres_migration_files.py`: static checks for Alembic schema files.
- Create `tests/test_auth_passwords.py`: password hashing tests.
- Create `tests/test_auth_bootstrap.py`: bootstrap SQL behavior with a fake connection.
- Create `tests/test_sqlite_to_postgres_dry_run.py`: dry-run counts from a legacy SQLite database.
- Modify `tests/test_cli.py`: CLI tests for the two new commands.
- Modify `tests/test_dockerfile.py`: static checks for optional Postgres Compose config.
- Create or modify `docs/ops/postgres-foundation.md`: operator notes for enabling the Postgres profile and running dry-run checks.

## Task 1: Prepare a Clean Execution Workspace

**Files:**
- No repo files changed.

- [ ] **Step 1: Start from a clean isolated worktree**

Run:

```powershell
git fetch origin main
git worktree add "$env:USERPROFILE\.config\superpowers\worktrees\deon-fin\multi-family-postgres-slice-1" -b codex/multi-family-postgres-slice-1 origin/main
Set-Location "$env:USERPROFILE\.config\superpowers\worktrees\deon-fin\multi-family-postgres-slice-1"
```

Expected: worktree is created from `origin/main`.

- [ ] **Step 2: Confirm clean status**

Run:

```powershell
git status --short --branch
```

Expected:

```text
## codex/multi-family-postgres-slice-1...origin/main
```

- [ ] **Step 3: Install dependencies already present in the project**

Run:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

Expected: install exits with code 0.

## Task 2: Add Database URL Parsing

**Files:**
- Create: `src/storage/database_url.py`
- Test: `tests/test_database_url.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_database_url.py`:

```python
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


def test_parse_postgres_url_keeps_raw_dsn(tmp_path: Path):
    dsn = "postgresql://deon:secret@postgres:5432/deon_fin"

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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_database_url.py -q
```

Expected: failure with `ModuleNotFoundError: No module named 'src.storage.database_url'`.

- [ ] **Step 3: Implement URL parsing**

Create `src/storage/database_url.py`:

```python
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
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_database_url.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/storage/database_url.py tests/test_database_url.py
git commit -m "feat: parse database urls"
```

## Task 3: Add Dependencies and Optional Postgres Compose Service

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `tests/test_dockerfile.py`

- [ ] **Step 1: Write failing static tests**

Append to `tests/test_dockerfile.py`:

```python

def test_requirements_include_postgres_migration_and_password_dependencies():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert "psycopg[binary]" in requirements
    assert "alembic" in requirements
    assert "sqlalchemy" in requirements
    assert "argon2-cffi" in requirements


def test_compose_declares_optional_postgres_profile():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "postgres:" in compose
    assert "profiles:" in compose
    assert '"postgres"' in compose
    assert "postgres_data:" in compose
    assert "deon_fin_internal:" in compose


def test_env_example_documents_postgres_without_switching_default_database():
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///data/financas.db" in env_example
    assert "POSTGRES_DB=deon_fin" in env_example
    assert "AUTH_PEPPER=" in env_example
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_dockerfile.py -q
```

Expected: failure because dependencies and Compose Postgres profile are absent.

- [ ] **Step 3: Add Python dependencies**

Append to `requirements.txt`:

```text
psycopg[binary]>=3.2.0
sqlalchemy>=2.0.0
alembic>=1.13.0
argon2-cffi>=23.1.0
```

- [ ] **Step 4: Document PostgreSQL variables without changing runtime default**

Add below the current `DATABASE_URL=sqlite:///data/financas.db` line in `.env.example`:

```text

# PostgreSQL foundation (optional until the multi-family cutover)
# To run locally: docker compose --profile postgres up -d postgres
# Keep DATABASE_URL as SQLite until the migration cutover is explicitly executed.
POSTGRES_DB=deon_fin
POSTGRES_USER=deon_fin
POSTGRES_PASSWORD=change-me-before-production
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
# DATABASE_URL=postgresql://deon_fin:change-me-before-production@postgres:5432/deon_fin

# Auth/session pepper for hashed audit identifiers and tokens.
AUTH_PEPPER=
```

- [ ] **Step 5: Add optional Postgres service**

Modify `docker-compose.yml` to this structure:

```yaml
services:
  financas-agent:
    build: .
    image: financas-agent:local
    container_name: financas-agent
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
    networks:
      - traefik_proxy
      - deon_fin_internal
    labels:
      - "traefik.enable=true"
      - "traefik.docker.network=traefik_proxy"
      - "traefik.http.routers.financas.rule=Host(`fin.deonlab.tech`)"
      - "traefik.http.routers.financas.entrypoints=websecure"
      - "traefik.http.routers.financas.middlewares=tailscale-only@docker"
      - "traefik.http.routers.financas.tls=true"
      - "traefik.http.routers.financas.tls.certresolver=letsencrypt"
      - "traefik.http.routers.financas.tls.domains[0].main=fin.deonlab.tech"
      - "traefik.http.routers.financas.service=financas"
      - "traefik.http.services.financas.loadbalancer.server.port=8000"

  postgres:
    image: postgres:16-alpine
    container_name: financas-postgres
    restart: unless-stopped
    profiles: ["postgres"]
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-deon_fin}
      POSTGRES_USER: ${POSTGRES_USER:-deon_fin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change-me-before-production}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - deon_fin_internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:

networks:
  traefik_proxy:
    external: true
  deon_fin_internal:
    driver: bridge
```

- [ ] **Step 6: Install new dependencies**

Run:

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

Expected: install exits with code 0.

- [ ] **Step 7: Run tests and verify pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_dockerfile.py -q
```

Expected: all tests in `tests/test_dockerfile.py` pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add requirements.txt .env.example docker-compose.yml tests/test_dockerfile.py
git commit -m "chore: add optional postgres foundation"
```

## Task 4: Add Alembic PostgreSQL Migration Scaffold

**Files:**
- Create: `alembic.ini`
- Create: `src/storage/postgres_migrations/env.py`
- Create: `src/storage/postgres_migrations/script.py.mako`
- Create: `src/storage/postgres_migrations/versions/0001_multi_family_foundation.py`
- Test: `tests/test_postgres_migration_files.py`

- [ ] **Step 1: Write failing static migration tests**

Create `tests/test_postgres_migration_files.py`:

```python
from __future__ import annotations

from pathlib import Path


MIGRATION = Path(
    "src/storage/postgres_migrations/versions/0001_multi_family_foundation.py"
)


def test_alembic_files_exist():
    assert Path("alembic.ini").is_file()
    assert Path("src/storage/postgres_migrations/env.py").is_file()
    assert Path("src/storage/postgres_migrations/script.py.mako").is_file()
    assert MIGRATION.is_file()


def test_foundation_migration_creates_required_tables():
    source = MIGRATION.read_text(encoding="utf-8")

    for table in (
        "users",
        "user_identities",
        "families",
        "family_members",
        "family_people",
        "sessions",
        "login_attempts",
        "user_security_state",
        "provider_connections",
        "accounts",
        "account_people",
        "transactions",
        "transaction_links",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in source


def test_foundation_migration_creates_required_indexes():
    source = MIGRATION.read_text(encoding="utf-8")

    for index in (
        "idx_family_members_user_family",
        "idx_provider_connections_family_provider_item",
        "idx_accounts_family_source_external",
        "idx_transactions_family_account_posted",
        "idx_transactions_family_reference_month",
        "idx_transaction_links_family_source",
        "idx_login_attempts_email_created",
        "idx_login_attempts_ip_created",
        "idx_sessions_token_hash",
    ):
        assert index in source


def test_foundation_migration_uses_jsonb_and_citext():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS citext" in source
    assert "jsonb" in source
    assert "citext" in source
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_postgres_migration_files.py -q
```

Expected: failure because Alembic files do not exist.

- [ ] **Step 3: Create `alembic.ini`**

Create `alembic.ini`:

```ini
[alembic]
script_location = src/storage/postgres_migrations
prepend_sys_path = .
timezone = UTC

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 4: Create Alembic environment**

Create `src/storage/postgres_migrations/env.py`:

```python
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if value.startswith("postgresql+psycopg://"):
        return value
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value.removeprefix("postgres://")
    raise RuntimeError("Alembic PostgreSQL migrations require DATABASE_URL=postgresql://...")


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Create Alembic script template**

Create `src/storage/postgres_migrations/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from __future__ import annotations

from alembic import op

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

- [ ] **Step 6: Create foundation migration**

Create `src/storage/postgres_migrations/versions/0001_multi_family_foundation.py` with the following structure. Keep the SQL strings exactly named so the static tests can read them:

```python
from __future__ import annotations

from alembic import op

revision = "0001_multi_family_foundation"
down_revision = None
branch_labels = None
depends_on = None


DDL = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    "CREATE EXTENSION IF NOT EXISTS citext",
    """
    CREATE TABLE IF NOT EXISTS users (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email citext UNIQUE NOT NULL,
        password_hash text,
        display_name text,
        status text NOT NULL DEFAULT 'active',
        password_changed_at timestamptz,
        last_login_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_identities (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider text NOT NULL,
        provider_subject text,
        provider_email citext,
        metadata_json jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_user_identities_provider_subject
        ON user_identities(provider, provider_subject)
        WHERE provider_subject IS NOT NULL
    """,
    """
    CREATE TABLE IF NOT EXISTS families (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        name text NOT NULL,
        slug text UNIQUE NOT NULL,
        status text NOT NULL DEFAULT 'active',
        default_currency text NOT NULL DEFAULT 'BRL',
        timezone text NOT NULL DEFAULT 'America/Sao_Paulo',
        created_by_user_id uuid REFERENCES users(id),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS family_members (
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role text NOT NULL,
        status text NOT NULL DEFAULT 'active',
        joined_at timestamptz,
        invited_by_user_id uuid REFERENCES users(id),
        PRIMARY KEY (family_id, user_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_family_members_user_family
        ON family_members(user_id, family_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS family_people (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        linked_user_id uuid REFERENCES users(id),
        display_name text NOT NULL,
        legal_name text,
        document_hash text,
        document_last4 text,
        aliases_json jsonb,
        status text NOT NULL DEFAULT 'active',
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        active_family_id uuid REFERENCES families(id),
        token_hash text UNIQUE NOT NULL,
        csrf_token_hash text,
        created_at timestamptz NOT NULL DEFAULT now(),
        last_seen_at timestamptz NOT NULL DEFAULT now(),
        expires_at timestamptz NOT NULL,
        rotated_at timestamptz,
        revoked_at timestamptz,
        ip_hash text,
        user_agent_hash text
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash)",
    """
    CREATE INDEX IF NOT EXISTS idx_sessions_user_active
        ON sessions(user_id, revoked_at, expires_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS login_attempts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid REFERENCES users(id) ON DELETE SET NULL,
        normalized_email_hash text,
        ip_hash text,
        user_agent_hash text,
        success boolean NOT NULL,
        failure_reason text,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_login_attempts_email_created
        ON login_attempts(normalized_email_hash, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_created
        ON login_attempts(ip_hash, created_at DESC)
    """,
    """
    CREATE TABLE IF NOT EXISTS user_security_state (
        user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        failed_login_count integer NOT NULL DEFAULT 0,
        last_failed_login_at timestamptz,
        locked_until timestamptz,
        password_reset_required boolean NOT NULL DEFAULT false,
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS provider_connections (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        provider text NOT NULL,
        external_item_id text,
        connector_id integer,
        connector_name text,
        status text,
        client_user_id text,
        owner_person_id uuid REFERENCES family_people(id),
        last_synced_at timestamptz,
        consent_expires_at timestamptz,
        metadata_json jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_provider_connections_family_provider_item
        ON provider_connections(family_id, provider, external_item_id)
        WHERE external_item_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_provider_connections_family_provider_item
        ON provider_connections(family_id, provider, external_item_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        connection_id uuid REFERENCES provider_connections(id),
        source text NOT NULL,
        external_account_id text,
        institution text,
        name text,
        type text,
        subtype text,
        currency text NOT NULL DEFAULT 'BRL',
        last4 text,
        status text,
        metadata_json jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_family_source_external
        ON accounts(family_id, source, external_account_id)
        WHERE external_account_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_accounts_family_source_external
        ON accounts(family_id, source, external_account_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_accounts_family_connection
        ON accounts(family_id, connection_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS account_people (
        account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        person_id uuid NOT NULL REFERENCES family_people(id) ON DELETE CASCADE,
        relationship text NOT NULL,
        source text NOT NULL,
        confidence real,
        created_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (account_id, person_id, relationship)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id text PRIMARY KEY,
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        connection_id uuid REFERENCES provider_connections(id),
        external_id text,
        posted_at date NOT NULL,
        reference_month text NOT NULL,
        amount numeric(14, 2) NOT NULL,
        currency text NOT NULL DEFAULT 'BRL',
        description text NOT NULL,
        raw_description text,
        category text,
        category_source text,
        tag_id uuid,
        bucket_id uuid,
        savings_goal_id uuid,
        hidden boolean NOT NULL DEFAULT false,
        note text,
        counterparty_name text,
        counterparty_document_hash text,
        merchant_key text,
        source text NOT NULL,
        metadata_json jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_family_source_external
        ON transactions(family_id, source, external_id)
        WHERE external_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_family_account_posted
        ON transactions(family_id, account_id, posted_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transactions_family_reference_month
        ON transactions(family_id, reference_month)
    """,
    "CREATE INDEX IF NOT EXISTS idx_transactions_family_tag ON transactions(family_id, tag_id)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_family_bucket ON transactions(family_id, bucket_id)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_family_merchant ON transactions(family_id, merchant_key)",
    """
    CREATE TABLE IF NOT EXISTS transaction_links (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        family_id uuid NOT NULL REFERENCES families(id) ON DELETE CASCADE,
        source_transaction_id text NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
        target_transaction_id text NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
        link_type text NOT NULL,
        confidence real,
        source text NOT NULL,
        metadata_json jsonb,
        created_at timestamptz NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transaction_links_family_source
        ON transaction_links(family_id, source_transaction_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transaction_links_family_target
        ON transaction_links(family_id, target_transaction_id)
    """,
]


DOWNGRADE = [
    "DROP TABLE IF EXISTS transaction_links",
    "DROP TABLE IF EXISTS transactions",
    "DROP TABLE IF EXISTS account_people",
    "DROP TABLE IF EXISTS accounts",
    "DROP TABLE IF EXISTS provider_connections",
    "DROP TABLE IF EXISTS user_security_state",
    "DROP TABLE IF EXISTS login_attempts",
    "DROP TABLE IF EXISTS sessions",
    "DROP TABLE IF EXISTS family_people",
    "DROP TABLE IF EXISTS family_members",
    "DROP TABLE IF EXISTS families",
    "DROP TABLE IF EXISTS user_identities",
    "DROP TABLE IF EXISTS users",
]


def upgrade() -> None:
    for statement in DDL:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
```

- [ ] **Step 7: Run migration file tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_postgres_migration_files.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add alembic.ini src/storage/postgres_migrations tests/test_postgres_migration_files.py
git commit -m "feat: add postgres foundation migrations"
```

## Task 5: Add PostgreSQL Connection and Migration Runner

**Files:**
- Create: `src/storage/postgres.py`
- Test: `tests/test_postgres_connection.py`

- [ ] **Step 1: Write failing tests with fakes**

Create `tests/test_postgres_connection.py`:

```python
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.storage.postgres import require_postgres_dsn, run_postgres_migrations


def test_require_postgres_dsn_accepts_postgresql_url():
    assert require_postgres_dsn("postgresql://u:p@localhost/db") == "postgresql://u:p@localhost/db"


def test_require_postgres_dsn_rejects_sqlite_url():
    with pytest.raises(ValueError, match="PostgreSQL DATABASE_URL required"):
        require_postgres_dsn("sqlite:///data/financas.db")


def test_run_postgres_migrations_passes_config_to_alembic(monkeypatch):
    calls = []

    class FakeConfig:
        def __init__(self, path):
            self.path = str(path)
            self.attributes = {}

        def set_main_option(self, key, value):
            calls.append((key, value))

    def fake_upgrade(config, revision):
        calls.append(("upgrade", revision, config.path))

    monkeypatch.setattr("src.storage.postgres.Config", FakeConfig)
    monkeypatch.setattr("src.storage.postgres.command", SimpleNamespace(upgrade=fake_upgrade))

    run_postgres_migrations("postgresql://u:p@localhost/db")

    assert ("sqlalchemy.url", "postgresql+psycopg://u:p@localhost/db") in calls
    assert any(call[0] == "upgrade" and call[1] == "head" for call in calls)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_postgres_connection.py -q
```

Expected: failure because `src.storage.postgres` does not exist.

- [ ] **Step 3: Implement PostgreSQL helpers**

Create `src/storage/postgres.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def require_postgres_dsn(database_url: str) -> str:
    value = (database_url or "").strip()
    if value.startswith("postgresql://") or value.startswith("postgres://"):
        return value
    if value.startswith("postgresql+psycopg://"):
        return "postgresql://" + value.removeprefix("postgresql+psycopg://")
    raise ValueError("PostgreSQL DATABASE_URL required")


def sqlalchemy_url(database_url: str) -> str:
    dsn = require_postgres_dsn(database_url)
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    return "postgresql+psycopg://" + dsn.removeprefix("postgres://")


@contextmanager
def connect_postgres(database_url: str) -> Iterator[psycopg.Connection]:
    dsn = require_postgres_dsn(database_url)
    with psycopg.connect(dsn) as conn:
        yield conn


def run_postgres_migrations(database_url: str, *, revision: str = "head") -> None:
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", sqlalchemy_url(database_url))
    command.upgrade(config, revision)
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_postgres_connection.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/storage/postgres.py tests/test_postgres_connection.py
git commit -m "feat: add postgres migration runner"
```

## Task 6: Add Password Hashing Primitives

**Files:**
- Create: `src/auth/__init__.py`
- Create: `src/auth/passwords.py`
- Test: `tests/test_auth_passwords.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_auth_passwords.py`:

```python
from __future__ import annotations

from src.auth.passwords import hash_password, normalize_email, verify_password


def test_normalize_email_strips_and_lowercases():
    assert normalize_email("  Davi@Example.COM ") == "davi@example.com"


def test_hash_password_uses_argon2_and_verifies():
    encoded = hash_password("correct horse battery staple")

    assert encoded.startswith("$argon2")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_auth_passwords.py -q
```

Expected: failure because `src.auth.passwords` does not exist.

- [ ] **Step 3: Implement password helpers**

Create `src/auth/__init__.py`:

```python
"""Authentication primitives for deon-fin."""
```

Create `src/auth/passwords.py`:

```python
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def normalize_email(email: str) -> str:
    return " ".join((email or "").strip().split()).lower()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password or not password_hash:
        return False
    try:
        return _HASHER.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_auth_passwords.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add src/auth/__init__.py src/auth/passwords.py tests/test_auth_passwords.py
git commit -m "feat: add password hashing primitives"
```

## Task 7: Add Closed Bootstrap for First User and Family

**Files:**
- Create: `src/auth/bootstrap.py`
- Modify: `src/cli.py`
- Test: `tests/test_auth_bootstrap.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write bootstrap unit tests with a fake connection**

Create `tests/test_auth_bootstrap.py`:

```python
from __future__ import annotations

from src.auth.bootstrap import BootstrapInput, bootstrap_admin_family


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.results = [
            ("user-1",),
            ("family-1",),
            ("person-1",),
        ]

    def execute(self, sql, params=None):
        self.statements.append((sql, params or {}))
        return self

    def fetchone(self):
        return self.results.pop(0)


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_bootstrap_admin_family_creates_user_family_membership_and_person():
    conn = FakeConnection()
    result = bootstrap_admin_family(
        conn,
        BootstrapInput(
            email=" Davi@Example.COM ",
            password="correct horse battery staple",
            display_name="Davi",
            family_name="Familia Principal",
            family_slug="familia-principal",
        ),
    )

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    assert result.user_id == "user-1"
    assert result.family_id == "family-1"
    assert result.person_id == "person-1"
    assert conn.committed
    assert "INSERT INTO users" in sql
    assert "INSERT INTO user_identities" in sql
    assert "INSERT INTO families" in sql
    assert "INSERT INTO family_members" in sql
    assert "INSERT INTO family_people" in sql
    assert conn.cursor_obj.statements[0][1]["email"] == "davi@example.com"
    assert conn.cursor_obj.statements[0][1]["password_hash"].startswith("$argon2")
```

- [ ] **Step 2: Run unit test and verify failure**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_auth_bootstrap.py -q
```

Expected: failure because `src.auth.bootstrap` does not exist.

- [ ] **Step 3: Implement bootstrap module**

Create `src/auth/bootstrap.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .passwords import hash_password, normalize_email


class CursorLike(Protocol):
    def execute(self, sql: str, params: dict[str, object] | None = None): ...
    def fetchone(self): ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...
    def commit(self) -> None: ...


@dataclass(frozen=True)
class BootstrapInput:
    email: str
    password: str
    display_name: str
    family_name: str = "Familia Principal"
    family_slug: str = "familia-principal"


@dataclass(frozen=True)
class BootstrapResult:
    user_id: str
    family_id: str
    person_id: str


def bootstrap_admin_family(conn: ConnectionLike, data: BootstrapInput) -> BootstrapResult:
    email = normalize_email(data.email)
    if not email:
        raise ValueError("Admin email must not be empty")
    if not data.password:
        raise ValueError("Admin password must not be empty")

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (email, password_hash, display_name, status, password_changed_at)
        VALUES (%(email)s, %(password_hash)s, %(display_name)s, 'active', now())
        ON CONFLICT (email) DO UPDATE SET
            password_hash = excluded.password_hash,
            display_name = excluded.display_name,
            status = 'active',
            password_changed_at = now(),
            updated_at = now()
        RETURNING id
        """,
        {
            "email": email,
            "password_hash": hash_password(data.password),
            "display_name": data.display_name,
        },
    )
    user_id = str(cur.fetchone()[0])

    cur.execute(
        """
        INSERT INTO user_identities (user_id, provider, provider_subject, provider_email)
        VALUES (%(user_id)s, 'local', %(email)s, %(email)s)
        ON CONFLICT (provider, provider_subject) WHERE provider_subject IS NOT NULL
        DO NOTHING
        """,
        {"user_id": user_id, "email": email},
    )

    cur.execute(
        """
        INSERT INTO families (name, slug, status, created_by_user_id)
        VALUES (%(name)s, %(slug)s, 'active', %(user_id)s)
        ON CONFLICT (slug) DO UPDATE SET
            name = excluded.name,
            status = 'active',
            updated_at = now()
        RETURNING id
        """,
        {"name": data.family_name, "slug": data.family_slug, "user_id": user_id},
    )
    family_id = str(cur.fetchone()[0])

    cur.execute(
        """
        INSERT INTO family_members (family_id, user_id, role, status, joined_at)
        VALUES (%(family_id)s, %(user_id)s, 'owner', 'active', now())
        ON CONFLICT (family_id, user_id) DO UPDATE SET
            role = 'owner',
            status = 'active',
            joined_at = COALESCE(family_members.joined_at, now())
        """,
        {"family_id": family_id, "user_id": user_id},
    )

    cur.execute(
        """
        INSERT INTO user_security_state (user_id)
        VALUES (%(user_id)s)
        ON CONFLICT (user_id) DO NOTHING
        """,
        {"user_id": user_id},
    )

    cur.execute(
        """
        INSERT INTO family_people (family_id, linked_user_id, display_name, status)
        VALUES (%(family_id)s, %(user_id)s, %(display_name)s, 'active')
        RETURNING id
        """,
        {"family_id": family_id, "user_id": user_id, "display_name": data.display_name},
    )
    person_id = str(cur.fetchone()[0])

    conn.commit()
    return BootstrapResult(user_id=user_id, family_id=family_id, person_id=person_id)
```

- [ ] **Step 4: Run bootstrap unit tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_auth_bootstrap.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Add CLI command**

Modify `src/cli.py` imports:

```python
from .auth.bootstrap import BootstrapInput, bootstrap_admin_family
from .storage.postgres import connect_postgres, run_postgres_migrations
```

Add this command before `serve`:

```python
@app.command("bootstrap-auth")
def bootstrap_auth(
    email: str = typer.Option(..., help="Email do primeiro administrador."),
    display_name: str = typer.Option("Admin", help="Nome exibido para o administrador."),
    family_name: str = typer.Option("Familia Principal", help="Nome da família inicial."),
    family_slug: str = typer.Option("familia-principal", help="Slug único da família inicial."),
    password: str = typer.Option(
        ...,
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Senha inicial do administrador.",
    ),
) -> None:
    """Cria ou atualiza o primeiro usuário owner e a família inicial no PostgreSQL."""
    run_postgres_migrations(settings.database_url)
    with connect_postgres(settings.database_url) as conn:
        result = bootstrap_admin_family(
            conn,
            BootstrapInput(
                email=email,
                password=password,
                display_name=display_name,
                family_name=family_name,
                family_slug=family_slug,
            ),
        )
    console.print(
        "[green]Bootstrap concluído:[/green] "
        f"user={result.user_id} family={result.family_id} person={result.person_id}"
    )
```

- [ ] **Step 6: Add CLI test with monkeypatches**

Append to `tests/test_cli.py`:

```python

def test_bootstrap_auth_command_runs_migrations_and_bootstrap(monkeypatch):
    calls = []

    class FakeConnection:
        pass

    class FakeConnectionContext:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_run_migrations(database_url):
        calls.append(("migrate", database_url))

    def fake_connect(database_url):
        calls.append(("connect", database_url))
        return FakeConnectionContext()

    def fake_bootstrap(conn, data):
        calls.append(("bootstrap", data.email, data.family_slug))
        return SimpleNamespace(user_id="user-1", family_id="family-1", person_id="person-1")

    monkeypatch.setattr(cli, "settings", SimpleNamespace(database_url="postgresql://u:p@localhost/db"))
    monkeypatch.setattr(cli, "run_postgres_migrations", fake_run_migrations)
    monkeypatch.setattr(cli, "connect_postgres", fake_connect)
    monkeypatch.setattr(cli, "bootstrap_admin_family", fake_bootstrap)

    result = CliRunner().invoke(
        cli.app,
        [
            "bootstrap-auth",
            "--email",
            "davi@example.com",
            "--display-name",
            "Davi",
            "--family-name",
            "Familia Principal",
            "--family-slug",
            "familia-principal",
        ],
        input="strong-password\nstrong-password\n",
    )

    assert result.exit_code == 0
    assert "Bootstrap concluído" in result.output
    assert calls == [
        ("migrate", "postgresql://u:p@localhost/db"),
        ("connect", "postgresql://u:p@localhost/db"),
        ("bootstrap", "davi@example.com", "familia-principal"),
    ]
```

- [ ] **Step 7: Run CLI and bootstrap tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_auth_bootstrap.py tests/test_cli.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src/auth/bootstrap.py src/cli.py tests/test_auth_bootstrap.py tests/test_cli.py
git commit -m "feat: add closed auth bootstrap"
```

## Task 8: Add SQLite Migration Dry-Run Report

**Files:**
- Create: `src/storage/migrate_sqlite_to_postgres.py`
- Modify: `src/cli.py`
- Test: `tests/test_sqlite_to_postgres_dry_run.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write dry-run unit tests**

Create `tests/test_sqlite_to_postgres_dry_run.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.storage import Account, Database, Transaction
from src.storage.migrate_sqlite_to_postgres import collect_sqlite_migration_report


def test_collect_sqlite_migration_report_counts_legacy_rows(tmp_path):
    db_path = tmp_path / "legacy.db"
    db = Database(db_path)
    db.upsert_account(Account(id="acc-1", source="csv", name="Conta", type="CHECKING"))
    db.insert_transactions(
        [
            Transaction(
                account_id="acc-1",
                posted_at=date(2026, 6, 1),
                amount=Decimal("-10.00"),
                description="Mercado",
                source="csv",
            )
        ]
    )
    db.upsert_pluggy_item("item-1", connector_id=1, connector_name="Banco", status="UPDATED")
    db.close()

    report = collect_sqlite_migration_report(db_path)

    assert report.sqlite_path == db_path
    assert report.default_family_name == "Familia Principal"
    assert report.counts["accounts"] == 1
    assert report.counts["transactions"] == 1
    assert report.counts["pluggy_items"] == 1
    assert report.target_tables["pluggy_items"] == "provider_connections"
```

- [ ] **Step 2: Run dry-run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_sqlite_to_postgres_dry_run.py -q
```

Expected: failure because the migration dry-run module does not exist.

- [ ] **Step 3: Implement dry-run module**

Create `src/storage/migrate_sqlite_to_postgres.py`:

```python
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


LEGACY_TABLES = (
    "pluggy_items",
    "accounts",
    "account_balances",
    "transactions",
    "tags",
    "budget_buckets",
    "bucket_rules",
    "tag_rules",
    "profile",
    "savings_goals",
    "portfolio_assets",
    "portfolio_transactions",
    "allocation_targets",
    "investment_profile",
    "asset_questions",
    "asset_answers",
    "classification_audit_log",
    "account_total_settings",
    "movement_total_settings",
)


TARGET_TABLES = {
    "pluggy_items": "provider_connections",
    "profile": "family_profiles",
}


@dataclass(frozen=True)
class SQLiteMigrationReport:
    sqlite_path: Path
    default_family_name: str
    counts: dict[str, int]
    target_tables: dict[str, str]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def collect_sqlite_migration_report(
    sqlite_path: Path,
    *,
    default_family_name: str = "Familia Principal",
) -> SQLiteMigrationReport:
    path = Path(sqlite_path)
    counts: dict[str, int] = {}
    with sqlite3.connect(path) as conn:
        for table in LEGACY_TABLES:
            if not _table_exists(conn, table):
                counts[table] = 0
                continue
            counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    return SQLiteMigrationReport(
        sqlite_path=path,
        default_family_name=default_family_name,
        counts=counts,
        target_tables={table: TARGET_TABLES.get(table, table) for table in LEGACY_TABLES},
    )
```

- [ ] **Step 4: Run dry-run tests and verify pass**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_sqlite_to_postgres_dry_run.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Add CLI command**

Modify `src/cli.py` imports:

```python
from .storage.migrate_sqlite_to_postgres import collect_sqlite_migration_report
```

Add this command before `serve`:

```python
@app.command("pg-migration-dry-run")
def pg_migration_dry_run(
    sqlite_path: Path | None = typer.Option(
        None,
        help="Caminho do SQLite legado. Usa settings.database_path quando omitido.",
    ),
    family_name: str = typer.Option("Familia Principal", help="Nome da família padrão da migração."),
) -> None:
    """Mostra contagens e mapeamentos da migração SQLite -> PostgreSQL sem escrever no destino."""
    source_path = sqlite_path or settings.database_path
    report = collect_sqlite_migration_report(source_path, default_family_name=family_name)
    table = Table("Origem SQLite", "Destino PostgreSQL", "Linhas")
    for source, count in report.counts.items():
        table.add_row(source, report.target_tables[source], str(count))
    console.print(f"[bold]Família padrão:[/bold] {report.default_family_name}")
    console.print(f"[bold]SQLite:[/bold] {report.sqlite_path}")
    console.print(table)
```

- [ ] **Step 6: Add CLI dry-run test**

Append to `tests/test_cli.py`:

```python

def test_pg_migration_dry_run_command_prints_counts(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy-cli.db"
    db = Database(db_path)
    db.upsert_account(Account(id="acc-1", source="csv"))
    db.close()

    monkeypatch.setattr(cli, "settings", SimpleNamespace(database_path=db_path))

    result = CliRunner().invoke(cli.app, ["pg-migration-dry-run"])

    assert result.exit_code == 0
    assert "Família padrão" in result.output
    assert "accounts" in result.output
    assert "1" in result.output
```

- [ ] **Step 7: Run selected tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest tests/test_sqlite_to_postgres_dry_run.py tests/test_cli.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src/storage/migrate_sqlite_to_postgres.py src/cli.py tests/test_sqlite_to_postgres_dry_run.py tests/test_cli.py
git commit -m "feat: add sqlite postgres migration dry run"
```

## Task 9: Add Operator Documentation

**Files:**
- Create: `docs/ops/postgres-foundation.md`

- [ ] **Step 1: Create operator doc**

Create `docs/ops/postgres-foundation.md`:

```markdown
# PostgreSQL foundation

This document covers the optional PostgreSQL foundation added before the
multi-family cutover.

## Local startup

```powershell
docker compose --profile postgres up -d postgres
```

The application keeps using SQLite while `DATABASE_URL` remains:

```text
DATABASE_URL=sqlite:///data/financas.db
```

To point commands at PostgreSQL:

```powershell
$env:DATABASE_URL="postgresql://deon_fin:change-me-before-production@localhost:5432/deon_fin"
```

## Bootstrap

After PostgreSQL is reachable:

```powershell
python -m src.cli bootstrap-auth --email admin@example.com --display-name Admin
```

The command runs Alembic migrations, hashes the password with Argon2id, creates
or updates the admin user, creates the default family, assigns the owner role,
and creates the first financial person.

## SQLite migration dry run

```powershell
python -m src.cli pg-migration-dry-run --sqlite-path data/financas.db
```

The command prints row counts and target table names. It does not write to
PostgreSQL.

## Production safety

Before enabling PostgreSQL in production:

1. Back up `data/financas.db`.
2. Start the `postgres` Compose profile with a production password.
3. Run the dry-run report and save the output.
4. Run `bootstrap-auth` for the first owner.
5. Keep SQLite as the rollback artifact until the full multi-family cutover has
   passed smoke tests.
```

- [ ] **Step 2: Commit**

Run:

```powershell
git add docs/ops/postgres-foundation.md
git commit -m "docs: document postgres foundation"
```

## Task 10: Run Full Verification

**Files:**
- No new files.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
.\.venv\Scripts\python -m pytest -q
```

Expected: pytest exits with code 0.

- [ ] **Step 2: Run frontend tests**

Run:

```powershell
Push-Location web
npm ci
npm test -- --run
npm run typecheck
npm run lint
npm run build
Pop-Location
```

Expected: each command exits with code 0.

- [ ] **Step 3: Run Docker build**

Run:

```powershell
docker build -t financas-agent:postgres-foundation .
```

Expected: Docker build exits with code 0.

- [ ] **Step 4: Run optional Postgres service smoke**

Run:

```powershell
docker compose --profile postgres up -d postgres
docker compose exec -T postgres pg_isready -U deon_fin -d deon_fin
docker compose --profile postgres down
```

Expected: `pg_isready` reports that PostgreSQL accepts connections.

- [ ] **Step 5: Confirm final diff**

Run:

```powershell
git status --short
git log --oneline origin/main..HEAD
```

Expected: working tree is clean and the branch contains only commits from this plan.

## Task 11: Publish

**Files:**
- No new files.

- [ ] **Step 1: Push branch**

Run:

```powershell
git push -u origin codex/multi-family-postgres-slice-1
```

Expected: branch is pushed to GitHub.

- [ ] **Step 2: Open draft PR**

Run:

```powershell
gh pr create --draft --base main --head codex/multi-family-postgres-slice-1 --title "[codex] Add multi-family Postgres foundation" --body "Adds the first PostgreSQL foundation slice for multi-family migration: optional Postgres Compose profile, Alembic schema, database URL parsing, Argon2 password primitives, closed admin/family bootstrap, SQLite migration dry-run report, and operator docs."
```

Expected: GitHub returns a draft PR URL.

## Self-Review Notes

Spec coverage in this plan:

- PostgreSQL service and migration tooling: Tasks 3, 4, 5, 9, 10.
- Core multi-family schema: Task 4.
- First admin/family bootstrap: Tasks 6 and 7.
- SQLite migration dry-run: Task 8.
- Production safety notes: Task 9.

Spec requirements intentionally assigned to subsequent plans:

- HTTP login endpoints, secure cookies, session middleware, brute-force runtime enforcement.
- `current_user`, `current_family`, and route authorization dependencies.
- Repository-wide family isolation.
- Full data-copy migration from SQLite rows into PostgreSQL rows.

Those subsequent plans should start from the schema and helpers introduced here.
