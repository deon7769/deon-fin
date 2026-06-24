# Operational QA Classification Income Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for the implementation batches. Use `superpowers:test-driven-development` before writing production code. Use `superpowers:verification-before-completion` before claiming each batch is complete.

**Goal:** Stabilize the known post-QA areas without chasing new reports prematurely: maintenance/classification usability, real income/transfer sign rules, invoice/card polish, and low-risk storage hardening.

**Architecture:** Keep the current FastAPI + repository + Next.js surface. Add behavior behind existing routers/components when possible, avoid route breaks, and keep learned/manual classification overrides durable after sync.

**Tech Stack:** Python/FastAPI/SQLite, pytest; Next.js/React/TypeScript, Vitest/Testing Library; VPS deploy through the existing deploy script after implementation batches pass locally.

---

## Current Baseline

- Local, VPS, and GitHub were aligned before this sprint on commit `94a3cbd`.
- The transaction filter drawer was already refactored to use controlled multiselect controls and mutually exclusive period modes.
- `docs/specs/F4-STATUS-aderencia.md` marks F4 follow-ups as complete/verify, so the next work should not restart F4 broadly.
- `docs/specs/F5-hardening-consolidacao.md` still maps technical hardening, starting with SQLite WAL/busy timeout and backup of WAL/SHM files.
- `docs/STATUS.md` and `README.md` still map open work in maintenance/classification, income/transfers, invoices, savings goals, investments, and technical consolidation.

## Execution Model

Run this in two phases.

### Phase 1: Explorer Agents, Read-Only

These agents may run in parallel. They must not edit files.

- **Explorer A - Maintenance/classification production audit**
  - Inspect real VPS data through the current app/database.
  - Capture counts and examples for categories without translation, categories without tag/meta mapping, manual overrides, audit propagation rows, and "similar affected" behavior.
  - Produce findings for the worker agent, preferably in `docs/qa/2026-06-24-classification-production-audit.md`.

- **Explorer B - Income/transfer cases**
  - Inspect existing tests and implementation for `income_value`, `spending_value`, refund/estorno/cashback, PIX, dividends/proventos, and own-account transfers.
  - Capture the current expected behavior from code before proposing any new rule.
  - Produce a concrete decision matrix with real examples where available.

- **Explorer C - F5.1 storage/deploy hardening**
  - Inspect the current `Database` implementation, connection lifecycle, write patterns, and `scripts/vps_deploy.sh` backup behavior.
  - Confirm the smallest file set needed for WAL/busy_timeout/concurrent-write protection.

### Phase 2: Worker Agents, TDD First

After the explorer notes are available, run independent workers in parallel only where write sets do not overlap.

- **Worker A - Maintenance/classification UX and suggestions**
  - Owns maintenance/classification API and UI files only.
  - Must not touch financial sign calculation helpers.

- **Worker B - Income/transfer sign matrix**
  - Owns financial classification/sign helpers and associated API tests.
  - Must not touch maintenance UI.

- **Worker C - F5.1 storage hardening**
  - Owns storage/deploy hardening.
  - Must not touch business classification files.

- **Worker D - Invoices polish**
  - Run after Worker A or in parallel only if it does not need shared category/tag UI components.
  - Owns invoice/card UI/API only.

## Batch 1 Scope

Start with the known, high-confidence items:

1. Maintenance/classification production audit and UX fixes.
2. Income/transfer sign matrix for known problem families.
3. SQLite WAL/busy_timeout and WAL/SHM backup.

Hold these for Batch 2 unless the audit shows they are blocking Batch 1:

1. Invoice card ordering persistence and inline Meta/Tag editing.
2. Savings goals candidate preview and withdrawal direction.
3. Investments Pluggy/BTG real JSON reconciliation, proventos, and movements.
4. Separate dashboards for grouped maintenance/merchant views.

## Task 1: Maintenance Classification Production Audit

**Purpose:** Verify the real state before changing behavior, because the user is testing production-like data and some docs may be stale.

**Files to read only:**

- `src/web/routers/maintenance.py`
- `src/web/repositories/transactions_repo.py`
- `src/web/repositories/classification_audit_repo.py`
- `src/agent/maintenance.py`
- `web/app/(app)/manutencao/page.tsx`
- `web/components/manutencao/*`
- `web/lib/maintenance.ts`
- `web/hooks/useMaintenance.ts`
- VPS database or API responses currently used by the deployed app.

**Audit checks:**

- Count raw Pluggy categories without Portuguese translation.
- Count raw categories without resolved Meta.
- Count raw categories without resolved Tag.
- Count transactions where manual edits exist and later sync should not overwrite them.
- Capture examples where applying Meta/Tag to one row should affect similar rows but the UI does not make that clear.
- Capture top merchants that are still noisy due to transaction description grouping rather than merchant normalization.

**Output:**

- Create `docs/qa/2026-06-24-classification-production-audit.md`.
- Include only observed counts, example IDs/descriptions, current endpoint/component responsible, and recommended worker task.
- Do not write application code in this task.

## Task 2: Maintenance Suggestions And Propagation Feedback

**Purpose:** Make maintenance fit the current UI and help the user complete missing classifications without treating legacy fields as pasted text.

**Expected behavior:**

- Maintenance should show structured suggestion rows for missing translation, suggested Tag, and suggested Meta.
- Applying a manual category/tag/meta edit must not be lost after sync.
- When an edit is propagated to similar transactions, the UI must show affected counts and refresh the list without a full page reload.
- Suggestions should use Portuguese display names where available and avoid showing raw Pluggy English literals as primary labels.

**Primary files:**

- `src/web/routers/maintenance.py`
- `src/web/repositories/transactions_repo.py`
- `src/web/repositories/classification_audit_repo.py`
- `src/agent/maintenance.py`
- `web/app/(app)/manutencao/page.tsx`
- `web/components/manutencao/*`
- `web/hooks/useMaintenance.ts`
- `web/lib/maintenance.ts`

**Tests first:**

Add or extend backend tests before implementation:

```python
def test_maintenance_suggestions_group_missing_translation_tag_and_bucket(client, sample_db):
    seed_transaction(sample_db, category="Digital services", description="OPENAI CHATGPT SUBSCR")

    response = client.get("/api/maintenance/classification-suggestions")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["raw_category"] == "Digital services"
    assert item["transaction_count"] == 1
    assert item["suggested_translation"]
    assert "suggested_tag" in item
    assert "suggested_bucket" in item
```

```python
def test_manual_classification_survives_resync(client, sample_db):
    transaction_id = seed_transaction(sample_db, category="Food", description="IFOOD")
    client.patch(f"/api/transactions/{transaction_id}/classification", json={"tag_id": "manual-food"})

    simulate_pluggy_resync(sample_db, transaction_id, category="Food")

    refreshed = client.get(f"/api/transactions/{transaction_id}").json()
    assert refreshed["tag_id"] == "manual-food"
    assert refreshed["classification_source"] == "manual"
```

```python
def test_apply_classification_returns_affected_count_and_ids(client, sample_db):
    ids = seed_similar_transactions(sample_db, description="UBER TRIP HELP")

    response = client.post("/api/maintenance/apply-classification", json={
        "transaction_id": ids[0],
        "tag_id": "transport-app",
        "apply_to_similar": True,
    })

    assert response.status_code == 200
    assert response.json()["affected_count"] == len(ids)
    assert set(response.json()["affected_transaction_ids"]) == set(ids)
```

Add or extend frontend tests before implementation:

```tsx
it("renders classification suggestions as structured fields", async () => {
  render(<MaintenancePage />)

  expect(await screen.findByText(/Sugestoes de classificacao/i)).toBeInTheDocument()
  expect(screen.getByRole("combobox", { name: /Meta/i })).toBeInTheDocument()
  expect(screen.getByRole("combobox", { name: /Tag/i })).toBeInTheDocument()
})
```

```tsx
it("shows affected count after applying a similar classification", async () => {
  render(<MaintenancePage />)

  await user.click(await screen.findByRole("button", { name: /Aplicar similares/i }))

  expect(await screen.findByText(/transacoes atualizadas/i)).toBeInTheDocument()
})
```

**Implementation notes:**

- Prefer adding a small repository method for suggestion aggregation instead of embedding query logic in the router.
- Keep legacy fields available for compatibility, but make the current UI consume structured fields.
- Use existing select/combobox components from the current UI; do not add raw comma-separated text inputs.
- Invalidate or refetch the affected maintenance query after mutation success.

## Task 3: Income And Transfer Decision Matrix

**Purpose:** Stop false income/expense totals for known families: own PIX, external PIX, Koopere, refunds/estornos, cashback, dividends/proventos, and investment movements.

**Primary files to inspect before editing:**

- `src/agent/context.py`
- `src/web/repositories/transactions_repo.py`
- `src/web/routers/transactions.py`
- `src/web/routers/dashboard.py`
- `tests/test_financial_signs.py`
- `tests/test_transactions_api.py`
- `tests/test_budget_api.py`
- `tests/test_painel.py`

**Decision matrix to encode:**

| Case | Expected income_value | Expected spending_value | Notes |
| --- | ---: | ---: | --- |
| Transfer between own accounts | 0 | 0 | Do not inflate income or expenses. |
| External PIX received | positive amount | 0 | Income only when source is external. |
| External PIX sent | 0 | positive amount | Expense only when destination is external. |
| Credit card refund/estorno | 0 or adjustment bucket | negative/offset expense | Must not become ordinary income. |
| Cashback | positive or adjustment bucket | 0 | Keep separate from salary/business income if model supports it. |
| Dividends/proventos | positive amount | 0 | Investment income, not transfer. |
| Investment application/rescue | 0 | 0 | Movement between cash/investment position, not income/expense. |
| Koopere and known financial intermediaries | classify by observed flow | classify by observed flow | Use real examples before hard-coding. |

**Tests first:**

```python
@pytest.mark.parametrize(
    "description,amount,transaction_type,expected_income,expected_spending",
    [
        ("PIX ENVIADO CONTA PROPRIA", -500, "TRANSFER", 0, 0),
        ("PIX RECEBIDO CLIENTE", 1200, "CREDIT", 1200, 0),
        ("PIX ENVIADO FORNECEDOR", -300, "DEBIT", 0, 300),
        ("ESTORNO COMPRA CARTAO", 80, "CREDIT", 0, -80),
        ("CASHBACK CARTAO", 12, "CREDIT", 12, 0),
        ("DIVIDENDOS AUVP11", 45, "CREDIT", 45, 0),
        ("APLICACAO INVESTIMENTO", -1000, "DEBIT", 0, 0),
    ],
)
def test_income_spending_matrix(description, amount, transaction_type, expected_income, expected_spending):
    values = compute_financial_values(description=description, amount=amount, transaction_type=transaction_type)

    assert values.income_value == expected_income
    assert values.spending_value == expected_spending
```

```python
def test_dashboard_and_transactions_use_same_financial_values(client, sample_db):
    seed_income_transfer_matrix(sample_db)

    dashboard = client.get("/api/dashboard").json()
    transactions = client.get("/api/transactions").json()

    assert dashboard["income_total"] == sum(row["income_value"] for row in transactions["items"])
    assert dashboard["expense_total"] == sum(row["spending_value"] for row in transactions["items"])
```

**Implementation notes:**

- Centralize the rule in one helper if the code currently calculates values in more than one place.
- Preserve existing manually classified transaction fields.
- Add real regression examples from Explorer B before finalizing hard-coded merchant or description rules.

## Task 4: F5.1 SQLite WAL, Busy Timeout, And Backup

**Purpose:** Reduce lock/retry risk before more parallel writes and ensure production backups include all SQLite sidecar state.

**Primary files:**

- `src/storage/db.py`
- `scripts/vps_deploy.sh`
- `tests/test_db_concurrency.py`
- Existing storage tests under `tests/`

**Tests first:**

```python
def test_database_enables_wal_and_busy_timeout(tmp_path):
    db_path = tmp_path / "app.db"
    db = Database(str(db_path))

    with db.connect() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]

    assert journal_mode.lower() == "wal"
    assert busy_timeout >= 5000
```

```python
def test_concurrent_writes_are_serialized(tmp_path):
    db = Database(str(tmp_path / "app.db"))
    create_small_write_table(db)

    run_parallel_writes(db, count=25)

    assert count_rows(db) == 25
```

```python
def test_vps_deploy_backup_includes_sqlite_sidecars():
    script = Path("scripts/vps_deploy.sh").read_text(encoding="utf-8")

    assert "-wal" in script
    assert "-shm" in script
```

**Implementation notes:**

- Set SQLite pragmas in the connection initialization path used by the app and tests.
- If the repository already has a write lock pattern, reuse it.
- Update backup logic so `.db`, `.db-wal`, and `.db-shm` are handled consistently.

## Task 5: Invoice/Card Polish

**Purpose:** Close known user-facing issues in invoice view without mixing it into Batch 1 unless capacity allows.

**Expected behavior:**

- User can reorder cards in invoice view and the order persists.
- Inline Meta/Tag editing works from invoice transaction rows when those fields are visible there.
- Category group labels use translations and Tag/Meta display names instead of raw integration literals.
- Closing/due dates prefer integration data when available, falling back to existing manual defaults.

**Primary files:**

- `src/web/routers/invoices.py`
- `src/web/repositories/invoices_repo.py`
- `web/app/(app)/cartoes/page.tsx`
- `web/components/faturas/*`
- `web/lib/invoices.ts`
- `web/tests/invoices*.test.tsx`
- `tests/test_invoices_api.py`

**Tests first:**

```tsx
it("persists card order after drag or move action", async () => {
  render(<InvoicesPage />)

  await moveCard("Nubank", "before", "BTG")
  await reloadInvoicesPage()

  expect(cardNames()).toEqual(["Nubank", "BTG"])
})
```

```python
def test_invoice_groups_use_translated_category_labels(client, sample_db):
    seed_invoice_transaction(sample_db, raw_category="Digital services", translated_category="Servicos digitais")

    response = client.get("/api/invoices/current")

    assert "Servicos digitais" in collect_group_names(response.json())
    assert "Digital services" not in collect_group_names(response.json())
```

## Task 6: Savings Goals Polish

**Purpose:** Keep this ready for the next pass after Batch 1, because it shares classification concepts but is not the first bottleneck.

**Expected behavior:**

- Candidate suggestions show why a transaction is linked to a goal.
- User previews affected transactions before saving links.
- Withdrawals/subtractions from a goal have an explicit direction model.
- Goal card navigation should show the active filter visibly on the transaction page.

**Primary files:**

- `src/web/routers/goals.py`
- `src/web/repositories/goals_repo.py`
- `web/app/(app)/metas/page.tsx`
- `web/app/(app)/transacoes/page.tsx`
- `web/components/metas/*`
- `web/components/transacoes/*`

## Task 7: Investments Pluggy/BTG Follow-Up

**Purpose:** Defer until the current UX/regression pass is stable, but keep the known modeling issue visible.

**Expected behavior:**

- `AUVP11` is handled as ETF, not FI.
- Manual asset edits persist after sync.
- Pluggy/BTG JSON fields are captured for proventos, movements, assets, and reconciled manual positions.
- Aporte confirmation updates position consistently.

**Primary files to inspect later:**

- `src/investments/*`
- `src/web/routers/investments.py`
- `src/web/repositories/investments_repo.py`
- `web/app/(app)/investimentos/page.tsx`
- Investment-related tests under `tests/` and `web/tests/`.

## Verification Gates

Each implementation batch must finish with:

```powershell
python -m pytest
npm --prefix web run lint
npm --prefix web run typecheck
npm --prefix web test -- --runInBand
```

Before deploy:

```powershell
git status --short
```

After deploy to VPS:

```bash
scripts/vps_deploy.sh
docker exec financas-agent curl -fsS http://127.0.0.1:8000/api/health
```

Then perform a browser smoke pass for:

- Transactions filter drawer.
- Maintenance classification/suggestions.
- Dashboard totals after income/transfer matrix changes.
- Invoice page if Task 5 is included.

## Recommended Immediate Dispatch

Start with these parallel prompts:

### Prompt For Explorer A

You are Explorer A for the Deon Fin operational QA sprint. Work read-only. Inspect the deployed/current data and code paths for maintenance/classification. Capture counts and examples for missing category translations, missing Tag/Meta mappings, manual overrides that must survive sync, similar-propagation audit rows, and noisy merchant/category groupings. Write findings to `docs/qa/2026-06-24-classification-production-audit.md`. Do not edit application code.

### Prompt For Explorer B

You are Explorer B for the Deon Fin operational QA sprint. Work read-only. Inspect current code/tests for `income_value` and `spending_value`, including own-account PIX, external PIX, Koopere, refunds/estornos, cashback, dividends/proventos, and investment application/rescue. Produce a concrete decision matrix with current behavior, desired behavior, affected helper/API files, and real examples where available. Do not edit application code.

### Prompt For Explorer C

You are Explorer C for the Deon Fin F5.1 hardening task. Work read-only. Inspect the SQLite connection setup, write patterns, concurrency tests, and `scripts/vps_deploy.sh` backup behavior. Confirm the smallest TDD implementation path for WAL, busy_timeout, serialized writes if needed, and backup of `.db-wal`/`.db-shm`. Do not edit application code.

After explorers complete, launch Worker A, Worker B, and Worker C with their respective task sections above. Worker D should wait unless Batch 1 completes quickly or invoice files are confirmed independent.

## Done Criteria

- Plan-backed tasks have failing tests before implementation.
- All changed behavior has passing backend/frontend tests.
- Manual overrides are preserved in classification and investments-related edits where touched.
- Existing transaction filters remain stable after classification/income changes.
- VPS deploy completes successfully.
- Local, VPS, and GitHub are aligned after the batch.
