# F3.5 Data Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve production data readability by fixing generic bank/card names and surfacing transaction categories that still need manual translation.

**Architecture:** Keep the changes at the existing API boundaries: enrich `/api/accounts` display fields inside `accounts_repo`, and enrich `/api/maintenance` with a read-only `category_audit`. The frontend only consumes the new audit data and keeps the editable de/para flow already delivered in F3.4.

**Tech Stack:** FastAPI, SQLite repository helpers, Next.js App Router, TypeScript, Vitest, pytest.

---

### Task 1: Account Display Fallbacks

**Files:**
- Modify: `src/web/repositories/accounts_repo.py`
- Test: `tests/test_accounts_api.py`

- [x] **Step 1: Write the failing test**

Add a test that seeds a Pluggy item with:

```python
Account(
    id="pluggy:inter-bank",
    source="pluggy",
    institution="077/0001/31238064-0",
    name="Conta Corrente",
    type="BANK",
    metadata={"itemId": "item-inter", "bankData": {"transferNumber": "077/0001/31238064-0"}},
)
Account(
    id="pluggy:inter-card",
    source="pluggy",
    institution="DAVI OLIVEIRA NETO",
    name="DAVI OLIVEIRA NETO",
    type="CREDIT",
    metadata={"itemId": "item-inter", "number": "1122", "creditData": {"brand": "MASTERCARD"}},
)
```

Assert that `accounts_repo.list_accounts_overview(..., month="2026-06")` returns:

```python
overview["banks"][0]["name"] == "Banco Inter - Conta Corrente"
overview["cards"][0]["name"] == "Banco Inter Mastercard final 1122"
```

- [x] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_accounts_api.py::test_accounts_overview_uses_bank_code_and_card_fallback_names -q`

Expected: FAIL because the bank still returns `Conta Corrente` and the card still returns the person name.

- [x] **Step 3: Implement fallbacks**

In `accounts_repo`, add:

- bank code map for common Brazilian institutions already observed in production;
- generic account name detection;
- person-name detection for card names;
- compact card level detection such as `gold`, `black`, `platinum`;
- per-item bank name lookup so card display can reuse the sibling bank institution.

Use these helpers only for display fields; do not mutate stored account data.

- [x] **Step 4: Run GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_accounts_api.py -q
```

Expected: PASS.

### Task 2: Maintenance Category Audit

**Files:**
- Modify: `src/web/app.py`
- Modify: `web/lib/types.ts`
- Modify: `web/lib/maintenance.ts`
- Modify: `web/app/(app)/manutencao/page.tsx`
- Test: `tests/test_web_app.py`
- Test: `web/tests/maintenance.test.ts`

- [x] **Step 1: Write failing backend test**

Seed transactions with categories `Groceries` and `Pet Shops`; mock `mnt.load_overrides()` to translate only `groceries`. Assert `/api/maintenance` returns:

```python
"category_audit": {
    "total_categories": 2,
    "translated": 1,
    "missing": [{"category": "Pet Shops", "tx_count": 1, "total_abs": 35.0}],
}
```

- [x] **Step 2: Run backend RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_maintenance_endpoint_reports_missing_category_translations -q`

Expected: FAIL because `category_audit` is missing.

- [x] **Step 3: Write failing frontend helper test**

Extend `web/tests/maintenance.test.ts` with `missingCategoryTranslations(data)` and assert it maps audit rows to renderable rows sorted as returned by the API.

- [x] **Step 4: Run frontend RED**

Run: `npm test -- --run tests/maintenance.test.ts`

Expected: FAIL because the helper/type is missing.

- [x] **Step 5: Implement audit**

Add a small helper near `/api/maintenance` that queries distinct non-empty `transactions.category`, compares lowercased keys with `overrides.categorias_pt`, and returns `total_categories`, `translated`, and top missing rows.

- [x] **Step 6: Render audit**

Show a `SectionCard` below the category preview titled `Categorias sem tradução`, with category, transaction count, and absolute movement total. Empty state: `Todas as categorias vistas já têm tradução.`

- [x] **Step 7: Run GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_maintenance_endpoint_reports_missing_category_translations tests/test_web_app.py::test_maintenance_endpoint_returns_profile_and_overrides -q
npm test -- --run tests/maintenance.test.ts
```

Expected: PASS.

### Task 3: Verification and Delivery

- [x] **Step 1: Local checks**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_accounts_api.py tests/test_web_app.py -q
npm test -- --run
npm run lint
npm run typecheck
npm run build
```

- [x] **Step 2: Browser smoke**

Open `/contas` and `/manutencao` locally. Verify account/card labels are readable and the maintenance page shows missing category translations without layout overlap.

- [ ] **Step 3: Commit, push, CI, deploy**

Commit as `feat: improve data quality maintenance`, push `main`, wait for CI success, deploy with `scripts/vps_deploy.sh`, and smoke `/api/accounts`, `/api/maintenance`, `/contas`, `/manutencao`.
