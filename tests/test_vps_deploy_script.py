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


def test_deploy_backup_includes_sqlite_sidecars():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert '"$db_path"' in script
    assert '"$db_path-wal"' in script
    assert '"$db_path-shm"' in script
    assert "basename" in script


def test_deploy_prunes_old_sqlite_backups_after_backup():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "BACKUP_KEEP_RECENT=" in script
    assert "rotate_sqlite_backups()" in script
    assert "find \"$backup_dir\" -maxdepth 1 -type f -name \"$pattern\"" in script
    assert "tail -n +\"$((BACKUP_KEEP_RECENT + 1))\"" in script
    assert "rm -f -- \"$old_backup\"" in script
    assert 'rotate_backups "financas.db.*.bak"' in script
    assert 'rotate_backups "financas.db-wal.*.bak"' in script
    assert 'rotate_backups "financas.db-shm.*.bak"' in script


def test_deploy_repairs_data_ownership_for_non_root_container():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "ensure_data_ownership()" in script
    assert 'APP_UID="${APP_UID:-1000}"' in script
    assert 'APP_GID="${APP_GID:-1000}"' in script
    assert 'sudo chown -R "$APP_UID:$APP_GID" "$ROOT/data"' in script
    assert "ensure_data_ownership" in script.split('echo "== pytest =="', 1)[0]


def test_deploy_pytest_runs_with_auth_cutover_flags_disabled():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "AUTH_SESSION_ENABLED=false" in script
    assert "NEXT_PUBLIC_AUTH_ENABLED=false" in script
    assert "AUTH_SESSION_ENABLED=false NEXT_PUBLIC_AUTH_ENABLED=false .venv/bin/python -m pytest -q" in script


def test_deploy_enforces_private_data_and_backup_permissions():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "umask 077" in script
    assert "ensure_private_permissions()" in script
    assert 'chmod 600 "$ROOT/.env"' in script
    assert 'chmod 700 "$private_dir"' in script
    assert 'find "$data_dir" -type f -exec chmod 600 {} +' in script
    before_pytest = script.split('echo "== pytest =="', 1)[0]
    assert before_pytest.index("ensure_data_ownership") < before_pytest.index(
        "ensure_private_permissions"
    )

def test_deploy_reexecutes_as_root_before_accessing_private_data():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert 'if [ "$(id -u)" -ne 0 ]; then' in script
    assert 'exec sudo --preserve-env=APP_UID,APP_GID,BACKUP_KEEP_RECENT "$0" "$@"' in script
    assert script.index('exec sudo --preserve-env=APP_UID,APP_GID,BACKUP_KEEP_RECENT "$0" "$@"') < script.index(
        'db_path="$ROOT/data/financas.db"'
    )
