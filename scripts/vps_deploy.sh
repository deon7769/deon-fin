#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

timestamp="$(date +%Y%m%d-%H%M%S)"
db_path="$ROOT/data/financas.db"
backup_dir="$ROOT/data/backups"
BACKUP_KEEP_RECENT="${BACKUP_KEEP_RECENT:-14}"
APP_UID="${APP_UID:-1000}"
APP_GID="${APP_GID:-1000}"

rotate_backups() {
  local pattern="$1"
  if [ ! -d "$backup_dir" ]; then
    return
  fi
  mapfile -t old_backups < <(
    find "$backup_dir" -maxdepth 1 -type f -name "$pattern" -printf '%T@\t%p\n' \
      | sort -rn \
      | tail -n +"$((BACKUP_KEEP_RECENT + 1))" \
      | cut -f2-
  )
  for old_backup in "${old_backups[@]}"; do
    rm -f -- "$old_backup"
    echo "backup pruned: $old_backup"
  done
}

rotate_sqlite_backups() {
  rotate_backups "financas.db.*.bak"
  rotate_backups "financas.db-wal.*.bak"
  rotate_backups "financas.db-shm.*.bak"
}

ensure_data_ownership() {
  if [ ! -d "$ROOT/data" ]; then
    return
  fi
  if [ "$(id -u)" -eq 0 ]; then
    chown -R "$APP_UID:$APP_GID" "$ROOT/data"
    return
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo chown -R "$APP_UID:$APP_GID" "$ROOT/data"
    return
  fi
  echo "sudo not available; cannot repair data ownership for non-root container" >&2
  exit 1
}

ensure_private_permissions() {
  local data_dir="$ROOT/data"
  local private_dir

  if [ -f "$ROOT/.env" ]; then
    chmod 600 "$ROOT/.env"
  fi

  for private_dir in "$data_dir" "$backup_dir" "$backup_dir/env" "$data_dir/secrets"; do
    if [ -d "$private_dir" ]; then
      chmod 700 "$private_dir"
    fi
  done

  if [ -d "$data_dir" ]; then
    find "$data_dir" -type f -exec chmod 600 {} +
  fi
}

echo "== Deon Fin VPS deploy ${timestamp} =="
echo "root: $ROOT"

if [ -f "$db_path" ]; then
  mkdir -p "$backup_dir"
  for source_path in "$db_path" "$db_path-wal" "$db_path-shm"; do
    if [ -f "$source_path" ]; then
      backup_path="$backup_dir/$(basename "$source_path").${timestamp}.bak"
      cp -p "$source_path" "$backup_path"
      echo "database backup: $backup_path"
    fi
  done
  rotate_sqlite_backups
else
  echo "database backup: skipped, $db_path not found"
fi

ensure_data_ownership
ensure_private_permissions

echo "== pytest =="
AUTH_SESSION_ENABLED=false NEXT_PUBLIC_AUTH_ENABLED=false .venv/bin/python -m pytest -q

echo "== docker compose build =="
docker compose build financas-agent

echo "== docker compose up =="
docker compose up -d financas-agent

echo "== container health smoke =="
for attempt in {1..30}; do
  if health_output="$(docker compose exec -T financas-agent python - <<'PY' 2>&1
import json
import urllib.request as request

resp = request.urlopen("http://127.0.0.1:8000/api/health", timeout=5)
body = resp.read().decode("utf-8")
if resp.status != 200:
    raise SystemExit(f"unexpected status: {resp.status}")
payload = json.loads(body)
if payload != {"status": "ok"}:
    raise SystemExit(f"unexpected body: {body}")
print(f"health ok: {body}")
PY
)"; then
    printf '%s\n' "$health_output"
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    printf '%s\n' "$health_output" >&2
    echo "health check failed after ${attempt} attempts" >&2
    exit 1
  fi
  echo "health not ready yet (attempt ${attempt}/30); waiting..."
  sleep 1
done

echo "== container frontend smoke =="
for attempt in {1..30}; do
  if frontend_output="$(docker compose exec -T financas-agent python - <<'PY' 2>&1
import base64
import os
import urllib.request as request

req = request.Request("http://127.0.0.1:8000/")
password = os.environ.get("APP_PASSWORD", "")
if password:
    user = os.environ.get("APP_USER", "admin")
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")

resp = request.urlopen(req, timeout=5)
html = resp.read().decode("utf-8", errors="replace")
if resp.status != 200:
    raise SystemExit(f"unexpected status: {resp.status}")

markers = ("deon-fin", "/_next/")
if os.environ.get("LEGACY_UI", "").lower() in {"1", "true", "yes"}:
    markers = markers + ("Pluggy Connect",)
if not any(marker in html for marker in markers):
    raise SystemExit("frontend marker not found")

print(f"frontend ok: status={resp.status}")
PY
)"; then
    printf '%s\n' "$frontend_output"
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    printf '%s\n' "$frontend_output" >&2
    echo "frontend check failed after ${attempt} attempts" >&2
    exit 1
  fi
  echo "frontend not ready yet (attempt ${attempt}/30); waiting..."
  sleep 1
done

echo "== recent logs =="
docker compose logs --tail=80 financas-agent
