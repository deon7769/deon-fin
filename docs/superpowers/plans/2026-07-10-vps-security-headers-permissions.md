# VPS Security Headers and File Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add security headers at Traefik and keep Deon Fin data, secrets, and existing backups private to the application owner.

**Architecture:** Docker Compose labels declare `financas-security@docker` and attach it after `tailscale-only@docker`. `scripts/vps_deploy.sh` keeps its existing backup flow, then applies a private umask and deterministic file modes after ownership repair.

**Tech Stack:** Docker Compose, Traefik Docker labels, Bash, pytest.

## Global Constraints

- Work on the active VPS repository `/opt/projetos/financas-agent`.
- Do not encrypt, relocate, schedule, or redesign backups.
- Preserve session auth, `tailscale-only@docker`, and the non-root container user.
- Add no dependency and preserve untracked `.cursor/` and `docs/repasse-2026-07-07.md`.
- Write and observe a failing test before each production change.

---

## File Structure

- `docker-compose.yml`: security middleware and router chain.
- `tests/test_dockerfile.py`: Compose security contract.
- `scripts/vps_deploy.sh`: private umask and modes.
- `tests/test_vps_deploy_script.py`: deploy permission contract.

### Task 1: Traefik edge headers

**Files:**
- Modify: `tests/test_dockerfile.py`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: router `financas` and `tailscale-only@docker`.
- Produces: middleware `financas-security@docker` with HSTS, CSP, nosniff, frame denial, referrer policy, and permissions policy.

- [ ] **Step 1: Write the failing test**

```python
def test_compose_applies_security_headers_at_the_traefik_edge():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    labels = compose["services"]["financas-agent"]["labels"]

    assert "traefik.http.routers.financas.middlewares=tailscale-only@docker,financas-security@docker" in labels
    assert "traefik.http.middlewares.financas-security.headers.stsSeconds=15552000" in labels
    assert "traefik.http.middlewares.financas-security.headers.contentTypeNosniff=true" in labels
    assert "traefik.http.middlewares.financas-security.headers.frameDeny=true" in labels
    assert "traefik.http.middlewares.financas-security.headers.referrerPolicy=strict-origin-when-cross-origin" in labels
    assert "traefik.http.middlewares.financas-security.headers.permissionsPolicy=geolocation=(), camera=(), microphone=(), payment=(), usb=()" in labels
    csp = next(label for label in labels if "contentSecurityPolicy=" in label)
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "https://cdn.pluggy.ai" in csp
    assert "https://*.pluggy.ai" in csp
    assert "https://*.basemaps.cartocdn.com" in csp
```

- [ ] **Step 2: Verify RED**

Run `AUTH_SESSION_ENABLED=false NEXT_PUBLIC_AUTH_ENABLED=false .venv/bin/python -m pytest -q tests/test_dockerfile.py::test_compose_applies_security_headers_at_the_traefik_edge`.

Expected: FAIL because the middleware labels do not exist.

- [ ] **Step 3: Add the minimal Compose labels**

Replace the router chain and add these labels under `financas-agent`:

```yaml
- "traefik.http.routers.financas.middlewares=tailscale-only@docker,financas-security@docker"
- "traefik.http.middlewares.financas-security.headers.stsSeconds=15552000"
- "traefik.http.middlewares.financas-security.headers.contentTypeNosniff=true"
- "traefik.http.middlewares.financas-security.headers.frameDeny=true"
- "traefik.http.middlewares.financas-security.headers.referrerPolicy=strict-origin-when-cross-origin"
- "traefik.http.middlewares.financas-security.headers.permissionsPolicy=geolocation=(), camera=(), microphone=(), payment=(), usb=()"
- "traefik.http.middlewares.financas-security.headers.contentSecurityPolicy=default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self' 'unsafe-inline' https://cdn.pluggy.ai; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.basemaps.cartocdn.com; font-src 'self' data:; connect-src 'self' https://*.pluggy.ai; frame-src https://*.pluggy.ai"
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
AUTH_SESSION_ENABLED=false NEXT_PUBLIC_AUTH_ENABLED=false .venv/bin/python -m pytest -q tests/test_dockerfile.py::test_compose_applies_security_headers_at_the_traefik_edge
docker compose config --quiet
```

Expected: test passes and Compose exits `0`.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml tests/test_dockerfile.py
git commit -m "feat: add Traefik security headers"
```

### Task 2: Private data modes

**Files:**
- Modify: `tests/test_vps_deploy_script.py`
- Modify: `scripts/vps_deploy.sh`

**Interfaces:**
- Consumes: `ROOT`, `backup_dir`, and `ensure_data_ownership()`.
- Produces: `ensure_private_permissions()`, called after ownership repair and before pytest.

- [ ] **Step 1: Write the failing test**

```python
def test_deploy_enforces_private_data_and_backup_permissions():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "umask 077" in script
    assert "ensure_private_permissions()" in script
    assert 'chmod 600 "$ROOT/.env"' in script
    assert 'chmod 700 "$private_dir"' in script
    assert 'find "$data_dir" -type f -exec chmod 600 {} +' in script
    before_pytest = script.split('echo "== pytest =="', 1)[0]
    assert before_pytest.index("ensure_data_ownership") < before_pytest.index("ensure_private_permissions")
```

- [ ] **Step 2: Verify RED**

Run `AUTH_SESSION_ENABLED=false NEXT_PUBLIC_AUTH_ENABLED=false .venv/bin/python -m pytest -q tests/test_vps_deploy_script.py::test_deploy_enforces_private_data_and_backup_permissions`.

Expected: FAIL because the private-permission helper is absent.

- [ ] **Step 3: Add the minimal Bash implementation**

Immediately after `set -euo pipefail`, add `umask 077`. Define this helper after `ensure_data_ownership()` and call it immediately after the ownership call:

```bash
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

ensure_data_ownership
