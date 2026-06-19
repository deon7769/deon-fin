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
