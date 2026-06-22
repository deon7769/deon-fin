# Assisted Tag Meta Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Tags the canonical subdivision under budget Metas while preserving raw Pluggy categories and manual user corrections.

**Architecture:** Add an additive migration for `tags.bucket_id`, `transactions.tag_source`, and `tag_rules`; extend the existing Tag and Transaction repositories instead of creating a parallel category service; add a conservative deterministic tag classifier that runs after sync and never overwrites manual tags. Update the Next UI only where the new foundation is directly usable: Tags page/modal and Transaction tag assignment.

**Tech Stack:** Python 3, SQLite migrations, FastAPI routers/repositories, pytest, Next.js/React/TypeScript, TanStack Query, Vitest, npm lint/build, VPS deploy through `scripts/vps_deploy.sh`.

---

## File Structure

- Modify `src/storage/migrations.py`: add migration `m0020_tag_bucket_source_rules`.
- Modify `src/web/repositories/tags_repo.py`: tag parent bucket metadata, validation, seed parent mapping, tag rules helpers.
- Modify `src/web/routers/tags.py`: accept `bucket_id` on create/patch.
- Modify `src/web/repositories/transactions_repo.py`: include `tag_source`, manual tag marking, set-tag propagation.
- Modify `src/web/routers/transactions.py`: add `POST /api/transactions/{id}/tag`.
- Create `src/agent/tags.py`: deterministic tag classifier and category/merchant map.
- Modify `src/web/app.py`: run tag classifier after sync pipelines.
- Modify `tests/test_migrations.py`: schema test.
- Modify `tests/test_tags.py`: parent bucket repository tests.
- Modify `tests/test_web_tags.py`: API tests for parent bucket validation.
- Modify `tests/test_transactions_repo.py`: manual source and similar propagation tests.
- Modify `tests/test_transactions_api.py` or `tests/test_web_tags.py`: tag endpoint tests.
- Create `tests/test_agent_tags.py`: classifier tests.
- Modify `web/lib/types.ts`: Tag parent bucket metadata and `Transaction.tag_source`.
- Modify `web/hooks/useTagMutations.ts`: include `bucket_id`.
- Modify `web/hooks/useSetTag.ts`: call the new tag endpoint with propagation support.
- Modify `web/components/tags/TagModal.tsx`: parent Meta selector.
- Modify `web/app/(app)/tags/page.tsx`: load buckets and show Meta column.
- Modify `web/components/ui/TagSelect.tsx`: optional apply-to-similar confirmation.
- Modify `web/app/(app)/transacoes/page.tsx`: use propagation and show tag source cue.
- Modify `web/tests/tags.test.ts` or add focused component/helper tests if the existing test harness supports the behavior.

---

### Task 1: Schema and Tag Parent Metadata

**Files:**
- Modify: `src/storage/migrations.py`
- Modify: `src/web/repositories/tags_repo.py`
- Modify: `src/web/routers/tags.py`
- Test: `tests/test_migrations.py`
- Test: `tests/test_tags.py`
- Test: `tests/test_web_tags.py`

- [ ] **Step 1: Write the failing migration test**

Add this behavior to `tests/test_migrations.py`:

```python
def test_tag_classification_schema_columns_and_rules(tmp_db):
    tag_cols = {row["name"] for row in tmp_db._conn.execute("PRAGMA table_info(tags)")}
    tx_cols = {row["name"] for row in tmp_db._conn.execute("PRAGMA table_info(transactions)")}
    rule_cols = {row["name"] for row in tmp_db._conn.execute("PRAGMA table_info(tag_rules)")}

    assert "bucket_id" in tag_cols
    assert "tag_source" in tx_cols
    assert {"id", "match_key", "tag_id", "created_at", "updated_at"}.issubset(rule_cols)
```

- [ ] **Step 2: Verify the schema test fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_migrations.py::test_tag_classification_schema_columns_and_rules -q
```

Expected: FAIL because `bucket_id`, `tag_source`, or `tag_rules` does not exist.

- [ ] **Step 3: Implement the minimal migration**

Add `m0020_tag_bucket_source_rules` with `_add_column(conn, "tags", "bucket_id", "INTEGER")`, `_add_column(conn, "transactions", "tag_source", "TEXT")`, `CREATE TABLE IF NOT EXISTS tag_rules (...)`, and append `(20, "tag_bucket_source_rules", m0020_tag_bucket_source_rules)` to `MIGRATIONS`.

- [ ] **Step 4: Verify the schema test passes**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_migrations.py::test_tag_classification_schema_columns_and_rules -q
```

Expected: PASS.

- [ ] **Step 5: Write failing repository/API tests for Tag parent bucket**

Add tests that create a Tag with `bucket_id`, update it to another valid bucket, clear it with `bucket_id=None`, and reject an invalid parent bucket through both repository and `/api/tags`.

- [ ] **Step 6: Verify the Tag parent tests fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_tags.py tests/test_web_tags.py -q
```

Expected: FAIL because `create_tag`, `update_tag`, and API bodies do not accept or return `bucket_id`.

- [ ] **Step 7: Implement Tag parent support**

Update `tags_repo` to join `budget_buckets`, return `bucket_id`, `bucket_key`, `bucket_name`, and `bucket_color`, validate bucket existence, and accept `bucket_id` in create/update. Update `TagCreateRequest` and `TagPatchRequest` in `tags.py` with optional `bucket_id`.

- [ ] **Step 8: Verify Tag parent tests pass**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_tags.py tests/test_web_tags.py -q
```

Expected: PASS.

---

### Task 2: Transaction Tag Source and Similar Propagation

**Files:**
- Modify: `src/web/repositories/transactions_repo.py`
- Modify: `src/web/routers/transactions.py`
- Test: `tests/test_transactions_repo.py`
- Test: `tests/test_transactions_api.py`

- [ ] **Step 1: Write failing tests for manual tag source**

Add tests proving `PATCH /api/transactions/{id}` and `transactions_repo.update_transaction(..., tag_id=...)` set `tag_source='manual'`, and clearing a tag also leaves `tag_source='manual'`.

- [ ] **Step 2: Verify manual tag source tests fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_transactions_repo.py::test_update_transaction_tag_marks_manual tests/test_transactions_api.py::test_patch_transaction_accepts_all_partial_fields -q
```

Expected: FAIL because `tag_source` is not selected, serialized, or written.

- [ ] **Step 3: Implement minimal manual source behavior**

Add `t.tag_source` to `SELECT_COLS`, serialize `tag_source`, set `tag_source='manual'` whenever `tag_id` is patched or created manually, and clear `tag_source` on tag deletion if the Tag row is deleted.

- [ ] **Step 4: Verify manual tag tests pass**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_transactions_repo.py tests/test_transactions_api.py tests/test_web_tags.py -q
```

Expected: PASS.

- [ ] **Step 5: Write failing propagation tests**

Add tests for `transactions_repo.set_tag(..., apply_to_similar=True)` and `POST /api/transactions/{id}/tag`, matching the existing bucket propagation behavior: same merchant/sign gets `tag_source='rule'`, different merchant is ignored, manual rows are not overwritten, and response includes `similar_ids`.

- [ ] **Step 6: Verify propagation tests fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_transactions_repo.py::test_set_tag_applies_to_similar_without_overwriting_manual tests/test_transactions_api.py::test_post_transaction_tag_propagates_to_similar -q
```

Expected: FAIL because `set_tag` has no `apply_to_similar` and there is no tag endpoint.

- [ ] **Step 7: Implement set_tag propagation**

Extend `set_tag(db, transaction_id, tag_id, apply_to_similar=False)` to reuse `match_key_for`, upsert/delete `tag_rules`, set target `tag_source='manual'`, update similar non-manual rows to `tag_source='rule'`, and return `match_key`, `rule_upserted`, `rule_deleted`, `similar_affected`, and `similar_ids`. Add `TransactionTagPost` and `POST /api/transactions/{id}/tag`.

- [ ] **Step 8: Verify propagation tests pass**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_transactions_repo.py tests/test_transactions_api.py tests/test_web_tags.py -q
```

Expected: PASS.

---

### Task 3: Automatic Tag Classifier and Sync Pipeline

**Files:**
- Create: `src/agent/tags.py`
- Modify: `src/web/app.py`
- Test: `tests/test_agent_tags.py`

- [ ] **Step 1: Write failing classifier tests**

Create `tests/test_agent_tags.py` with tests that prove `apply_tags_to_database(db)` applies `tag_rules` before heuristics, maps obvious category/merchant examples such as `Food Delivery` or `IFOOD` to a seeded Tag, skips `tag_source='manual'`, and leaves credit card payments untagged.

- [ ] **Step 2: Verify classifier tests fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_agent_tags.py -q
```

Expected: FAIL because `src.agent.tags` does not exist.

- [ ] **Step 3: Implement deterministic classifier**

Create `src/agent/tags.py` with `apply_tags_to_database(db)`, conservative category/merchant maps, seeded Tag lookup by normalized name, `tag_rules` lookup by `match_key_for`, and stats such as `by_rule`, `by_map`, `unmatched`, and `skipped_manual`.

- [ ] **Step 4: Verify classifier tests pass**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_agent_tags.py tests/test_tags.py tests/test_transactions_repo.py -q
```

Expected: PASS.

- [ ] **Step 5: Wire classifier into sync**

Import `apply_tags_to_database` in `src/web/app.py` and call it after `apply_buckets_to_database(db)` and before marking the Pluggy item synced in `_background_sync` and `_sync_all_items`.

- [ ] **Step 6: Verify backend integration**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_agent_tags.py tests/test_web_app.py -q
```

Expected: PASS.

---

### Task 4: Tags UI Parent Meta

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/hooks/useTagMutations.ts`
- Modify: `web/components/tags/TagModal.tsx`
- Modify: `web/app/(app)/tags/page.tsx`
- Test: `web/tests/tags.test.ts` or existing frontend test file if a component harness is present.

- [ ] **Step 1: Write failing frontend type/helper test**

Add a frontend test that uses a `Tag` with `bucket_id`, `bucket_name`, and `bucket_color`, and validates any helper added to display parent Meta fallback as `"Sem meta"`.

- [ ] **Step 2: Verify the frontend test fails**

Run:

```powershell
npm test -- --run web/tests/tags.test.ts
```

Expected: FAIL because the helper/type support is missing.

- [ ] **Step 3: Implement Tag parent UI data flow**

Extend `Tag` with `bucket_id`, `bucket_key`, `bucket_name`, and `bucket_color`. Extend `TagInput` with `bucket_id`. Load buckets in `TagsPage`, add a Meta column, and pass buckets into `TagModal`. Add a select in the modal with `"Sem meta"` plus the six buckets.

- [ ] **Step 4: Verify frontend Tag tests pass**

Run:

```powershell
npm test -- --run web/tests/tags.test.ts
```

Expected: PASS.

---

### Task 5: Transaction Tag Apply-to-Similar UI

**Files:**
- Modify: `web/hooks/useSetTag.ts`
- Modify: `web/components/ui/TagSelect.tsx`
- Modify: `web/app/(app)/transacoes/page.tsx`
- Modify: `web/lib/types.ts`
- Test: `web/tests/tags.test.ts` or new focused test if needed.

- [ ] **Step 1: Write failing frontend test for source labels or propagation payload**

Add a test for a small helper that maps `tag_source` values to user-facing labels: `manual -> Manual`, `rule -> Regra`, `auto -> Automatica`, and null -> empty string.

- [ ] **Step 2: Verify the frontend test fails**

Run:

```powershell
npm test -- --run web/tests/tags.test.ts
```

Expected: FAIL because the helper is not implemented.

- [ ] **Step 3: Implement propagation UI**

Update `useSetTag` to call `POST /transactions/{id}/tag` with `apply_to_similar`. Add optional `onChangeWithPropagation` to `TagSelect`, mirroring `BucketSelect`'s pending choice UI. Show a compact source cue under the selected Tag in `TransacoesPage`.

- [ ] **Step 4: Verify frontend tests pass**

Run:

```powershell
npm test -- --run web/tests/tags.test.ts
```

Expected: PASS.

---

### Task 6: Full Verification, Commit, VPS Deploy

**Files:**
- All changed files from Tasks 1-5.

- [ ] **Step 1: Run full backend tests**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run full frontend tests**

```powershell
npm test -- --run
```

Expected: all tests pass.

- [ ] **Step 3: Run lint and build**

```powershell
npm run lint
npm run build
```

Expected: both commands exit 0.

- [ ] **Step 4: Review diff**

```powershell
git diff --stat
git diff --check
git status --short
```

Expected: no whitespace errors; changed files are limited to this sprint.

- [ ] **Step 5: Commit implementation**

```powershell
git add src tests web docs/superpowers/plans/2026-06-22-assisted-tag-meta-classification.md
git commit -m "feat: add assisted tag classification"
```

Expected: one implementation commit after tests pass.

- [ ] **Step 6: Deploy on VPS**

Push or transfer the committed branch according to the current repo workflow, then on `minha-vps` in `/opt/projetos/financas-agent` run:

```bash
./scripts/vps_deploy.sh
```

Expected: backup created, host pytest passes, Docker build succeeds, Compose restarts, and `/api/health` smoke test returns OK.

---

## Self-Review

- The plan follows the approved spec and the attached user guidance: no dashboard redesign, no category replacement, and no LLM classifier.
- Each production behavior has a failing test before implementation.
- The migration number is `m0020` because the current latest migration is `m0019_system_total_settings`.
- `transactions.category` remains raw source data; the canonical classification layer is `transactions.tag_id` plus `transactions.bucket_id`.
- Manual preservation is covered in repository, API, classifier, and sync pipeline tests.
