# Maintenance Classification Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a maintenance health view for transaction classification coverage.

**Architecture:** Extend the existing `/api/maintenance` response with a read-only `classification_health` object, then render it in the current Next Manutencao page. Keep actions out of this slice; this sprint only exposes counts and review queues for "sem Tag" and "sem Meta".

**Tech Stack:** Python/FastAPI/SQLite backend, Vitest/React helper tests, Next.js UI components.

---

### Task 1: Backend Classification Health

**Files:**
- Modify: `src/web/app.py`
- Test: `tests/test_web_app.py`

- [ ] Write a failing test that seeds transactions with and without `tag_id`/`bucket_id` and asserts `/api/maintenance` returns `classification_health`.
- [ ] Implement `_classification_health(db, cat_map)` beside `_category_translation_audit`.
- [ ] Include `classification_health` in `get_maintenance`.
- [ ] Run `python -m pytest tests/test_web_app.py::test_maintenance_endpoint_reports_classification_health -q`.

### Task 2: Frontend Helpers And Types

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/maintenance.ts`
- Test: `web/tests/maintenance.test.ts`

- [ ] Add `MaintenanceClassificationHealth` and issue-row types.
- [ ] Add helper functions that convert API issue rows into renderable rows and compute coverage percentages.
- [ ] Run `npm test -- maintenance.test.ts --run`.

### Task 3: Manutencao UI Panel

**Files:**
- Create: `web/components/manutencao/ClassificationHealthPanel.tsx`
- Modify: `web/app/(app)/manutencao/page.tsx`

- [ ] Render compact coverage cards for Tag and Meta.
- [ ] Render two small tables for top "sem Tag" and "sem Meta" rows.
- [ ] Keep layout responsive and reuse `SectionCard`, `DataTable`, and `MoneyText`.
- [ ] Run `npm test`, `npm run build`, and backend tests before commit.

