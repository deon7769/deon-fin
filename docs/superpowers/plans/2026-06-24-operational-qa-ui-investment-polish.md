# Operational QA UI And Investment Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir a próxima fatia de QA operacional: sidebar fixa, ordenação de cartões em Faturas mais clara e preservação de classe manual em investimentos Pluggy.

**Architecture:** Manter mudanças pequenas e compatíveis com os padrões existentes. UI segue os componentes atuais em React/Next com testes Vitest por markup estático; backend segue `portfolio_repo` com regressões em pytest.

**Tech Stack:** Python, FastAPI, SQLite, pytest, Next.js, React, Vitest, Tailwind.

---

### Task 1: Sidebar realmente fixa no desktop

**Files:**
- Modify: `web/components/layout/Sidebar.tsx`
- Modify: `web/tests/sidebar.test.ts`

- [ ] **Step 1: Write the failing test**

Update `web/tests/sidebar.test.ts` in `keeps the desktop sidebar pinned while page content scrolls` to expect the desktop sidebar to render as `fixed left-0 top-0` and a desktop spacer preserving the layout width.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm.cmd --prefix web test -- --run web/tests/sidebar.test.ts`

Expected: FAIL because the current sidebar uses `sticky top-0` and has no spacer.

- [ ] **Step 3: Write minimal implementation**

Render a hidden desktop spacer with `sidebarWidthClass(collapsed)` before the desktop `<aside>`, and change that `<aside>` to fixed positioning while preserving `h-screen`, collapse/expand behavior and mobile drawer behavior.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm.cmd --prefix web test -- --run web/tests/sidebar.test.ts`

Expected: PASS.

### Task 2: Faturas com ordenação horizontal clara

**Files:**
- Modify: `web/components/faturas/CardPicker.tsx`
- Modify: `web/tests/invoices.test.ts`

- [ ] **Step 1: Write the failing test**

Update `web/tests/invoices.test.ts` so `CardPicker` order mode expects horizontal controls: `Mover Cartao A para a direita`, `Mover Cartao B para a esquerda`, and a visible short hint `Use as setas para reposicionar os cartões`.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm.cmd --prefix web test -- --run web/tests/invoices.test.ts`

Expected: FAIL because the current labels say cima/baixo and there is no order hint.

- [ ] **Step 3: Write minimal implementation**

Use `ArrowLeft`/`ArrowRight` for horizontal card order, adjust aria labels/titles, and add one compact hint inside order mode.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm.cmd --prefix web test -- --run web/tests/invoices.test.ts`

Expected: PASS.

### Task 3: Classe manual de ativo Pluggy sobrevive ao sync

**Files:**
- Modify: `tests/test_portfolio_api.py`
- Modify: `tests/test_pluggy_investments.py`
- Modify: `src/web/repositories/portfolio_repo.py`

- [ ] **Step 1: Write the failing tests**

Add one pytest asserting that a Pluggy asset patched from auto class to a different class keeps the patched `asset_class` after `upsert_pluggy_asset` refreshes price/quantity. Add one sync-level test covering the same behavior through `sync_pluggy_investments`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_portfolio_api.py::test_manual_asset_class_override_survives_pluggy_sync tests/test_pluggy_investments.py::test_sync_preserves_manual_asset_class_override -q`

Expected: FAIL because `upsert_pluggy_asset` currently rewrites `asset_class` from Pluggy classification on every sync.

- [ ] **Step 3: Write minimal implementation**

When `update_asset` changes `asset_class` for a Pluggy asset, mark it as manually adjusted. When `upsert_pluggy_asset` updates an existing manually adjusted row, preserve the current `asset_class` while still refreshing Pluggy market fields.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_portfolio_api.py::test_manual_asset_class_override_survives_pluggy_sync tests/test_pluggy_investments.py::test_sync_preserves_manual_asset_class_override -q`

Expected: PASS.

### Final Verification

- [ ] Run backend tests: `.venv\Scripts\python.exe -m pytest -q`
- [ ] Run frontend tests: `npm.cmd --prefix web test -- --run`
- [ ] Run lint: `npm.cmd --prefix web run lint`
- [ ] Run typecheck: `npm.cmd --prefix web run typecheck`
- [ ] Commit, push branch, deploy with `scripts/vps_deploy.sh`, and smoke-test the deployed app.
