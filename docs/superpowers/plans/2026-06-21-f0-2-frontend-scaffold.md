# F0.2 Frontend Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the initial Next.js app in `web/` with the dark shell, sidebar, typed UI primitives, API client, and placeholder routes required by F0.2.

**Architecture:** The new UI lives beside the existing FastAPI/Jinja app and does not alter `src/web/`. The Next App Router uses a shared `(app)` route group for the financial shell, typed components under `web/components`, and thin utilities under `web/lib`.

**Tech Stack:** Next.js 16, React 19, TypeScript 5.9, Tailwind CSS, TanStack Query, lucide-react, Recharts 3, Vitest for light utility/API-client tests.

---

## Files

- Create `web/package.json`, `web/package-lock.json`, `web/tsconfig.json`, `web/next.config.mjs`, `web/postcss.config.mjs`, `web/tailwind.config.ts`, `web/eslint.config.mjs`, `web/.gitignore`, `web/.env.example`, `web/README.md`.
- Create `web/app/globals.css`, `web/app/layout.tsx`, `web/app/not-found.tsx`, `web/app/(app)/layout.tsx`, and one placeholder `page.tsx` for each menu route.
- Create `web/providers/Providers.tsx`.
- Create `web/lib/cn.ts`, `web/lib/types.ts`, `web/lib/format.ts`, `web/lib/api.ts`.
- Create `web/components/layout/nav.ts`, `web/components/layout/Sidebar.tsx`, `web/components/layout/Header.tsx`.
- Create UI primitives in `web/components/ui/`: `Skeleton.tsx`, `SectionCard.tsx`, `EmptyState.tsx`, `MoneyText.tsx`, `KpiCard.tsx`, `Pill.tsx`, `ProgressBar.tsx`, `DataTable.tsx`, `BucketSelect.tsx`, `TagSelect.tsx`.
- Create tests `web/tests/format.test.ts` and `web/tests/api.test.ts`.

## Task 1: Bootstrap Project

- [ ] **Step 1: Create package/config files**

Create the Next/Tailwind/TypeScript config exactly in `web/`.

- [ ] **Step 2: Install dependencies**

Run: `cd web && npm install`
Expected: `package-lock.json` generated and no install errors.

- [ ] **Step 3: Verify baseline scripts exist**

Run: `cd web && npm run typecheck`
Expected: initially fails until source files exist, then passes after Task 2.

## Task 2: Test Utilities First

- [ ] **Step 1: Write failing tests**

Add `web/tests/format.test.ts` for BRL/date/percent/month formatting and `web/tests/api.test.ts` for API error envelope parsing.

- [ ] **Step 2: Run tests red**

Run: `cd web && npm test -- --run`
Expected: fail because `web/lib/format.ts` and `web/lib/api.ts` are not implemented.

- [ ] **Step 3: Implement libs**

Add `web/lib/format.ts`, `web/lib/api.ts`, `web/lib/types.ts`, `web/lib/cn.ts`.

- [ ] **Step 4: Run tests green**

Run: `cd web && npm test -- --run`
Expected: pass.

## Task 3: Providers And Shell

- [ ] **Step 1: Add providers and root layout**

Create `web/providers/Providers.tsx`, `web/app/layout.tsx`, and `web/app/globals.css`.

- [ ] **Step 2: Add navigation shell**

Create `web/components/layout/nav.ts`, `Sidebar.tsx`, `Header.tsx`, and `web/app/(app)/layout.tsx`.

- [ ] **Step 3: Verify typecheck**

Run: `cd web && npm run typecheck`
Expected: pass after components compile.

## Task 4: UI Primitives

- [ ] **Step 1: Add typed presentational primitives**

Create the UI components with stable props and no API calls.

- [ ] **Step 2: Verify typecheck**

Run: `cd web && npm run typecheck`
Expected: pass.

## Task 5: Placeholder Routes

- [ ] **Step 1: Add all menu routes**

Create placeholders for `/`, `/orcamento`, `/metas`, `/contas`, `/faturas`, `/transacoes`, `/tags`, `/perfil`, `/faq`.

- [ ] **Step 2: Build**

Run: `cd web && npm run build`
Expected: all routes compile.

## Task 6: Final Verification

- [ ] **Step 1: Run frontend checks**

Run: `cd web && npm test -- --run && npm run typecheck && npm run lint && npm run build`
Expected: all pass.

- [ ] **Step 2: Run backend regression**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: all existing backend tests still pass.

- [ ] **Step 3: Commit**

Run: `git add web docs/superpowers/plans/2026-06-21-f0-2-frontend-scaffold.md && git commit -m "feat: scaffold F0.2 frontend"`
