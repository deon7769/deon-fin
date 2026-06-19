# Deon Fin VPS foundation design

Date: 2026-06-19
Project: `/opt/projetos/financas-agent`
Repository: `deon7769/deon-fin`
Runtime host: `minha-vps`

## Context

`financas-agent` is already running on the VPS as a Docker Compose service named
`financas-agent`, behind Traefik at `fin.deonlab.tech`, using SQLite data under
`/opt/projetos/financas-agent/data`.

The production checkout is the operational source of truth. It tracks
`deon/main`, while the original Sergio remote remains configured as `origin`.
The current GitHub repository `deon7769/deon-fin` contains the same deployed
commit. The only untracked item observed before this work was `.cursor/`.

The VPS infrastructure pattern documented in `deon7769/mysecondbrain` is:

- Docker/Compose services with `restart=unless-stopped`.
- Traefik for routing and TLS.
- Manual healthcheck at `/opt/infra-healthcheck.sh`.
- Automatic watchdog at `/opt/infra-watchdog.sh`, triggered every 15 minutes by
  `infra-watchdog.timer`, with Docker auto-heal and Telegram alert when recovery
  fails.
- Loki/Promtail/Grafana already available for logs and observability.
- Host-level backups before risky runtime or data changes.

## Problem

The app is alive, but its development and operational safety loop is weak:

- `pytest` on the VPS currently reports 64 passed and 6 failed because web tests
  inherit production `APP_PASSWORD` from `.env` and therefore receive `401`.
- The Docker image does not include tests, so `docker compose exec ... pytest`
  currently runs zero tests.
- `financas-agent` is not yet covered by `/opt/infra-healthcheck.sh` or
  `/opt/infra-watchdog.sh`.
- The project lacks an explicit VPS deploy/smoke-test procedure.
- SQLite contains real data, so changes must back up `data/financas.db` before
  deploys or migrations.

## Considered approaches

### Approach A: VPS foundation first (recommended)

Fix the test isolation issue, document and script the safe deploy path, add the
app to the existing healthcheck/watchdog coverage, then validate with tests,
Docker rebuild, restart, and smoke checks.

Trade-off: this spends the first slice on operational safety rather than visible
product features. It is the best first step because every future improvement can
then be tested and deployed from the real environment with less risk.

### Approach B: Product/UI first

Start improving the dashboard, categorization, Pluggy flows, cards, or IA
insights immediately.

Trade-off: this creates visible progress sooner, but the current failing test
suite and missing watchdog coverage would make every deploy less trustworthy.

### Approach C: Full infra refactor

Move configuration/secrets, database, monitoring, CI, backup automation, and
deployment into a broader platform pattern at once.

Trade-off: this could be cleaner long-term, but it is too large for the first
slice and risks mixing unrelated changes into a finance app that already handles
real data.

## Design

Use Approach A as the first implementation slice.

### Code and configuration

- Keep production `.env` untouched except if a later explicit change is needed.
- Make tests independent from production `.env` values by setting test-safe
  environment defaults in `tests/conftest.py` before test modules import the web
  app. At minimum, tests should clear `APP_PASSWORD`, disable autosync, and
  provide harmless Pluggy placeholder credentials when real ones are absent.
- Preserve Basic Auth behavior in production: `/api/health` remains public;
  other routes require auth when `APP_PASSWORD` is set.

### Deployment workflow

- Work directly on the VPS checkout, on branch `codex/financas-vps-foundation`.
- Before any deploy/recreate that could touch data, create a timestamped backup
  of `data/financas.db` on the host.
