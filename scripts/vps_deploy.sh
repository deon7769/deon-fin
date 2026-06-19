#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

timestamp="$(date +%Y%m%d-%H%M%S)"
db_path="$ROOT/data/financas.db"
backup_dir="$ROOT/data/backups"

echo "== Deon Fin VPS deploy ${timestamp} =="
echo "root: $ROOT"

if [ -f "$db_path" ]; then
  mkdir -p "$backup_dir"
  backup_path="$backup_dir/financas.db.${timestamp}.bak"
  cp -p "$db_path" "$backup_path"
  echo "database backup: $backup_path"
else
  echo "database backup: skipped, $db_path not found"
fi

echo "== pytest =="
.venv/bin/python -m pytest -q

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

echo "== recent logs =="
docker compose logs --tail=80 financas-agent
