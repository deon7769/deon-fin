from __future__ import annotations

from pathlib import Path


def test_dockerfile_builds_next_export_in_node_stage():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:24-slim AS web" in dockerfile
    assert "COPY web/package*.json ./" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "ENV NEXT_PUBLIC_API_URL=/api" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "COPY --from=web /web/out ./web_dist" in dockerfile


def test_dockerignore_excludes_local_build_and_secret_artifacts():
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert ".venv/" in dockerignore
    assert "data/" in dockerignore
    assert "web/node_modules/" in dockerignore
    assert "web/.next/" in dockerignore
    assert "web/out/" in dockerignore


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
