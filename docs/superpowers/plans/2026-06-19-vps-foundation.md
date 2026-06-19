# VPS Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the VPS-hosted Deon Fin app safe to change by restoring reliable tests, adding a repeatable deploy/smoke workflow, and enrolling it in the existing VPS health/watchdog loop.

**Architecture:** Keep the app running from `/opt/projetos/financas-agent` and preserve the current Docker Compose + Traefik deployment. Version app-side changes in the repo, but update VPS-wide scripts in `/opt` with timestamped backups because they are host infrastructure, not part of this repository. Tests run in the host virtualenv before Docker rebuild; the container is smoke-tested after restart.

**Tech Stack:** Python 3.12, pytest, FastAPI, SQLite, Docker Compose v5, Traefik, Bash, systemd watchdog timer.

---

## File Structure

- Modify `tests/conftest.py`: make test collection independent from production `.env` values while keeping Pluggy integration tests skipped unless real credentials are exported in the shell.
- Create `scripts/vps_deploy.sh`: one-command VPS deploy helper that backs up SQLite, runs tests, rebuilds/restarts Docker Compose, smoke-tests `/api/health`, and prints recent logs.
- Create `docs/ops/vps-deploy.md`: human-readable VPS operating procedure for this project.
- Modify host file `/opt/infra-healthcheck.sh`: include `financas-agent` in key container and endpoint checks.
- Modify host file `/opt/infra-watchdog.sh`: include `/opt/projetos/financas-agent` in Docker Compose project recovery and `fin.deonlab.tech/api/health` in endpoint checks.

## Task 1: Isolate Tests From Production `.env`

**Files:**
- Modify: `tests/conftest.py`
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Confirm the current regression**

Run from the VPS checkout:

```bash
cd /opt/projetos/financas-agent
.venv/bin/python -m pytest tests/test_web_app.py::test_index_renders -q
```

Expected before the fix:

```text
F
E   assert 401 == 200
```

This confirms the web tests are inheriting production Basic Auth.

- [ ] **Step 2: Replace `tests/conftest.py` with test-safe environment setup**

Write this exact file content:

```python
from __future__ import annotations

import os
from pathlib import Path

# Capture real shell-provided Pluggy credentials before test placeholders are
# installed. Values loaded only from .env should not make integration tests run.
_HAS_REAL_PLUGGY_ENV_CREDS = bool(
    os.environ.get("PLUGGY_CLIENT_ID") and os.environ.get("PLUGGY_CLIENT_SECRET")
)

# src.config loads .env on import with override=False. These values must exist
# before tests import src.web.app, otherwise production .env can leak into unit
# tests and enable Basic Auth/autosync.
os.environ.setdefault("PLUGGY_CLIENT_ID", "test-client-id")
os.environ.setdefault("PLUGGY_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("DATABASE_URL", "sqlite:///data/test-suite.db")
os.environ["APP_PASSWORD"] = ""
os.environ["AUTO_SYNC_ON_START"] = "false"
os.environ["AUTO_SYNC_MINUTES"] = "0"

import pytest

from src.storage import Database


@pytest.fixture
def tmp_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    yield db
    db.close()


def pytest_collection_modifyitems(config, items):
    if not _HAS_REAL_PLUGGY_ENV_CREDS:
        skip = pytest.mark.skip(reason="Pluggy credentials not configured")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
```

- [ ] **Step 3: Run the focused web test**

```bash
cd /opt/projetos/financas-agent
.venv/bin/python -m pytest tests/test_web_app.py::test_index_renders -q
```

Expected after the fix:

```text
.                                                                        [100%]
```

- [ ] **Step 4: Run the full suite**

```bash
cd /opt/projetos/financas-agent
.venv/bin/python -m pytest -q
```

Expected after the fix:

```text
66 passed, 4 skipped
```

If real Pluggy credentials are exported in the shell before pytest starts, the four integration tests may run and the expected summary becomes `70 passed`. The exact warning count may vary because FastAPI and ofxparse emit deprecation warnings.

- [ ] **Step 5: Commit the test isolation change**

```bash
cd /opt/projetos/financas-agent
git status --short
git add tests/conftest.py
git commit -m "test: isolate web tests from production env"
```

Expected:

```text
[codex/financas-vps-foundation ...] test: isolate web tests from production env
```

Do not stage `.cursor/`.

## Task 2: Add a VPS Deploy and Smoke-Test Helper

**Files:**
- Create: `scripts/vps_deploy.sh`
- Create: `docs/ops/vps-deploy.md`
- Test: shell syntax and actual deploy smoke in Task 4

- [ ] **Step 1: Create `scripts/vps_deploy.sh`**

Write this exact file content:

```bash
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
docker compose exec -T financas-agent python - <<'PY'
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

echo "== recent logs =="
docker compose logs --tail=80 financas-agent
```

- [ ] **Step 2: Make the deploy helper executable**

```bash
cd /opt/projetos/financas-agent
chmod +x scripts/vps_deploy.sh
```

Expected: command exits with status 0.

- [ ] **Step 3: Create `docs/ops/vps-deploy.md`**

Write this exact file content:

````markdown
# VPS deploy procedure

This project is operated directly on `minha-vps` from:

```text
/opt/projetos/financas-agent
```

The running app is the Docker Compose service `financas-agent`, routed by Traefik at:

```text
https://fin.deonlab.tech
```

## Safe deploy

Run from the VPS checkout:

```bash
cd /opt/projetos/financas-agent
./scripts/vps_deploy.sh
```

The script performs this sequence:

1. Creates a timestamped backup of `data/financas.db` under `data/backups/` when the database exists.
2. Runs `.venv/bin/python -m pytest -q`.
3. Rebuilds the Docker image for `financas-agent`.
4. Restarts the Compose service.
5. Calls `http://127.0.0.1:8000/api/health` from inside the container.
6. Prints the last 80 container log lines.

If any step fails, the script stops before continuing.

## Manual checks

```bash
cd /opt/projetos/financas-agent
.venv/bin/python -m pytest -q
docker compose ps
docker compose exec -T financas-agent python - <<'PY'
import urllib.request as request
resp = request.urlopen("http://127.0.0.1:8000/api/health", timeout=5)
print(resp.status, resp.read().decode())
PY
docker compose logs --tail=120 financas-agent
```

## VPS infra checks

The host-level scripts are outside this repository:

```text
/opt/infra-healthcheck.sh
/opt/infra-watchdog.sh
```

`financas-agent` should be present in both scripts. The watchdog is managed by:

```text
infra-watchdog.timer
infra-watchdog.service
```

Check them with:

```bash
/opt/infra-healthcheck.sh
systemctl list-timers --all --no-pager | grep infra-watchdog
systemctl status infra-watchdog.service --no-pager
```
````

- [ ] **Step 4: Syntax-check the shell script**

```bash
cd /opt/projetos/financas-agent
bash -n scripts/vps_deploy.sh
```

Expected: no output and exit status 0.

- [ ] **Step 5: Commit the deploy helper and docs**

```bash
cd /opt/projetos/financas-agent
git add scripts/vps_deploy.sh docs/ops/vps-deploy.md
git commit -m "ops: add VPS deploy helper"
```

Expected:

```text
[codex/financas-vps-foundation ...] ops: add VPS deploy helper
```

Do not stage `.cursor/`.

## Task 3: Enroll Deon Fin in VPS Healthcheck and Watchdog

**Files:**
- Modify host file: `/opt/infra-healthcheck.sh`
- Modify host file: `/opt/infra-watchdog.sh`
- Test: `/opt/infra-healthcheck.sh`, `infra-watchdog.service`

- [ ] **Step 1: Back up both host scripts**

```bash
ts="$(date +%Y%m%d-%H%M%S)"
sudo cp -p /opt/infra-healthcheck.sh "/opt/infra-healthcheck.sh.bak-${ts}-financas-agent"
sudo cp -p /opt/infra-watchdog.sh "/opt/infra-watchdog.sh.bak-${ts}-financas-agent"
ls -l "/opt/infra-healthcheck.sh.bak-${ts}-financas-agent" "/opt/infra-watchdog.sh.bak-${ts}-financas-agent"
```

Expected: both backup files exist and have nonzero sizes.

- [ ] **Step 2: Update `/opt/infra-healthcheck.sh`**

Apply these exact edits:

```bash
sudo python3 - <<'PY'
from pathlib import Path

path = Path("/opt/infra-healthcheck.sh")
text = path.read_text()

old_regex = 'grep -E "^(NAMES|openclaw|vaultwarden|infisical|n8n|traefik|portainer|grafana|prometheus|loki|promtail|nutri_|postiz|monitoraitajai|node-exporter|cadvisor)" || true'
new_regex = 'grep -E "^(NAMES|financas-agent|openclaw|vaultwarden|infisical|n8n|traefik|portainer|grafana|prometheus|loki|promtail|nutri_|postiz|monitoraitajai|node-exporter|cadvisor)" || true'
if old_regex not in text and new_regex not in text:
    raise SystemExit("key container regex anchor not found")
text = text.replace(old_regex, new_regex)

old_endpoint = '  https://postiz.deonlab.tech/; do'
new_endpoint = '  https://postiz.deonlab.tech/ \\' + chr(10) + '  https://fin.deonlab.tech/api/health; do'
if old_endpoint not in text and 'https://fin.deonlab.tech/api/health' not in text:
    raise SystemExit("endpoint list anchor not found")
text = text.replace(old_endpoint, new_endpoint)

path.write_text(text)
PY
```

- [ ] **Step 3: Update `/opt/infra-watchdog.sh`**

Apply these exact edits:

```bash
sudo python3 - <<'PY'
from pathlib import Path

path = Path("/opt/infra-watchdog.sh")
text = path.read_text()

old_project = '  /opt/monitoraitajai\n)'
new_project = '  /opt/monitoraitajai\n  /opt/projetos/financas-agent\n)'
if old_project not in text and '/opt/projetos/financas-agent' not in text:
    raise SystemExit("project list anchor not found")
text = text.replace(old_project, new_project)

old_endpoint = 'check_endpoint "postiz" "https://postiz.deonlab.tech/" "^(200|302|307|401|403)$"'
new_endpoint = old_endpoint + '\ncheck_endpoint "financas-agent" "https://fin.deonlab.tech/api/health" "^200$"'
if old_endpoint not in text and 'check_endpoint "financas-agent"' not in text:
    raise SystemExit("endpoint check anchor not found")
text = text.replace(old_endpoint, new_endpoint)

path.write_text(text)
PY
```

- [ ] **Step 4: Syntax-check both host scripts**

```bash
sudo bash -n /opt/infra-healthcheck.sh
sudo bash -n /opt/infra-watchdog.sh
```

Expected: no output and exit status 0.

- [ ] **Step 5: Run the manual healthcheck**

```bash
/opt/infra-healthcheck.sh | tee /tmp/financas-healthcheck.out
grep -E '^financas-agent\b' /tmp/financas-healthcheck.out
grep 'https://fin.deonlab.tech/api/health' /tmp/financas-healthcheck.out
```

Expected:

```text
financas-agent ... Up ...
200 https://fin.deonlab.tech/api/health
```

- [ ] **Step 6: Run the watchdog once through systemd**

```bash
sudo systemctl start infra-watchdog.service
systemctl show infra-watchdog.service --property=Result --property=ExecMainStatus --no-pager
tail -n 20 /var/log/infra-watchdog/infra-watchdog.log
```

Expected:

```text
Result=success
ExecMainStatus=0
watchdog ok
```

## Task 4: Deploy and Final Verification

**Files:**
- Execute: `scripts/vps_deploy.sh`
- Inspect: Docker Compose service `financas-agent`
- Inspect: Git branch `codex/financas-vps-foundation`

- [ ] **Step 1: Confirm branch and working tree before deploy**

```bash
cd /opt/projetos/financas-agent
git branch --show-current
git status --short
```

Expected:

```text
codex/financas-vps-foundation
.cursor/ is the only untracked path
```

If committed plan files or implementation files appear as modified, commit them before deployment.

- [ ] **Step 2: Run the deploy helper**

```bash
cd /opt/projetos/financas-agent
./scripts/vps_deploy.sh
```

Expected output must include:

```text
database backup: /opt/projetos/financas-agent/data/backups/financas.db.<timestamp>.bak
66 passed, 4 skipped
health ok: {"status":"ok"}
```

- [ ] **Step 3: Verify Compose state**

```bash
cd /opt/projetos/financas-agent
docker compose ps
```

Expected: service `financas-agent` is `running`.

- [ ] **Step 4: Verify external health endpoint from VPS**

```bash
curl -k -sS -o /tmp/financas-health.out -w "%{http_code}\n" --connect-timeout 8 --max-time 15 https://fin.deonlab.tech/api/health
cat /tmp/financas-health.out
rm -f /tmp/financas-health.out
```

Expected:

```text
200
{"status":"ok"}
```

- [ ] **Step 5: Confirm Git history and leave `.cursor/` untouched**

```bash
cd /opt/projetos/financas-agent
git log --oneline --decorate -5
git status --short --branch
```

Expected:

```text
## codex/financas-vps-foundation
.cursor/ is the only untracked path
```

The branch should contain commits for the design, the plan, the test isolation change, and the deploy helper. The host-level `/opt/infra-*.sh` edits are intentionally not committed to this app repository.

## Self-Review

- Spec coverage: Task 1 fixes the failing test loop; Task 2 creates the deploy/smoke workflow and SQLite backup path; Task 3 adds existing VPS health/watchdog coverage; Task 4 validates deploy, Docker state, external health, and Git cleanliness.
- Placeholder scan: no incomplete steps remain; every code or script change includes exact content or exact deterministic replacement commands.
- Type and command consistency: paths match the deployed VPS layout, the Docker Compose service name is `financas-agent`, and the branch name is `codex/financas-vps-foundation`.

## Execution Notes

- Do not stage `.cursor/`.
- Do not change production `.env` in this slice.
- Do not weaken the existing Traefik/Tailscale access model for `fin.deonlab.tech`.
- If sudo is not passwordless for `/opt/infra-*.sh`, stop after Task 2 and ask Davi to grant the host script edit or run the shown commands.
