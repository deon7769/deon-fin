# Bootstrap Credential Retirement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the obsolete plaintext bootstrap credential from the live VPS while preserving session authentication, private-directory permissions, Git state, and public availability.

**Architecture:** This is an operational retirement, not an application change. First publish the approved design and plan by fast-forwarding the active VPS branch, then remove one exact regular file behind strict path, symlink, mode, and parent guards, and finally prove that the VPS, GitHub, container, and public edge remain healthy.

**Tech Stack:** Git, OpenSSH, PowerShell, Bash, GNU coreutils, Docker Compose, curl, PostgreSQL-backed session authentication

## Global Constraints

- Treat `/opt/projetos/financas-agent` on `minha-vps` as the production source of truth.
- Never print, copy, hash, archive, or otherwise read the contents of `data/secrets/initial-auth-owner.txt`.
- Remove only `/opt/projetos/financas-agent/data/secrets/initial-auth-owner.txt` after proving it is a regular non-symlink file at that resolved path.
- Preserve `data/secrets/` at mode `0700`; never widen permissions to make the operation easier.
- Do not change `.env`, `APP_PASSWORD`, `AUTH_PEPPER`, PostgreSQL records, user sessions, or database credentials.
- Do not restart or redeploy the application; no running component references the retired file.
- Preserve the known untracked VPS paths `.cursor/` and `docs/repasse-2026-07-07.md`; do not add, edit, move, or delete them.
- Stop on any unexpected Git change, path mismatch, symlink, permission mismatch, branch divergence, or public-health failure.
- Do not claim forensic secure erasure; this plan performs a normal filesystem unlink.

---

### Task 1: Publish the Approved Operational Documentation

**Files:**
- Verify: `docs/superpowers/specs/2026-07-14-bootstrap-credential-retirement-design.md`
- Verify: `docs/superpowers/plans/2026-07-14-bootstrap-credential-retirement.md`
- Modify on the VPS by fast-forward only: Git branch `codex/fase0-guardrails`

**Interfaces:**
- Consumes: local branch `codex/bootstrap-secret-retirement` based on `vps/codex/fase0-guardrails`
- Produces: the design and plan reachable from the active VPS branch and `deon/codex/fase0-guardrails`

- [ ] **Step 1: Verify the local branch contains only the approved documentation commits**

Run from PowerShell:

```powershell
$worktree = 'C:\tmp\deon-fin-worktrees\codex-bootstrap-secret-retirement'
$base = 'vps/codex/fase0-guardrails'
$expected = @(
  'docs/superpowers/plans/2026-07-14-bootstrap-credential-retirement.md',
  'docs/superpowers/specs/2026-07-14-bootstrap-credential-retirement-design.md'
)

git -C $worktree fetch vps 'codex/fase0-guardrails:refs/remotes/vps/codex/fase0-guardrails'
if ($LASTEXITCODE -ne 0) {
  throw 'Could not refresh the production base'
}

if (git -C $worktree status --porcelain) {
  throw 'Worktree must be clean before publication'
}

$actual = @(git -C $worktree diff --name-only "$base..HEAD" | Sort-Object)
$expected = @($expected | Sort-Object)
if (Compare-Object $expected $actual) {
  throw "Unexpected files relative to $base"
}

git -C $worktree log --oneline "$base..HEAD"
```

Expected: clean worktree; exactly the approved design and plan files are changed relative to the VPS base; the log contains only the approved documentation commits.

- [ ] **Step 2: Re-run the backend and frontend baselines**

Run from PowerShell:

```powershell
$worktree = 'C:\tmp\deon-fin-worktrees\codex-bootstrap-secret-retirement'
$python = 'C:\Users\Escalasoft\Documents\Deon Fin\.venv\Scripts\python.exe'
$cache = Join-Path $worktree '.pytest_cache'
$basetemp = Join-Path $cache 'retirement-baseline'
New-Item -ItemType Directory -Path $cache -Force | Out-Null

Push-Location $worktree
try {
  & $python -m pytest -q "--basetemp=$basetemp"
  if ($LASTEXITCODE -ne 0) {
    throw 'Backend baseline failed'
  }
} finally {
  Pop-Location
}

Push-Location (Join-Path $worktree 'web')
try {
  npm.cmd test -- --run
  if ($LASTEXITCODE -ne 0) {
    throw 'Frontend baseline failed'
  }
} finally {
  Pop-Location
}
```

Expected: backend reports `499 passed, 5 skipped`; frontend reports `36 passed` test files and `152 passed` tests.

- [ ] **Step 3: Push the documentation branch to the VPS repository**

Run:

```powershell
$worktree = 'C:\tmp\deon-fin-worktrees\codex-bootstrap-secret-retirement'
git -C $worktree push vps codex/bootstrap-secret-retirement
```

Expected: `codex/bootstrap-secret-retirement` is created or fast-forwarded on the VPS remote without force-push.

- [ ] **Step 4: Fast-forward the active VPS branch and publish it to GitHub**

Run this literal remote script from PowerShell:

```powershell
$remoteScript = @'
set -euo pipefail
repo=/opt/projetos/financas-agent
cd "$repo"

test "$(git branch --show-current)" = "codex/fase0-guardrails"

expected_status='?? .cursor/
?? docs/repasse-2026-07-07.md'
actual_status=$(git status --porcelain=v1)
test "$actual_status" = "$expected_status"

git merge-base --is-ancestor HEAD codex/bootstrap-secret-retirement
git merge --ff-only codex/bootstrap-secret-retirement
git push deon codex/fase0-guardrails

set -- $(git rev-list --left-right --count deon/codex/fase0-guardrails...HEAD)
test "$1" = "0"
test "$2" = "0"
echo "DOCS_PUBLISHED head=$(git rev-parse HEAD)"
'@

$remoteScript | ssh minha-vps "tr -d '\r' | bash -s"
if ($LASTEXITCODE -ne 0) {
  throw 'Documentation publication failed'
}
```

Expected: output starts with `DOCS_PUBLISHED head=` followed by a 40-character Git object id, and the branch has zero divergence from `deon/codex/fase0-guardrails`. Do not run `scripts/vps_deploy.sh`; documentation does not change the image.

---

### Task 2: Retire the Obsolete Bootstrap Credential

**Files:**
- Delete on the VPS host: `/opt/projetos/financas-agent/data/secrets/initial-auth-owner.txt`
- Preserve: `/opt/projetos/financas-agent/data/secrets/`
- Preserve: `/opt/projetos/financas-agent/.env`

**Interfaces:**
- Consumes: user confirmation that the session-login password was changed; private directory mode `0700`; stale file mode `0600`
- Produces: absent plaintext bootstrap artifact with no application, environment, or database mutation

- [ ] **Step 1: Run the metadata-only preflight**

Run this literal remote script from PowerShell:

```powershell
$preflight = @'
set -euo pipefail
repo=/opt/projetos/financas-agent
repo_real=$(readlink -f "$repo")
secrets="$repo_real/data/secrets"
target="$secrets/initial-auth-owner.txt"

test "$repo_real" = "/opt/projetos/financas-agent"
cd "$repo_real"
expected_status='?? .cursor/
?? docs/repasse-2026-07-07.md'
actual_status=$(git status --porcelain=v1)
test "$actual_status" = "$expected_status"
sudo test -d "$secrets"
sudo test ! -L "$secrets"
test "$(sudo readlink -f "$secrets")" = "/opt/projetos/financas-agent/data/secrets"
test "$(sudo stat -c '%a' "$secrets")" = "700"
test "$(sudo stat -c '%U:%G' "$secrets")" = "ubuntu:ubuntu"

if sudo test -L "$target"; then
  echo 'TARGET_INVALID_SYMLINK' >&2
  exit 1
elif sudo test -e "$target"; then
  sudo test -f "$target"
  sudo test ! -L "$target"
  test "$(sudo readlink -f "$target")" = "$target"
  test "$(sudo stat -c '%a' "$target")" = "600"
  test "$(sudo stat -c '%U:%G' "$target")" = "ubuntu:ubuntu"
  sudo stat -c 'TARGET_PRESENT mode=%a owner=%U:%G bytes=%s modified=%y' "$target"
else
  echo 'TARGET_ALREADY_ABSENT'
fi
'@

$preflight | ssh minha-vps "tr -d '\r' | bash -s"
if ($LASTEXITCODE -ne 0) {
  throw 'Credential-retirement preflight failed'
}
```

Expected: either `TARGET_PRESENT` with metadata only, or `TARGET_ALREADY_ABSENT`. No command may display file contents.

- [ ] **Step 2: Recheck the guards and unlink the exact file**

Run:

```powershell
$retire = @'
set -euo pipefail
repo=/opt/projetos/financas-agent
repo_real=$(readlink -f "$repo")
secrets="$repo_real/data/secrets"
target="$secrets/initial-auth-owner.txt"

test "$repo_real" = "/opt/projetos/financas-agent"
sudo test -d "$secrets"
sudo test ! -L "$secrets"
test "$(sudo readlink -f "$secrets")" = "/opt/projetos/financas-agent/data/secrets"
test "$(sudo stat -c '%a' "$secrets")" = "700"
test "$(sudo stat -c '%U:%G' "$secrets")" = "ubuntu:ubuntu"

if sudo test -L "$target"; then
  echo 'TARGET_INVALID_SYMLINK' >&2
  exit 1
elif sudo test -e "$target"; then
  sudo test -f "$target"
  sudo test ! -L "$target"
  test "$(sudo readlink -f "$target")" = "$target"
  test "$(sudo stat -c '%a' "$target")" = "600"
  test "$(sudo stat -c '%U:%G' "$target")" = "ubuntu:ubuntu"
  cd "$repo_real"
  expected_status='?? .cursor/
?? docs/repasse-2026-07-07.md'
  actual_status=$(git status --porcelain=v1)
  test "$actual_status" = "$expected_status"
  sudo rm -- "$target"
  echo 'TARGET_REMOVED'
else
  echo 'TARGET_ALREADY_ABSENT'
fi

sudo test ! -e "$target"
sudo test ! -L "$target"
test "$(sudo stat -c '%a' "$secrets")" = "700"
test "$(sudo stat -c '%U:%G' "$secrets")" = "ubuntu:ubuntu"
'@

$retire | ssh minha-vps "tr -d '\r' | bash -s"
if ($LASTEXITCODE -ne 0) {
  throw 'Credential retirement failed'
}
```

Expected: `TARGET_REMOVED` on the first execution or `TARGET_ALREADY_ABSENT` on an idempotent rerun; the script exits zero only when the target is absent and the directory remains `0700`.

- [ ] **Step 3: Verify the host invariants without restarting the application**

Run:

```powershell
$verifyHost = @'
set -euo pipefail
repo=/opt/projetos/financas-agent
repo_real=$(readlink -f "$repo")
secrets="$repo_real/data/secrets"
target="$secrets/initial-auth-owner.txt"

test "$repo_real" = "/opt/projetos/financas-agent"
sudo test -d "$secrets"
sudo test ! -L "$secrets"
test "$(sudo readlink -f "$secrets")" = "/opt/projetos/financas-agent/data/secrets"
test "$(sudo stat -c '%a' "$secrets")" = "700"
test "$(sudo stat -c '%U:%G' "$secrets")" = "ubuntu:ubuntu"
sudo test ! -e "$target"
sudo test ! -L "$target"

cd "$repo_real"

expected_status='?? .cursor/
?? docs/repasse-2026-07-07.md'
actual_status=$(git status --porcelain=v1)
test "$actual_status" = "$expected_status"

set -- $(git rev-list --left-right --count deon/codex/fase0-guardrails...HEAD)
test "$1" = "0"
test "$2" = "0"
container=$(docker ps --filter 'status=running' --format '{{.Names}}' | grep -Fx 'financas-agent' || true)
test "$container" = "financas-agent"
echo "CONTAINER=$container STATUS=running"
echo "HOST_OK head=$(git rev-parse HEAD) secret_dir_mode=$(sudo stat -c '%a' "$secrets") secret_dir_owner=$(sudo stat -c '%U:%G' "$secrets")"
'@

$verifyHost | ssh minha-vps "tr -d '\r' | bash -s"
if ($LASTEXITCODE -ne 0) {
  throw 'Host verification failed'
}
```

Expected: the exact `financas-agent` container is running; `HOST_OK` reports the published head, `secret_dir_mode=700`, and `secret_dir_owner=ubuntu:ubuntu`; Git has no unexpected changes.

---

### Task 3: Verify the Public Edge and Final Provenance

**Files:**
- Verify only: local branch `codex/bootstrap-secret-retirement`
- Verify only: VPS/GitHub branch `codex/fase0-guardrails`
- Verify only: `https://fin.deonlab.tech/` and `https://fin.deonlab.tech/api/health`

**Interfaces:**
- Consumes: completed host retirement from Task 2
- Produces: evidence that local documentation, VPS production, GitHub, and the public edge are consistent

- [ ] **Step 1: Verify the public health response and login redirect**

Run from PowerShell:

```powershell
$health = curl.exe -fsS 'https://fin.deonlab.tech/api/health'
if ($LASTEXITCODE -ne 0 -or $health -notmatch '"status"\s*:\s*"ok"') {
  throw "Unexpected public health response: $health"
}

$rootStatus = curl.exe -sS -o NUL -w '%{http_code}' 'https://fin.deonlab.tech/'
if ($LASTEXITCODE -ne 0 -or $rootStatus -ne '303') {
  throw "Unexpected root status: $rootStatus"
}

$rootHeaders = curl.exe -sSI 'https://fin.deonlab.tech/'
$rootHeaderText = $rootHeaders -join "`n"
if ($LASTEXITCODE -ne 0 -or $rootHeaderText -notmatch '(?im)^location:\s*/login\s*$') {
  throw 'Root response does not redirect to /login'
}

Write-Output "PUBLIC_OK health=$health root_status=$rootStatus location=/login"
```

Expected: `PUBLIC_OK health={"status":"ok"} root_status=303 location=/login`.

- [ ] **Step 2: Compare the real VPS and GitHub object ids**

Run:

```powershell
$vpsHead = (ssh minha-vps 'git -C /opt/projetos/financas-agent rev-parse HEAD').Trim()
if ($LASTEXITCODE -ne 0) {
  throw 'Could not read VPS HEAD'
}

$githubLine = ssh minha-vps 'git -C /opt/projetos/financas-agent ls-remote deon refs/heads/codex/fase0-guardrails'
if ($LASTEXITCODE -ne 0) {
  throw 'Could not read GitHub branch from the VPS'
}
$githubHead = (($githubLine -split '\s+')[0]).Trim()

if ($vpsHead -ne $githubHead) {
  throw "VPS/GitHub divergence: vps=$vpsHead github=$githubHead"
}

Write-Output "REMOTE_OK vps=$vpsHead github=$githubHead"
```

Expected: identical 40-character object ids for VPS and GitHub.

- [ ] **Step 3: Refresh the local VPS refs and verify the worktree remains clean**

Run:

```powershell
$worktree = 'C:\tmp\deon-fin-worktrees\codex-bootstrap-secret-retirement'
git -C $worktree fetch vps `
  'codex/fase0-guardrails:refs/remotes/vps/codex/fase0-guardrails' `
  'codex/bootstrap-secret-retirement:refs/remotes/vps/codex/bootstrap-secret-retirement'
if ($LASTEXITCODE -ne 0) {
  throw 'Could not refresh VPS refs'
}

if (git -C $worktree status --porcelain) {
  throw 'Local worktree is not clean'
}

$productionHead = git -C $worktree rev-parse vps/codex/fase0-guardrails
$featureHead = git -C $worktree rev-parse HEAD
if ($productionHead -ne $featureHead) {
  throw "Local feature and production refs differ: feature=$featureHead production=$productionHead"
}

$localBranch = (git -C $worktree branch --show-current).Trim()
if ($localBranch -ne 'codex/bootstrap-secret-retirement') {
  throw "Unexpected local branch: $localBranch"
}

Write-Output "LOCAL_OK branch=$localBranch head=$featureHead status=clean"
```

Expected: local worktree clean and the local feature head identical to `vps/codex/fase0-guardrails`. No post-retirement commit is created because the deleted file is ignored host state, not repository content.
