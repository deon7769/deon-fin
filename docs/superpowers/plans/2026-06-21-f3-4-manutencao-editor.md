# F3.4 Manutenção Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe editing and saving to the Next.js Manutenção screen, matching the useful legacy editor behavior.

**Architecture:** Keep `/api/maintenance` as the persistence contract and add frontend-only transformation helpers for editable rows. The page remains a client component using React Query for load/save, preserving unknown `family_profile` fields while editing the known sections.

**Tech Stack:** FastAPI existing endpoint, Next.js App Router, React Query, TypeScript, Vitest, Tailwind.

---

## Files

- Modify: `web/lib/types.ts` to complete maintenance property/cost types.
- Modify: `web/lib/maintenance.ts` with editor row helpers and payload builder.
- Modify: `web/tests/maintenance.test.ts` with TDD tests for edit transforms.
- Modify: `web/hooks/useMaintenance.ts` with `useSaveMaintenance`.
- Create: `web/components/manutencao/EditableMaintenanceTable.tsx`.
- Modify: `web/app/(app)/manutencao/page.tsx` to add edit/reload/save workflow.
- Modify: `README.md`, `docs/specs/README.md`, `docs/arquitetura-review-2026-06-21.md` after delivery.

## Task 1: Editor Helper TDD

- [ ] **Step 1: Add failing tests**

Extend `web/tests/maintenance.test.ts` with tests for:

- `maintenanceToEditorState` converts `categorias_pt` into `{ en, pt }[]`.
- `maintenanceToEditorState` flattens `imoveis[].custos` into editable cost columns.
- `buildMaintenanceSavePayload(original, editor)` lowercases/trims category keys.
- `buildMaintenanceSavePayload` preserves unknown profile fields while replacing edited known sections.
- `buildMaintenanceSavePayload` nests edited property costs back under `custos`.

Run: `npm test -- --run tests/maintenance.test.ts`

Expected: FAIL because editor helpers are missing.

- [ ] **Step 2: Implement helpers**

Add typed editor rows in `web/lib/maintenance.ts`:

- `MaintenanceEditorState`
- `maintenanceToEditorState(data)`
- `buildMaintenanceSavePayload(original, editor)`
- `emptyMaintenanceRow(kind)`
- `hasMeaningfulRow(row)`

Use simple object/array transforms only; do not mutate the original response.

- [ ] **Step 3: Run GREEN**

Run: `npm test -- --run tests/maintenance.test.ts`

Expected: PASS.

## Task 2: Save Hook

- [ ] **Step 1: Add mutation**

Extend `web/hooks/useMaintenance.ts`:

- `useSaveMaintenance()` calls `api.post<{ saved: boolean }>("/maintenance", payload)`.
- On success, invalidate `["maintenance"]`.

- [ ] **Step 2: Typecheck target**

Run: `npm run typecheck`

Expected: PASS after the page uses the hook.

## Task 3: Editable Tables

- [ ] **Step 1: Create generic editable table**

Create `web/components/manutencao/EditableMaintenanceTable.tsx`:

- Receives columns `{ key, label, type, options? }[]`.
- Renders text/number/select inputs.
- Supports add row and remove row.
- Emits full row arrays via `onChange`.
- Keeps stable button sizes and table layout.

- [ ] **Step 2: Use accessible labels**

Inputs must have `aria-label` including section label and column label so browser smoke can target them.

## Task 4: Page Integration

- [ ] **Step 1: Add editor state**

In `web/app/(app)/manutencao/page.tsx`:

- Convert loaded data with `maintenanceToEditorState`.
- Render current health/summary blocks as they are.
- Add an "Editar dados" section with eight editable tables:
  receitas, caixa, provisoes, metas, wishlist, imoveis, categorias, recorrencias.
- Add buttons: `Salvar tudo` and `Recarregar`.
- Show success/error status.

- [ ] **Step 2: Save**

On save:

- Build payload using `buildMaintenanceSavePayload`.
- POST with `useSaveMaintenance`.
- Update local editor state from returned cached/refetched data.
- Do not save if no original data exists.

## Task 5: Verification and Delivery

- [ ] **Step 1: Local checks**

Run:

```powershell
npm test -- --run tests/maintenance.test.ts
npm test -- --run
npm run lint
npm run typecheck
npm run build
.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_maintenance_endpoint_returns_profile_and_overrides -q
```

- [ ] **Step 2: Browser smoke**

Open `/manutencao`, verify:

- edit section renders;
- category rows are editable;
- reload button resets from API;
- save button posts without full-page reload;
- no absolute API URL is present.

- [ ] **Step 3: Full deploy flow**

After full local verification, commit, push, wait for CI success, deploy to VPS, and smoke `/manutencao`, `/api/maintenance`, `/legacy`.
