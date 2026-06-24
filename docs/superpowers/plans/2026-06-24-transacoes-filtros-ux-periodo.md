# Transacoes Filtros UX Periodo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir os filtros avancados de Transacoes para usar controles da UI atual e tornar periodo e mes de referencia mutuamente exclusivos.

**Architecture:** O backend rejeita `month` junto de `from/to` para evitar intersecoes silenciosas. O frontend passa a representar periodo como modo unico (`month` ou `range`) e substitui listas nativas por um multiselect local com busca, chips e suporte a valores `none`.

**Tech Stack:** FastAPI/Pydantic/Pytest no backend, Next.js/React/Vitest no frontend.

---

### Task 1: Contrato de periodo e listas

**Files:**
- Modify: `tests/test_transactions_api.py`
- Modify: `src/web/routers/transactions.py`

- [ ] **Step 1: Write failing API tests**

Add tests proving `month` cannot coexist with `from/to`, partial ranges are invalid, `from > to` is invalid, and list filters still accept `none` values.

- [ ] **Step 2: Run the API tests and verify RED**

Run: `.venv/Scripts/python -m pytest tests/test_transactions_api.py -q`

Expected: new tests fail because the current backend accepts `month` with `from/to` and partial ranges.

- [ ] **Step 3: Implement minimal validation**

In `get_transactions`, parse dates first, reject mixed `month` and range, reject partial range, and reject `from > to`.

- [ ] **Step 4: Run the API tests and verify GREEN**

Run: `.venv/Scripts/python -m pytest tests/test_transactions_api.py -q`

Expected: tests pass.

### Task 2: Drawer state and multiselect UX

**Files:**
- Modify: `web/tests/transaction-advanced-filters.test.ts`
- Modify: `web/tests/transactions.test.ts`
- Modify: `web/lib/transactions.ts`
- Modify: `web/hooks/useTransactionFilters.ts`
- Modify: `web/components/transacoes/TransactionAdvancedFilters.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add tests proving the drawer no longer renders native `select multiple`, selected multi filters appear as chips, range mode exposes initial/final dates, and query serialization keeps range preferred over month.

- [ ] **Step 2: Run the frontend tests and verify RED**

Run: `npm --prefix web test -- transaction-advanced-filters.test.ts transactions.test.ts`

Expected: new tests fail because native multiselects still exist and range state is not represented.

- [ ] **Step 3: Implement minimal frontend changes**

Add a local reusable `FilterMultiSelect` inside `TransactionAdvancedFilters.tsx`, add `range` to `TransactionAdvancedFilterPatch`, replace native multiselects, and update `applyAdvancedFilters`.

- [ ] **Step 4: Run the frontend tests and verify GREEN**

Run: `npm --prefix web test -- transaction-advanced-filters.test.ts transactions.test.ts`

Expected: tests pass.

### Task 3: Verification and deploy

**Files:**
- Verify all touched frontend and backend behavior.

- [ ] **Step 1: Run focused local verification**

Run: `.venv/Scripts/python -m pytest tests/test_transactions_api.py tests/test_transactions_repo.py -q`
Run: `npm --prefix web test -- transaction-advanced-filters.test.ts transactions.test.ts`
Run: `npm --prefix web run typecheck`

- [ ] **Step 2: Review git diff**

Run: `git diff --check` and `git status --short`.

- [ ] **Step 3: Commit and deploy through VPS workflow**

After local verification, sync changes to the VPS checkout, run host tests there, run `scripts/vps_deploy.sh`, and smoke-test `/api/health`.
