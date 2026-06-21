# VPS deploy procedure

This project is operated directly on `minha-vps` from:

```text
/opt/projetos/financas-agent
```

The running app is the Docker Compose service `financas-agent`, routed by Traefik at:

```text
https://fin.deonlab.tech
```

## Current status

Status em **2026-06-21**:

- A VPS acompanha a `main` pelo safe deploy em `/opt/projetos/financas-agent`.
- Cada deploy recria o container após backup do SQLite, pytest remoto, build Docker e smoke checks.
- O workflow ativo é `.github/workflows/ci-cd.yml`: pytest, testes/typecheck/lint/build do frontend e build Docker.
- O job de deploy automático existe, mas só conecta na VPS quando os secrets SSH (`VPS_SSH_*`) estiverem configurados no GitHub.
- O script faz smoke de `/api/health` e de `/`, validando também o frontend servido same-origin.

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
6. Calls `http://127.0.0.1:8000/` from inside the container and validates a frontend marker.
7. Prints the last 80 container log lines.

If any step fails, the script stops before continuing.

## Automatic deploy from GitHub

GitHub Actions runs CI for pull requests and every push para `main`. The workflow lives at
`.github/workflows/ci-cd.yml`. When CI passes on
`main`, the `deploy` job connects to the VPS over SSH, updates the checkout, and runs
the same safe deploy script:

```bash
cd /opt/projetos/financas-agent
git fetch deon main
git checkout main
git pull --ff-only deon main
./scripts/vps_deploy.sh
```

The job refuses to continue when the VPS checkout has tracked local changes. Untracked
machine-local files such as `.cursor/` are ignored by that guard.
The branch update must remain a fast-forward through `git pull --ff-only deon main`.

Required repository secrets:

- `VPS_SSH_HOST`: VPS hostname or IP.
- `VPS_SSH_USER`: SSH user, currently `davi`.
- `VPS_SSH_KEY`: private deploy key allowed to SSH into the VPS.
- `VPS_SSH_FINGERPRINT`: SSH host fingerprint for the VPS.
- `VPS_SSH_PORT`: optional SSH port; defaults to `22`.

Until the required secrets are configured, the workflow keeps CI green and skips the SSH
deploy step with a notice. Once the secrets exist, every successful push to `main`
deploys automatically.

The VPS repository remote used for deploy is `deon`, pointing at
`git@github-deon-fin:deon7769/deon-fin.git`. Keep the production `.env` only on the VPS;
GitHub Actions should not receive Pluggy or analyst provider credentials.

## Environment

The VPS `.env` remains the only real runtime configuration file. Tests install harmless process-local defaults in pytest only so unit tests do not inherit production Basic Auth or call Pluggy unless real credentials are exported explicitly in the shell.

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

Frontend smoke used by the deploy script:

```bash
docker compose exec -T financas-agent python - <<'PY'
import os
import urllib.request as request

url = "http://127.0.0.1:8000/"
username = os.environ.get("APP_USER", "admin")
password = os.environ.get("APP_PASSWORD", "")
req = request.Request(url)
if password:
    import base64
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
resp = request.urlopen(req, timeout=5)
html = resp.read().decode("utf-8", errors="replace")
print(resp.status, "deon-fin" in html or "/_next/" in html)
PY
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
