# F2.2 Transacoes Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core Transacoes experience: queryable transaction list API, partial transaction edits, manual creation/deletion/bulk updates, and a functional Next.js `/transacoes` page.

**Architecture:** Keep SQL in `src/web/repositories/transactions_repo.py`; keep FastAPI validation/routing in `src/web/routers/transactions.py`; keep the Next page as a composition of small hooks and local UI helpers. This first slice intentionally excludes advanced multipart import and duplicate modal polish if they threaten quality; the API/page foundation should be stable for the next cascade.

**Tech Stack:** Python 3.12, FastAPI, SQLite, pytest, Next.js App Router, TypeScript, TanStack Query, Tailwind, Vitest.

---

## File Structure

- Modify `src/web/repositories/transactions_repo.py`: repository list/update/create/delete/bulk functions, serialization, summary helpers.
- Modify `src/web/routers/transactions.py`: `GET /api/transactions`, unified `PATCH`, manual `POST`, `DELETE`, and `PATCH /api/transactions/bulk`.
- Modify `src/storage/migrations.py`: add idempotent filter indexes for `transactions.tag_id` and `transactions.bucket_id`.
- Create `tests/test_transactions_repo.py`: repository behavior tests.
- Create `tests/test_transactions_api.py`: HTTP contract tests.
- Modify `web/lib/types.ts`: transaction and transaction page types.
- Create `web/lib/transactions.ts`: query serialization/helpers for transaction filters.
- Create `web/hooks/useTransactions.ts`: list query hook.
- Create `web/hooks/useTransactionMutations.ts`: update/create/delete/bulk hooks.
- Modify `web/app/(app)/transacoes/page.tsx`: replace placeholder with the first functional transaction page.
- Create `web/tests/transactions.test.ts`: query serialization helper tests.

---

### Task 1: Backend Repository List And Summary

**Files:**
- Create: `tests/test_transactions_repo.py`
- Modify: `src/web/repositories/transactions_repo.py`
- Modify: `src/storage/migrations.py`

- [ ] **Step 1: Write failing repository tests**

Create tests for these behaviors:

```python
def test_list_transactions_filters_month_range_q_type_amount_hidden_and_account(tmp_db):
    # Seed checking and credit accounts, transactions across months, hidden states,
    # income/expense signs, and descriptions. Assert filters compose and page.total
    # remains the total filtered count.
    ...

def test_list_transactions_filters_bucket_and_tag_with_none(tmp_db):
    # Seed a bucket and a tag. Assert [id, None] matches rows with that id or NULL.
    ...

def test_list_transactions_summary_ignores_hidden_and_uses_sign_helpers(tmp_db):
    # Checking income counts as income, checking debit counts as expense,
    # credit positive purchase counts as expense, transfer category is visible
    # but excluded from summary, hidden rows are excluded from summary.
    ...
```

- [ ] **Step 2: Run repository tests to verify RED**

Run:

```bash
pytest tests/test_transactions_repo.py -q
```

Expected: fail because `list_transactions` does not exist yet.

- [ ] **Step 3: Implement repository functions**

Add these public functions/signatures:

```python
def list_transactions(db: Database, *, month=None, date_from=None, date_to=None, q=None,
                      type=None, amount_min=None, amount_max=None, account_id=None,
                      bucket_ids=None, tag_ids=None, hidden="exclude", page=1,
                      page_size=25) -> dict[str, Any]:
    ...

def update_transaction(db: Database, transaction_id: str, *, bucket_id=_UNSET,
                       tag_id=_UNSET, hidden=_UNSET, note=_UNSET,
                       reference_month=_UNSET) -> dict[str, Any]:
    ...
```

Use bound parameters, `LEFT JOIN`s to accounts/buckets/tags, `spending_value` and `income_value` for summary and displayed sign, and clamp `page_size` to `1..100`.

- [ ] **Step 4: Add migration indexes**

Append an idempotent migration:

```python
def m0011_tx_filter_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_tag_id ON transactions(tag_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_bucket_id ON transactions(bucket_id)")
```

- [ ] **Step 5: Verify GREEN**

Run:

```bash
pytest tests/test_transactions_repo.py -q
```

Expected: all repository tests pass.

---

### Task 2: Backend API Mutations

**Files:**
- Create: `tests/test_transactions_api.py`
- Modify: `src/web/routers/transactions.py`
- Modify: `src/web/repositories/transactions_repo.py`

- [ ] **Step 1: Write failing API tests**

Create HTTP tests for:

```python
def test_get_transactions_shape_and_bad_params(client, tmp_db): ...
def test_patch_transaction_accepts_all_partial_fields(client, tmp_db): ...
def test_patch_transaction_validates_empty_body_fk_and_reference_month(client, tmp_db): ...
def test_create_manual_transaction_uses_type_sign_and_reference_month(client, tmp_db): ...
def test_create_duplicate_returns_existing_without_second_insert(client, tmp_db): ...
def test_delete_transaction_and_bulk_patch(client, tmp_db): ...
```

- [ ] **Step 2: Run API tests to verify RED**

Run:

```bash
pytest tests/test_transactions_api.py -q
```

Expected: failures for missing routes/fields.

- [ ] **Step 3: Implement routes and repository mutation helpers**

Keep existing `PATCH {bucket_id}` and `PATCH {tag_id}` compatibility. Add Pydantic validation for month/date formats, `min <= max`, hidden tri-state, bucket/tag token parsing, and empty body rejection.

Implement:

```python
@router.get("/transactions")
def get_transactions(...): ...

@router.post("/transactions")
def create_transaction(...): ...

@router.delete("/transactions/{transaction_id}")
def delete_transaction(...): ...

@router.patch("/transactions/bulk")
def bulk_update(...): ...
```

- [ ] **Step 4: Verify API GREEN and regressions**

Run:

```bash
pytest tests/test_transactions_repo.py tests/test_transactions_api.py tests/test_web_buckets.py tests/test_web_tags.py -q
```

Expected: all pass.

---

### Task 3: Frontend Types, Hooks, And Query Helpers

**Files:**
- Modify: `web/lib/types.ts`
- Create: `web/lib/transactions.ts`
- Create: `web/hooks/useTransactions.ts`
- Create: `web/hooks/useTransactionMutations.ts`
- Create: `web/tests/transactions.test.ts`

- [ ] **Step 1: Write failing helper tests**

```ts
it("serializes transaction filters without empty values", () => {
  expect(transactionQuery({
    month: "2026-06",
    q: " ifood ",
    hidden: "exclude",
    bucketIds: [1, null],
    page: 2,
    pageSize: 10,
  })).toEqual({
    month: "2026-06",
    q: "ifood",
    hidden: "exclude",
    bucket_ids: "1,none",
    page: 2,
    page_size: 10,
  });
});
```

- [ ] **Step 2: Run Vitest RED**

Run:

```bash
cd web && npm test -- transactions.test.ts --run
```

Expected: fail because helper does not exist.

- [ ] **Step 3: Implement helper, types, hooks**

Add `Transaction`, `TransactionSummary`, `TransactionPage`, `TransactionFilters`, `transactionQuery`, `useTransactions`, `useUpdateTransaction`, `useCreateTransaction`, `useDeleteTransaction`, and `useBulkUpdateTransactions`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cd web && npm test -- transactions.test.ts --run
```

Expected: pass.

---

### Task 4: Frontend Page

**Files:**
- Modify: `web/app/(app)/transacoes/page.tsx`

- [ ] **Step 1: Replace placeholder with page shell**

Implement a client page with:
- header actions for refresh/new transaction,
- search input,
- type and hidden filters,
- summary cards for Entradas/Saidas/Saldo,
- `DataTable` with description/date/account/value/reference month/Meta/Tag/Ocultar/Note,
- pagination controls.

- [ ] **Step 2: Wire inline mutations**

Use `BucketSelect` + `useSetBucket`, `TagSelect` + `useSetTag`/`useCreateTag`, and unified `PATCH` for hidden/note/reference_month. Invalidate `["transactions"]` on success.

- [ ] **Step 3: Wire manual create/delete**

Use a compact modal/form or inline panel to create a manual transaction and per-row delete action with confirm.

- [ ] **Step 4: Verify frontend**

Run:

```bash
cd web && npm run typecheck && npm run lint && npm run build
```

Expected: all pass.

---

### Task 5: Final Verification And Deploy

**Files:**
- No planned source edits unless verification finds a bug.

- [ ] **Step 1: Run full backend tests**

```bash
pytest -q
```

- [ ] **Step 2: Run full frontend tests/checks**

```bash
cd web && npm test -- --run && npm run typecheck && npm run lint && npm run build
```

- [ ] **Step 3: Commit, push main, wait CI, deploy VPS**

```bash
git status --short
git add ...
git commit -m "feat: add F2.2 transactions core"
git push origin main
```

Then wait for GitHub Actions, run `minha-vps` deploy from `/opt/projetos/financas-agent`, and smoke `/api/health` plus `/api/transactions`.

