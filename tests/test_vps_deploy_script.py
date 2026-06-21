from __future__ import annotations

from pathlib import Path


def test_deploy_health_smoke_retries_until_container_is_ready():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "for attempt in {1..30}" in script
    assert "health_output=\"$(" in script
    assert '"$health_output"' in script
    assert "health not ready yet" in script
    assert "sleep 1" in script
    assert "health check failed after" in script
    assert "health ok:" in script


def test_deploy_frontend_smoke_checks_root_with_basic_auth_support():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "frontend_output=\"$(" in script
    assert "http://127.0.0.1:8000/" in script
    assert "APP_USER" in script
    assert "APP_PASSWORD" in script
    assert "Authorization" in script
    assert "Basic" in script
    assert "deon-fin" in script
    assert "/_next/" in script
    assert "frontend ok:" in script
    assert "frontend check failed after" in script
