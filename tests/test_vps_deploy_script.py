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
