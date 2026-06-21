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
