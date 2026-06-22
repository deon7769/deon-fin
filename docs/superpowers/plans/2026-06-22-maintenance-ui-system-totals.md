# Maintenance UI And System Totals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize Manutencao, switch primary UI accent to blue, and add the first SQL-backed policy layer for accounts and movement types included in system totals.

**Architecture:** Keep fixed family data and legacy overrides compatible, but stop adding new operational policy to JSON. Store total-inclusion settings in SQLite, expose them through a focused maintenance endpoint, and render them in the Next Manutencao page as current UI panels instead of generic legacy spreadsheets.

**Tech Stack:** FastAPI, SQLite migrations, repository modules, Next.js static app, React Query, Tailwind tokens, Vitest, pytest.

---

### Task 1: Blue Accent Tokens And Primary Button Primitive

**Files:**
- Modify: `web/app/globals.css`
- Modify: `web/tailwind.config.ts`
- Create: `web/lib/uiClasses.ts`
- Modify: representative primary-button call sites as needed
- Test: `web/tests/tailwind-config.test.ts`

- [ ] **Step 1: Write failing token tests**
  Add tests that assert `accent` maps to `var(--color-accent)`, `accentFg` maps to `var(--color-accent-fg)`, `globals.css` no longer uses `#f5b301` or `#b57e00` for `--color-accent`, and source does not use `accent-[var(--accent)]`.

- [ ] **Step 2: Run token tests red**
  Run: `npm.cmd test -- tailwind-config.test.ts --run` from `web`.
  Expected: fail because `accentFg` and blue tokens are absent.

- [ ] **Step 3: Implement tokens and helper**
  Add `--color-accent: #2563eb`, light `#1d4ed8`, and `--color-accent-fg: #ffffff`; map `accentFg`; add `primaryButtonClass` using `bg-accent text-accentFg`.

- [ ] **Step 4: Replace broken CSS var references**
  Replace `accent-[var(--accent)]` with `accent-accent`.

- [ ] **Step 5: Verify**
  Run: `npm.cmd test -- tailwind-config.test.ts --run`, `npm.cmd run lint`, `npm.cmd run typecheck`.

### Task 2: SQL Policy For System Totals

**Files:**
- Modify: `src/storage/migrations.py`
- Create: `src/web/repositories/system_totals_repo.py`
- Modify: `src/web/app.py` or add/import a focused router
- Test: `tests/test_migrations.py`
- Test: `tests/test_system_totals_repo.py`
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Write failing migration/repo/API tests**
  Cover creation of `account_total_settings`, `movement_total_settings`, default movement seed, default include behavior, account toggle persistence, movement toggle persistence, and `/api/maintenance/system-totals` response/update contract.

- [ ] **Step 2: Run tests red**
  Run targeted pytest for the new tests.
  Expected: fail because tables, repo, and endpoint do not exist.

- [ ] **Step 3: Implement migrations**
  Add idempotent migration after the current latest version. Seed movement keys: `income`, `expense`, `refund`, `internal_transfer`, `card_payment`, `investment`, `financial_cost`, `other_non_spending`.

- [ ] **Step 4: Implement repository**
  Add functions to list policy rows with account labels, update account settings, update movement settings, and classify movement rows using existing sign/category helpers.

- [ ] **Step 5: Implement endpoint**
  Add GET/PATCH endpoint under `/api/maintenance/system-totals`.

- [ ] **Step 6: Verify targeted tests**
  Run migration, repo, and API tests.

### Task 3: Apply Account Policy To First Aggregates

**Files:**
- Modify: `src/web/repositories/painel_repo.py`
- Modify: `src/web/repositories/budget_repo.py`
- Modify: `src/web/repositories/savings_repo.py` if budget surplus needs explicit propagation
- Modify: `src/web/repositories/accounts_repo.py`
- Test: `tests/test_painel.py`
- Test: `tests/test_budget_api.py`
- Test: `tests/test_accounts_api.py`

- [ ] **Step 1: Write failing aggregate tests**
  Excluding an account's transactions removes them from painel summary/history/by-tag and budget/metas. Excluding an account balance removes it from accounts balance totals.

- [ ] **Step 2: Run tests red**
  Run targeted pytest.
  Expected: fail because aggregate queries ignore account settings.

- [ ] **Step 3: Apply include_transactions**
  Join/filter against `account_total_settings` with default included behavior in painel and budget visible transaction queries.

- [ ] **Step 4: Apply include_balance**
  Join/filter account balance totals in painel/accounts overview.

- [ ] **Step 5: Verify targeted tests**
  Run targeted pytest.

### Task 4: Manutencao UI 2.0 With Totals Policy Box

**Files:**
- Modify: `web/lib/maintenance.ts`
- Modify: `web/hooks/useMaintenance.ts`
- Create: `web/components/manutencao/SystemTotalsPolicyPanel.tsx`
- Modify: `web/app/(app)/manutencao/page.tsx`
- Test: `web/tests/maintenance.test.ts`
- Test: new or existing frontend component tests

- [ ] **Step 1: Write failing frontend tests**
  Cover helper mapping for system-totals policy, rendering of account and movement toggles, and the absence of the giant single editor-only flow as the primary Manutencao shape.

- [ ] **Step 2: Run tests red**
  Run: `npm.cmd test -- maintenance.test.ts --run`.

- [ ] **Step 3: Add hooks/types**
  Add types and React Query hooks for GET/PATCH `/maintenance/system-totals`.

- [ ] **Step 4: Add policy panel**
  Render two compact tables/lists: accounts and movement types. Include labels explaining whether they count in balances and transaction totals.

- [ ] **Step 5: Reorganize Manutencao page**
  Keep current fixed-data editor compatible, but split the page into clearer sections and place the system totals box near the top.

- [ ] **Step 6: Verify frontend tests**
  Run targeted Vitest, lint, and typecheck.

### Task 5: Full Verification And Deploy

**Files:**
- No source edits unless verification finds a defect.

- [ ] **Step 1: Run full backend tests**
  Run: `.\\.venv\\Scripts\\python.exe -m pytest -q`.

- [ ] **Step 2: Run full frontend checks**
  Run from `web`: `npm.cmd test -- --run`, `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run build`.

- [ ] **Step 3: Code review**
  Dispatch final code review subagent, fix any important issues, repeat targeted verification.

- [ ] **Step 4: Commit**
  Commit with message `feat: add maintenance totals policy`.

- [ ] **Step 5: Push and deploy**
  Push branch to `vps`, fast-forward `/opt/projetos/financas-agent`, run `./scripts/vps_deploy.sh`, and confirm health/frontend smoke.
