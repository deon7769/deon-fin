# Responsive Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app shell responsive by adding a collapsible desktop sidebar, a mobile drawer, and route-level HEAD support for the exported Next frontend.

**Architecture:** Keep the navigation state inside `Sidebar`, with pure helper functions in `web/lib/sidebar.ts` for testable class/state decisions. Preserve the current FastAPI same-origin deployment while teaching the SPA fallback routes to accept both GET and HEAD. Stabilize Recharts containers with explicit minimum dimensions so responsive measurements never start at negative sizes.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS, Vitest, FastAPI, pytest.

---

### Task 1: Sidebar State Helpers

**Files:**
- Create: `web/lib/sidebar.ts`
- Test: `web/tests/sidebar.test.ts`

- [x] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import {
  SIDEBAR_STORAGE_KEY,
  initialSidebarCollapsed,
  sidebarLabelClass,
  sidebarWidthClass,
  toggleSidebarCollapsed,
} from "@/lib/sidebar";

describe("sidebar helpers", () => {
  it("uses a stable storage key for the collapsed state", () => {
    expect(SIDEBAR_STORAGE_KEY).toBe("deon-fin:sidebar-collapsed");
  });

  it("parses the persisted collapsed state conservatively", () => {
    expect(initialSidebarCollapsed(null)).toBe(false);
    expect(initialSidebarCollapsed("0")).toBe(false);
    expect(initialSidebarCollapsed("1")).toBe(true);
    expect(initialSidebarCollapsed("true")).toBe(true);
  });

  it("returns desktop width classes for expanded and collapsed states", () => {
    expect(sidebarWidthClass(false)).toContain("md:w-[240px]");
    expect(sidebarWidthClass(true)).toContain("md:w-16");
  });

  it("keeps collapsed labels available to screen readers", () => {
    expect(sidebarLabelClass(false)).toBe("");
    expect(sidebarLabelClass(true)).toContain("md:sr-only");
  });

  it("toggles the collapsed state", () => {
    expect(toggleSidebarCollapsed(false)).toBe(true);
    expect(toggleSidebarCollapsed(true)).toBe(false);
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- --run web/tests/sidebar.test.ts`

Expected: FAIL because `@/lib/sidebar` does not exist.

- [x] **Step 3: Write minimal implementation**

```ts
export const SIDEBAR_STORAGE_KEY = "deon-fin:sidebar-collapsed";

export function initialSidebarCollapsed(value: string | null): boolean {
  return value === "1" || value === "true";
}

export function sidebarWidthClass(collapsed: boolean): string {
  return collapsed ? "md:w-16" : "md:w-[240px]";
}

export function sidebarLabelClass(collapsed: boolean): string {
  return collapsed ? "md:sr-only" : "";
}

export function toggleSidebarCollapsed(collapsed: boolean): boolean {
  return !collapsed;
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `npm test -- --run web/tests/sidebar.test.ts`

Expected: PASS.

### Task 2: SPA HEAD Fallback

**Files:**
- Modify: `src/web/app.py`
- Test: `tests/test_web_spa.py`

- [x] **Step 1: Write the failing test**

```py
def test_head_requests_are_supported_for_next_export_routes(tmp_path, monkeypatch):
    client = _client_with_export(tmp_path, monkeypatch)

    for path in ["/", "/metas", "/simulador", "/transacoes/?month=2026-06"]:
        response = client.head(path)
        assert response.status_code == 200
        assert response.text == ""
```

- [x] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_web_spa.py::test_head_requests_are_supported_for_next_export_routes -q`

Expected: FAIL with 405 before the route decorators include HEAD.

- [x] **Step 3: Write minimal implementation**

Update the root, legacy, and SPA fallback decorators:

```py
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def index(request: Request) -> Response:
    ...

@app.api_route("/legacy", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)
def legacy(request: Request) -> Response:
    ...

@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def spa_fallback(full_path: str) -> Response:
    ...
```

- [x] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_web_spa.py::test_head_requests_are_supported_for_next_export_routes -q`

Expected: PASS.

### Task 3: Responsive App Shell

**Files:**
- Modify: `web/components/layout/Sidebar.tsx`
- Modify: `web/components/layout/SidebarFooter.tsx`
- Modify: `web/components/layout/Header.tsx`
- Modify: `web/components/charts/HistoryBarChart.tsx`
- Modify: `web/components/charts/TagDonut.tsx`

- [x] **Step 1: Implement desktop collapsed rail**

Use `sidebarWidthClass`, `sidebarLabelClass`, `SIDEBAR_STORAGE_KEY`, and `toggleSidebarCollapsed` in `Sidebar`. Render desktop as `hidden md:flex`; expanded width is `240px`, collapsed width is `64px`, labels become `md:sr-only`, and links/buttons expose `title` and `aria-label`.

- [x] **Step 2: Implement mobile drawer**

Render a fixed `md:hidden` menu button at the top-left, a backdrop, and a `w-[280px]` drawer that reuses the same navigation groups. Close the drawer on backdrop click, close button, and nav link click.

- [x] **Step 3: Keep header content clear of the mobile menu button**

Change the header padding from `px-4` to `pl-14 pr-4 sm:px-6` so page titles do not sit under the fixed menu button.

- [x] **Step 4: Stabilize chart containers**

Add `min-h` and `min-w` constraints to Recharts wrappers:

```tsx
<div className="h-[280px] min-h-[280px] min-w-[220px] w-full">
```

```tsx
<div className="relative h-[260px] min-h-[260px] min-w-[220px] w-full">
```

- [x] **Step 5: Run frontend verification**

Run:

```bash
npm test -- --run web/tests/sidebar.test.ts
npm run lint
npm run typecheck
npm run build
```

Expected: all commands exit 0.

### Task 4: Full Verification and Deployment

**Files:**
- Existing CI/CD scripts and deployment target only.

- [x] **Step 1: Run backend regression**

Run: `.venv\Scripts\python.exe -m pytest tests/test_web_spa.py tests/test_web_app.py -q`

Expected: PASS.

- [x] **Step 2: Verify in browser**

Use the in-app browser at `http://127.0.0.1:8000/` after `npm run build`. Check desktop expanded/collapsed sidebar, mobile drawer behavior, and absence of visible layout overlap.

- [ ] **Step 3: Commit and push**

```bash
git add docs/superpowers/plans/2026-06-21-responsive-sidebar.md web/lib/sidebar.ts web/tests/sidebar.test.ts web/components/layout/Sidebar.tsx web/components/layout/SidebarFooter.tsx web/components/layout/Header.tsx web/components/charts/HistoryBarChart.tsx web/components/charts/TagDonut.tsx src/web/app.py tests/test_web_spa.py
git commit -m "feat: add responsive sidebar"
git push origin main
```

- [ ] **Step 4: Deploy to VPS**

```bash
ssh minha-vps 'set -euo pipefail; cd /opt/projetos/financas-agent; if [ -n "$(git status --porcelain --untracked-files=no)" ]; then git status --short; echo "tracked working tree changes present; refusing deploy"; exit 1; fi; git fetch deon main; git checkout main; git pull --ff-only deon main; ./scripts/vps_deploy.sh'
```

Expected: deployment recreates the production container and preserves a SQLite backup.
