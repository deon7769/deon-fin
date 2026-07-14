# Static Reference Data Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the sovereign-ratings reference dataset with the portfolio module so the VPS operator can use Git normally while `data/` remains private.

**Architecture:** The immutable JSON moves beside `country_ratings.py` and the loader resolves it with `Path(__file__).with_suffix(".json")`. Runtime financial state remains under the ignored `data/` volume at `0700`/`0600`; the first VPS fast-forward removes the legacy tracked path through a narrow, automatically restored permission window.

**Tech Stack:** Python 3.12+, pathlib, JSON, pytest, Git, Docker Compose, Bash, Next.js/Vitest.

## Global Constraints

- Work from `codex/fase0-static-data-boundary`, based on VPS commit `8587c06`.
- Follow TDD: observe the focused test fail before moving the asset or changing `DATA_PATH`.
- Do not change ratings values, API payloads, Compose volumes, database files, backups, secrets, or permission targets.
- Keep `data/` ignored and private at steady-state modes `0700` for directories and `0600` for files.
- Never run the production Git fast-forward as root.
- Preserve the VPS untracked `.cursor/` and `docs/repasse-2026-07-07.md` paths.
- Do not repair OpenClaw, consolidate `main`, or prune branches in this slice.

---

## File Structure

- `src/agent/portfolio/country_ratings.json`: immutable sovereign-ratings dataset shipped with the portfolio module.
- `src/agent/portfolio/country_ratings.py`: resolves and caches the adjacent JSON without changing the public API.
- `tests/test_country_ratings.py`: owns the asset-location regression contract and existing ratings behavior tests.
- `docs/specs/F4-carteira-investimentos.md`: names the packaged reference-data location.
- `docs/specs/F4.5-investimentos-mapa.md`: names the packaged reference-data location in the map specification and checklist.
- `data/country_ratings.json`: removed tracked legacy location; no runtime data below `data/` is modified.

### Task 1: Move the reference asset with a RED/GREEN contract

**Files:**
- Move: `data/country_ratings.json` -> `src/agent/portfolio/country_ratings.json`
- Modify: `src/agent/portfolio/country_ratings.py:9`
- Modify: `tests/test_country_ratings.py:25`
- Modify: `docs/specs/F4-carteira-investimentos.md:364`
- Modify: `docs/specs/F4.5-investimentos-mapa.md:15,57`

**Interfaces:**
- Consumes: `country_ratings.__file__`, standard-library `Path` and `json`.
- Produces: `DATA_PATH: Path` equal to the loader path with suffix `.json`; existing `load_country_ratings()`, `list_country_ratings()`, and `get_country_rating()` signatures remain unchanged.

- [ ] **Step 1: Write the failing asset-boundary test**

Add this test before `test_load_country_ratings_reads_seeded_dataset_once_per_process`:

```python
def test_country_ratings_dataset_is_packaged_beside_loader():
    import json
    from pathlib import Path

    from src.agent.portfolio import country_ratings

    expected_path = Path(country_ratings.__file__).with_suffix(".json")

    assert country_ratings.DATA_PATH == expected_path
    assert expected_path.is_file()

    payload = json.loads(expected_path.read_text(encoding="utf-8"))
    assert {"US", "BR", "DE", "IN", "RU"} <= set(payload)
```

- [ ] **Step 2: Run the focused test and observe RED**

Run from the worktree root:

```powershell
& 'C:\Users\Escalasoft\Documents\Deon Fin\.venv\Scripts\python.exe' `
  -m pytest tests/test_country_ratings.py::test_country_ratings_dataset_is_packaged_beside_loader -v
```

Expected: FAIL because current `DATA_PATH` ends in `data/country_ratings.json`, not `src/agent/portfolio/country_ratings.json`.

- [ ] **Step 3: Move the JSON without changing its blob**

Run:

```powershell
git mv data/country_ratings.json src/agent/portfolio/country_ratings.json
```

Verify Git recognizes a pure rename:

```powershell
git diff --summary
```

Expected: a rename from `data/country_ratings.json` to `src/agent/portfolio/country_ratings.json` with `100%` similarity.

- [ ] **Step 4: Point the loader to the adjacent asset**

Replace the current `DATA_PATH` assignment with:

```python
DATA_PATH = Path(__file__).with_suffix(".json")
```

Do not change caching, tier calculation, error handling, or response shaping.

- [ ] **Step 5: Update the two F4 specifications**

In `docs/specs/F4-carteira-investimentos.md`, replace:

```text
data/country_ratings.json
```

with:

```text
src/agent/portfolio/country_ratings.json
```

Make the same literal replacement for both occurrences in `docs/specs/F4.5-investimentos-mapa.md`.

- [ ] **Step 6: Run focused GREEN tests**

Run:

```powershell
& 'C:\Users\Escalasoft\Documents\Deon Fin\.venv\Scripts\python.exe' `
  -m pytest tests/test_country_ratings.py -q
```

Expected: `6 passed`.

- [ ] **Step 7: Verify the repository boundary**

Run:

```powershell
git ls-files data
git ls-files src/agent/portfolio/country_ratings.json
git diff --check
git diff --summary
```

Expected:

- `git ls-files data` prints nothing.
- The new `src/agent/portfolio/country_ratings.json` path is printed.
- `git diff --check` exits `0`.
- The JSON is reported as a `100%` rename.

- [ ] **Step 8: Commit the tested asset-boundary change**

```powershell
git add src/agent/portfolio/country_ratings.py `
  src/agent/portfolio/country_ratings.json `
  tests/test_country_ratings.py `
  docs/specs/F4-carteira-investimentos.md `
  docs/specs/F4.5-investimentos-mapa.md
git add -u data/country_ratings.json
git commit -m "fix: package country ratings with portfolio module"
```

### Task 2: Run the complete regression stack and publish to the VPS

**Files:**
- Verify only; no additional source changes are expected.

**Interfaces:**
- Consumes: the Task 1 commit and the existing Python/Node runtimes.
- Produces: a fully verified `codex/fase0-static-data-boundary` branch available as a local branch in the VPS repository.

- [ ] **Step 1: Run the complete backend suite in a writable temp root**

```powershell
New-Item -ItemType Directory -Force '.pytest_cache\local-temp' | Out-Null
$tempPath = (Resolve-Path '.pytest_cache\local-temp').Path
$env:AUTH_SESSION_ENABLED = 'false'
$env:NEXT_PUBLIC_AUTH_ENABLED = 'false'
$env:TEMP = $tempPath
$env:TMP = $tempPath
& 'C:\Users\Escalasoft\Documents\Deon Fin\.venv\Scripts\python.exe' `
  -m pytest -q --basetemp (Join-Path $tempPath 'base')
```

Expected: `499 passed, 5 skipped`; deprecation warnings are allowed.

- [ ] **Step 2: Run frontend Vitest**

From `web/`:

```powershell
npm.cmd test -- --run
```

Expected: `36 passed` files and `152 passed` tests.

- [ ] **Step 3: Run frontend typecheck**

```powershell
npm.cmd run typecheck
```

Expected: exit `0` with no TypeScript errors.

- [ ] **Step 4: Run frontend lint**

```powershell
npm.cmd run lint
```

Expected: exit `0` with no ESLint warnings or errors.

- [ ] **Step 5: Build the frontend export**

```powershell
npm.cmd run build
```

Expected: exit `0` and a refreshed ignored `web/out/` export.

- [ ] **Step 6: Inspect the final branch before publication**

From the worktree root:

```powershell
git status --short --branch
git log -4 --oneline
git show --stat --oneline HEAD
git diff vps/codex/fase0-guardrails...HEAD --check
```

Expected: clean worktree; latest commit is `fix: package country ratings with portfolio module`; diff check exits `0`.

- [ ] **Step 7: Push the verified feature branch to the VPS repository**

```powershell
git push vps codex/fase0-static-data-boundary
```

Expected: the VPS repository receives `refs/heads/codex/fase0-static-data-boundary` without changing its checked-out production branch.

### Task 3: Fast-forward, deploy, and synchronize the production branch

**Files:**
- Runtime migration only: `/opt/projetos/financas-agent/data/country_ratings.json` is removed after content verification.
- No database, backup, secret, or untracked handoff file is changed.

**Interfaces:**
- Consumes: VPS branch `codex/fase0-static-data-boundary` and active branch `codex/fase0-guardrails`.
- Produces: active production branch at the verified target commit, private permissions restored, healthy Docker service, and `deon/codex/fase0-guardrails` synchronized.

- [ ] **Step 1: Verify target blobs and matching content before removal**

Run on the VPS:

```bash
cd /opt/projetos/financas-agent
target=codex/fase0-static-data-boundary
git cat-file -e "$target:src/agent/portfolio/country_ratings.json"
if git cat-file -e "$target:data/country_ratings.json" 2>/dev/null; then
  echo "target still tracks legacy data path" >&2
  exit 1
fi
legacy_sha=$(sudo sha256sum data/country_ratings.json | cut -d' ' -f1)
target_sha=$(git show "$target:src/agent/portfolio/country_ratings.json" | sha256sum | cut -d' ' -f1)
test "$legacy_sha" = "$target_sha"
```

Expected: all commands exit `0`; the legacy file and target blob have identical SHA-256 hashes.

- [ ] **Step 2: Confirm the active tree has only known untracked noise**

```bash
sudo env GIT_OPTIONAL_LOCKS=0 git \
  -c safe.directory=/opt/projetos/financas-agent \
  status --short --branch
```

Expected: branch `codex/fase0-guardrails`, five or more commits ahead of the old GitHub ref, with only `.cursor/` and `docs/repasse-2026-07-07.md` untracked.

- [ ] **Step 3: Perform the one-time safe fast-forward as the normal user**

```bash
set -euo pipefail
repo=/opt/projetos/financas-agent
target=codex/fase0-static-data-boundary
legacy="$repo/data/country_ratings.json"
legacy_stash="/tmp/deon-fin-country-ratings.$$.json"
cd "$repo"

restore_after_failure() {
  status=$?
  trap - EXIT
  if [ "$status" -ne 0 ] && sudo test -f "$legacy_stash"; then
    sudo mv -- "$legacy_stash" "$legacy"
  fi
  sudo chmod 700 "$repo/data"
  exit "$status"
}
trap restore_after_failure EXIT

sudo chmod 711 "$repo/data"
sudo mv -- "$legacy" "$legacy_stash"
git merge --ff-only "$target"

sudo rm -f -- "$legacy_stash"
sudo chmod 700 "$repo/data"
trap - EXIT
```

Expected: fast-forward succeeds without invoking Git through `sudo`; `data/` returns to `0700` even if the merge fails.

- [ ] **Step 4: Run the authoritative VPS deploy**

```bash
cd /opt/projetos/financas-agent
./scripts/vps_deploy.sh
```

Expected:

- timestamped SQLite backup created and rotation applied;
- backend reports `499 passed, 5 skipped`;
- Docker image builds and `financas-agent` is recreated;
- internal health prints `health ok: {"status":"ok"}`;
- frontend smoke prints status `200`.

- [ ] **Step 5: Verify steady-state permissions and Git operability**

```bash
cd /opt/projetos/financas-agent
git status --short --branch
test -z "$(git ls-files data)"
sudo stat -c '%a %U:%G %n' data data/backups data/secrets data/financas.db
```

Expected:

- `git status` emits no permission warning and still preserves the two known untracked paths;
- no tracked path remains below `data/`;
- directories are `700` and `data/financas.db` is `600` under the application UID/GID owner.

- [ ] **Step 6: Verify the packaged asset inside the running container**

```bash
cd /opt/projetos/financas-agent
docker compose exec -T financas-agent \
  test -f /app/src/agent/portfolio/country_ratings.json
docker compose exec -T financas-agent python - <<'PY'
from pathlib import Path

from src.agent.portfolio import country_ratings

expected_path = Path(country_ratings.__file__).with_suffix(".json")
assert country_ratings.DATA_PATH == expected_path
assert expected_path.is_file()
assert country_ratings.get_country_rating("BR")["name"] == "Brasil"
print(expected_path)
PY
```

Expected: the asset path prints from `/app/src/agent/portfolio/` and all assertions pass.

- [ ] **Step 7: Verify the public edge**

```bash
curl -fsS --max-time 10 https://fin.deonlab.tech/api/health
```

Expected: `{"status":"ok"}`.

- [ ] **Step 8: Push the active production history to GitHub**

```bash
cd /opt/projetos/financas-agent
git push deon codex/fase0-guardrails
git rev-list --left-right --count deon/codex/fase0-guardrails...HEAD
```

Expected: push succeeds and divergence is `0  0`.

- [ ] **Step 9: Refresh the Windows view of the VPS and close status**

From the local worktree:

```powershell
git fetch vps --prune
git rev-list --left-right --count HEAD...vps/codex/fase0-guardrails
git status --short --branch
```

Expected: divergence is `0  0`; the worktree remains clean.
