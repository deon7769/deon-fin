# F3.1 Deploy Same-Origin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the exported Next.js app from the FastAPI container at `/`, keep the API at `/api`, preserve the legacy UI at `/legacy`, and make the VPS deploy script smoke both backend and frontend.

**Architecture:** Export `web/` as static assets (`web/out`) during Docker build, copy them into `/app/web_dist`, and let FastAPI serve `/_next/*`, static exported files, and SPA fallbacks after all `/api/*` routes and legacy `/static` assets are registered. Keep a `LEGACY_UI=1` rollback toggle so `/` can render the old Jinja page without rebuilding the image.

**Tech Stack:** FastAPI, Starlette `StaticFiles`, pytest/TestClient, Docker multi-stage build, Next.js App Router static export, Node 24, npm/Vitest/TypeScript/ESLint, Bash deploy script.

---

### Task 1: Backend RED For SPA Routing

**Files:**
- Create: `tests/test_web_spa.py`
- Modify if needed: `tests/test_web_app.py`

- [ ] **Step 1: Write static fixture helpers**

In `tests/test_web_spa.py`, create a temporary exported app structure:

```text
tmp_path/web_dist/
  index.html
  metas/index.html
  _next/static/app.js
```

Use `monkeypatch.setenv("WEB_DIST_DIR", str(tmp_web_dist))` before creating the app. Use a clear marker in the HTML such as `data-app="deon-fin-next"` and a script path containing `/_next/static/app.js`.

- [ ] **Step 2: Write failing root and fallback tests**

Cover:
- `GET /` serves exported Next HTML when `WEB_DIST_DIR` exists and `LEGACY_UI` is not enabled.
- `GET /metas?month=2026-06` returns the SPA shell or exported route HTML, not a JSON 404.
- `GET /_next/static/app.js` returns the static asset.

- [ ] **Step 3: Write failing precedence tests**

Cover:
- `GET /api/health` still returns `{"status": "ok"}`.
- `GET /api/does-not-exist` returns a JSON 404/error envelope, not HTML.
- `GET /static/app.js` still serves the legacy static asset if present.

- [ ] **Step 4: Write failing legacy rollback tests**

Cover:
- `GET /legacy` renders the old Pluggy/Jinja UI.
- `LEGACY_UI=1` makes `GET /` render the old Pluggy/Jinja UI even when `WEB_DIST_DIR` exists.
- When `WEB_DIST_DIR` is absent in local dev, `GET /` falls back to the legacy UI instead of 404.

- [ ] **Step 5: Verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_spa.py tests/test_web_app.py -q
```

Expected: failures for missing `/legacy`, missing SPA serving, and/or root still serving the legacy UI.

### Task 2: FastAPI SPA Serving GREEN

**Files:**
- Modify: `src/web/app.py`
- Modify: `tests/test_web_app.py`
- Keep existing: `src/web/static/*`, `src/web/templates/*`

- [ ] **Step 1: Add config helpers**

Add app-level helpers that are easy to test:
- `WEB_DIST_DIR = os.environ.get("WEB_DIST_DIR", "web_dist")`
- `LEGACY_UI = os.environ.get("LEGACY_UI", "").lower() in {"1", "true", "yes"}`
- `_web_dist_dir() -> Path`
- `_legacy_ui_enabled() -> bool`
- `_next_index_exists() -> bool`

Read env inside helpers, not only at import time, so pytest `monkeypatch` works.

- [ ] **Step 2: Move legacy root into a reusable function**

Extract the current `@app.get("/")` Jinja response into a helper like `_render_legacy_index(request)`. Register:
- `GET /legacy` always renders the legacy page.
- `GET /` renders legacy only when `LEGACY_UI=1` or when no Next export is available.

Keep `/api/health` public behavior unchanged.

- [ ] **Step 3: Serve Next assets before the catch-all**

When `WEB_DIST_DIR/_next` exists, mount it:

```python
app.mount("/_next", StaticFiles(directory=str(web_dist / "_next")), name="next-assets")
```

Do not change the existing `/static` mount for the legacy app.

- [ ] **Step 4: Add SPA/static fallback after routers**

Register a final catch-all route after all API routers and mounts. It must:
- reject `api`, `static`, and `_next` prefixes with `HTTPException(status_code=404)`;
- return exact exported files when they exist;
- return `full_path/index.html` when it exists;
- return `index.html` for app routes like `/transacoes`;
- return the legacy UI only when the export does not exist and the path is `/`;
- set `Cache-Control: no-cache` for HTML responses.

- [ ] **Step 5: Verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_spa.py tests/test_web_app.py tests/test_router_structure.py -q
```

Expected: all selected tests pass.

### Task 3: Next Static Export And API Base

**Files:**
- Modify: `web/next.config.mjs`
- Modify: `web/lib/api.ts`
- Modify: `web/.env.example` or create it if missing
- Do not commit: `web/.env.local`

- [ ] **Step 1: Configure static export**

Set:

```js
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};
```

Keep any existing config that is still required by the app.

- [ ] **Step 2: Default the frontend API to same-origin**

In `web/lib/api.ts`, make production-friendly default behavior:

```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";
```

Keep dev support through `web/.env.local` with:

```text
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
```

Document this in `web/.env.example`.

- [ ] **Step 3: Verify frontend export**

Run:

```powershell
cd web
npm test -- --run
npm run lint
npm run typecheck
npm run build
cd ..
```

Expected: `web/out/` exists and contains route HTML plus `/_next` assets.

### Task 4: Docker Multi-Stage Build

**Files:**
- Modify: `Dockerfile`
- Possibly modify: `.dockerignore`

- [ ] **Step 1: Add Node build stage**

Use the same Node major version as CI:

```dockerfile
FROM node:24-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=/api
RUN npm run build
```

- [ ] **Step 2: Copy the export into the Python image**

After Python dependencies and source copy, include:

```dockerfile
COPY --from=web /web/out ./web_dist
```

Do not install Node in the runtime stage.

- [ ] **Step 3: Keep runtime behavior unchanged**

Preserve:
- `WORKDIR /app`
- `/app/data`
- exposed port `8000`
- `CMD ["python", "-m", "src.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]`

- [ ] **Step 4: Verify image builds**

Run:

```powershell
docker build -t financas-agent:f3-1 .
```

Expected: image builds successfully and includes `/app/web_dist/index.html`.

### Task 5: Deploy Script Frontend Smoke

**Files:**
- Modify: `scripts/vps_deploy.sh`
- Modify: `tests/test_vps_deploy_script.py`

- [ ] **Step 1: Add RED script test**

Extend `tests/test_vps_deploy_script.py` to assert that the deploy script checks:
- `/api/health`
- `/`
- an HTML marker such as `deon-fin` or `/_next/`
- Basic Auth headers when `APP_PASSWORD` exists

- [ ] **Step 2: Add frontend smoke after health smoke**

In `scripts/vps_deploy.sh`, after `/api/health` succeeds, run a container-local Python smoke that:
- builds a request for `http://127.0.0.1:8000/`;
- reads `APP_USER` and `APP_PASSWORD` from container env;
- adds `Authorization: Basic ...` when password is configured;
- requires status 200;
- requires the HTML to include `deon-fin`, `/_next/`, or another stable app marker.

- [ ] **Step 3: Verify deploy script tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_vps_deploy_script.py -q
```

Expected: deploy script structural test passes.

### Task 6: Full Verification, Commit, CI, VPS

**Files:**
- All changed files.

- [ ] **Step 1: Local full verification**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
cd web
npm test -- --run
npm run lint
npm run typecheck
npm run build
cd ..
docker build -t financas-agent:f3-1 .
git diff --check
```

- [ ] **Step 2: Commit and push to main**

Use a conventional commit, for example:

```text
feat: serve next app same-origin
```

Push to `origin/main`.

- [ ] **Step 3: Wait for GitHub Actions**

Confirm the `CI/CD` workflow passes for the pushed commit before touching production.

- [ ] **Step 4: Deploy on the VPS**

On `minha-vps`:

```bash
cd /opt/projetos/financas-agent
git fetch deon main
git checkout main
git pull --ff-only deon main
./scripts/vps_deploy.sh
```

Expected deploy evidence:
- timestamped backup under `data/backups/`;
- remote pytest passes;
- Docker image rebuilds;
- `/api/health` smoke passes;
- `/` frontend smoke passes;
- `docker compose logs --tail=80 financas-agent` has no startup exception.

- [ ] **Step 5: Browser smoke**

Verify:
- `https://fin.deonlab.tech/` renders the Next app;
- refresh works on `/metas`, `/orcamento`, `/transacoes`, `/faturas`, `/contas`;
- `/legacy` renders the old Pluggy page;
- `/api/health` still returns JSON.
