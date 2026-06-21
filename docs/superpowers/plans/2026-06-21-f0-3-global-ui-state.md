# F0.3 Global UI State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate global period selection, privacy masking, and light/dark theme controls across the new `web/` app.

**Architecture:** Keep UI state in focused client providers under `web/providers/`, with pure period math in `web/lib/period.ts` and small hooks in `web/hooks/`. The existing F0.2 shell is reused by replacing inert Header/Sidebar buttons with functional controls.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5.9, TanStack Query, next-themes, Tailwind CSS, Vitest.

---

## Files

- Create `web/lib/period.ts` and `web/tests/period.test.ts`.
- Create `web/providers/PrivacyProvider.tsx` and `web/providers/PeriodProvider.tsx`.
- Create `web/hooks/useFinancialMonthStartDay.ts`, `web/hooks/useThemeToggle.ts`, and `web/hooks/useMoneyFormatter.ts`.
- Create `web/components/ui/MonthYearPicker.tsx` and `web/components/layout/SidebarFooter.tsx`.
- Modify `web/providers/Providers.tsx`, `web/app/layout.tsx`, `web/app/globals.css`, `web/components/layout/Header.tsx`, `web/components/layout/Sidebar.tsx`, `web/components/ui/MoneyText.tsx`, `web/package.json`, and `web/package-lock.json`.

## Task 1: Period Math

- [ ] **Step 1: Write failing period tests**

Add tests for `currentReferenceMonth`, `monthRange`, `shiftMonth`, `yearOf`, and `monthOf` using the F0.1 edge table.

Run: `cd web && npm test -- --run web/tests/period.test.ts`
Expected: fail because `@/lib/period` does not exist.

- [ ] **Step 2: Implement `web/lib/period.ts`**

Implement the backend-compatible 1-28 start-day clamp, month shifting, month label helpers, and civil date range derivation.

Run: `cd web && npm test -- --run web/tests/period.test.ts`
Expected: pass.

## Task 2: Providers And Hooks

- [ ] **Step 1: Install theme dependency**

Run: `cd web && npm install next-themes`
Expected: lockfile updated.

- [ ] **Step 2: Add focused providers/hooks**

Implement privacy localStorage state, financial start-day query fallback, period URL/localStorage synchronization, theme toggle wrapper, and money formatter.

- [ ] **Step 3: Wire provider tree**

Update `Providers.tsx` to mount `ThemeProvider`, `QueryClientProvider`, `PrivacyProvider`, and `PeriodProvider` with a Suspense boundary for search params.

Run: `cd web && npm run typecheck`
Expected: pass.

## Task 3: Functional Controls

- [ ] **Step 1: Implement MonthYearPicker**

Replace the inert header month button with a popover that selects months, supports year navigation, and applies/clears custom ranges.

- [ ] **Step 2: Connect privacy and theme controls**

Update Header eye button, Sidebar footer, and MoneyText to use global state.

Run: `cd web && npm run lint && npm run build`
Expected: pass.

## Task 4: Verification And Deploy

- [ ] **Step 1: Run frontend checks**

Run: `cd web && npm test -- --run && npm run typecheck && npm run lint && npm run build`
Expected: all pass.

- [ ] **Step 2: Run backend checks**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: backend suite passes.

- [ ] **Step 3: Commit, push, CI, VPS**

Commit as `feat: add F0.3 global UI state`, push `main`, wait for CI, then deploy the backend container on the VPS as before.
