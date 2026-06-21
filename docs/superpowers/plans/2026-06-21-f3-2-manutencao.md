# F3.2 Manutencao Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `/manutencao` in the Next UI as a read-only operational maintenance screen over the existing `/api/maintenance` endpoint.

**Architecture:** Keep the FastAPI endpoint shape intact and add a focused regression test for it. Add frontend types, a React Query hook, helper functions that derive health/summary rows from `family_profile` and `overrides`, focused presentation components, and a new App Router page linked from the sidebar. Editing remains in the legacy UI for this sprint; the new page surfaces health, counts, missing sections, and review tables without issuing writes.

**Tech Stack:** FastAPI, pytest, Next.js App Router, React Query, TypeScript, Vitest, Tailwind, lucide-react.

---

### Task 1: Backend Regression

**Files:**
- Modify: `tests/test_web_app.py`

- [ ] **Step 1: Add a regression test for `/api/maintenance`**

Append a test that monkeypatches `src.web.app.mnt.load_family_profile` and `src.web.app.mnt.load_overrides`, then asserts that the endpoint keeps returning `{family_profile, overrides}`:

```python
def test_maintenance_endpoint_returns_profile_and_overrides(client, monkeypatch):
    monkeypatch.setattr(
        "src.web.app.mnt.load_family_profile",
        lambda: {"receitas": [{"membro": "Davi", "valor": 1000}]},
    )
    monkeypatch.setattr(
        "src.web.app.mnt.load_overrides",
        lambda: {
            "categorias_pt": {"groceries": "Mercado"},
            "recorrencias": [{"match": "netflix", "tipo": "assinatura", "rotulo": "Netflix"}],
        },
    )

    response = client.get("/api/maintenance")

    assert response.status_code == 200
    assert response.json() == {
        "family_profile": {"receitas": [{"membro": "Davi", "valor": 1000}]},
        "overrides": {
            "categorias_pt": {"groceries": "Mercado"},
            "recorrencias": [{"match": "netflix", "tipo": "assinatura", "rotulo": "Netflix"}],
        },
    }
```

- [ ] **Step 2: Run the backend regression**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_maintenance_endpoint_returns_profile_and_overrides -q
```

Expected: pass, because the backend endpoint already exists. This is a characterization test, not a RED feature test.

### Task 2: Frontend RED For Maintenance Helpers

**Files:**
- Modify: `web/lib/types.ts`
- Create: `web/lib/maintenance.ts`
- Create: `web/tests/maintenance.test.ts`

- [ ] **Step 1: Add TypeScript types**

Add these types to `web/lib/types.ts`:

```ts
export type MaintenanceFamilyProfile = {
  receitas?: Array<{ membro?: string; valor?: number }>;
  provisoes?: Array<{ nome?: string; mensal?: number; alvo?: number; periodicidade_meses?: number }>;
  metas?: Array<{ nome?: string; alvo?: number; atual?: number; prazo?: string }>;
  wishlist?: Array<{ nome?: string; valor_alvo?: number; prazo_meses?: number; guardado?: number; prioridade?: number }>;
  patrimonio?: {
    investimentos_caixa?: Array<{ local?: string; valor?: number; aporte_mensal_recorrente?: number }>;
    imoveis?: Array<{
      nome?: string;
      valor_mercado?: number;
      saldo_devedor?: number;
      aluguel_receita?: number;
      custos?: Record<string, number | undefined>;
    }>;
  };
};

export type MaintenanceOverrides = {
  categorias_pt?: Record<string, string>;
  recorrencias?: Array<{ match?: string; tipo?: string; rotulo?: string }>;
};

export type MaintenanceResponse = {
  family_profile: MaintenanceFamilyProfile;
  overrides: MaintenanceOverrides;
};
```

- [ ] **Step 2: Write failing helper tests**

Create `web/tests/maintenance.test.ts` with tests for:

```ts
import { describe, expect, it } from "vitest";

import {
  buildMaintenanceHealth,
  buildMaintenanceSections,
  maintenanceSummary,
  recurrenceTypeLabel,
} from "@/lib/maintenance";
import type { MaintenanceResponse } from "@/lib/types";

const sample: MaintenanceResponse = {
  family_profile: {
    receitas: [{ membro: "Davi", valor: 5000 }],
    provisoes: [{ nome: "IPTU", mensal: 200 }],
    metas: [{ nome: "Reserva", alvo: 20000, atual: 3500 }],
    wishlist: [{ nome: "Viagem", valor_alvo: 7000, prazo_meses: 10, guardado: 1000 }],
    patrimonio: {
      investimentos_caixa: [{ local: "Inter", valor: 12000, aporte_mensal_recorrente: 500 }],
      imoveis: [{ nome: "Casa", valor_mercado: 300000, saldo_devedor: 120000 }],
    },
  },
  overrides: {
    categorias_pt: { groceries: "Mercado", rent: "Aluguel" },
    recorrencias: [{ match: "netflix", tipo: "assinatura", rotulo: "Netflix" }],
  },
};

describe("maintenance helpers", () => {
  it("summarizes configured sections", () => {
    expect(maintenanceSummary(sample)).toEqual({
      incomeTotal: 5000,
      cashTotal: 12000,
      provisionMonthlyTotal: 200,
      propertyEquity: 180000,
      categoryCount: 2,
      recurrenceCount: 1,
      configuredSections: 8,
      missingSections: 0,
    });
  });

  it("builds section rows with counts and totals", () => {
    expect(buildMaintenanceSections(sample).map((section) => section.key)).toEqual([
      "receitas",
      "caixa",
      "provisoes",
      "metas",
      "wishlist",
      "imoveis",
      "categorias",
      "recorrencias",
    ]);
  });

  it("reports missing sections as review items", () => {
    const health = buildMaintenanceHealth({
      family_profile: {},
      overrides: { categorias_pt: {}, recorrencias: [] },
    });

    expect(health.status).toBe("review");
    expect(health.items.map((item) => item.key)).toContain("receitas");
    expect(health.items.map((item) => item.key)).toContain("categorias");
  });

  it("labels recurrence types", () => {
    expect(recurrenceTypeLabel("assinatura")).toBe("Assinatura");
    expect(recurrenceTypeLabel("recorrencia")).toBe("Recorrência");
    expect(recurrenceTypeLabel("ignorar")).toBe("Ignorar");
    expect(recurrenceTypeLabel("x")).toBe("x");
  });
});
```

- [ ] **Step 3: Verify RED**

Run:

```powershell
cd web
npm test -- --run tests/maintenance.test.ts
cd ..
```

Expected: fail because `@/lib/maintenance` does not exist.

### Task 3: Frontend Helpers GREEN

**Files:**
- Create: `web/lib/maintenance.ts`

- [ ] **Step 1: Implement helper functions**

Create `web/lib/maintenance.ts` with:
- `maintenanceSummary(data)`
- `buildMaintenanceSections(data)`
- `buildMaintenanceHealth(data)`
- `recurrenceTypeLabel(type)`

The implementation must treat missing arrays and invalid numbers as zero, compute property equity as `valor_mercado - saldo_devedor`, and mark status `"ok"` only when all eight sections have at least one item.

- [ ] **Step 2: Verify helpers**

Run:

```powershell
cd web
npm test -- --run tests/maintenance.test.ts
cd ..
```

Expected: pass.

### Task 4: Hook And Presentation Components

**Files:**
- Create: `web/hooks/useMaintenance.ts`
- Create: `web/components/manutencao/HealthChecklist.tsx`
- Create: `web/components/manutencao/MaintenanceSectionTable.tsx`
- Create: `web/components/manutencao/RecurrenceRulesTable.tsx`
- Create: `web/components/manutencao/CategoryMapPreview.tsx`

- [ ] **Step 1: Add the query hook**

Create `web/hooks/useMaintenance.ts`:

```ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MaintenanceResponse } from "@/lib/types";

export function useMaintenance() {
  return useQuery({
    queryKey: ["maintenance"],
    queryFn: ({ signal }) => api.get<MaintenanceResponse>("/maintenance", undefined, signal),
    staleTime: 30_000,
  });
}
```

- [ ] **Step 2: Add focused read-only components**

Add small components that accept already-derived rows and render existing UI primitives:
- `HealthChecklist` renders health items as review rows.
- `MaintenanceSectionTable` renders section counts/totals in `DataTable`.
- `RecurrenceRulesTable` renders up to 8 recurrence rules.
- `CategoryMapPreview` renders up to 10 category mappings.

Keep components presentational; no fetches and no mutations.

### Task 5: Route And Navigation

**Files:**
- Modify: `web/components/layout/nav.ts`
- Create: `web/app/(app)/manutencao/page.tsx`

- [ ] **Step 1: Add nav item**

Import `Wrench` from `lucide-react` and add:

```ts
{ href: "/manutencao", label: "Manutenção", icon: Wrench }
```

Place it in `otherItems`, near Perfil/FAQ, to avoid crowding the primary financial flow.

- [ ] **Step 2: Build the page**

Create `web/app/(app)/manutencao/page.tsx` as a client page using:
- `Header title="Manutenção"`
- `useMaintenance`
- `KpiCard` for income, cash, provisions, and property equity
- `HealthChecklist`
- `MaintenanceSectionTable`
- `CategoryMapPreview`
- `RecurrenceRulesTable`
- loading skeleton, error retry, and empty states

Use a small link button to `/legacy` labeled `"Abrir editor legado"` because editing is intentionally not in this sprint.

### Task 6: Verification, Commit, CI, VPS

**Files:**
- All changed files.

- [ ] **Step 1: Local verification**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
cd web
npm test -- --run
npm run lint
npm run typecheck
npm run build
cd ..
docker build -t financas-agent:f3-2 .
git diff --check
```

- [ ] **Step 2: Runtime smoke**

Run the local FastAPI preview with `WEB_DIST_DIR=web/out`, then smoke:
- `http://127.0.0.1:8000/manutencao`
- `http://127.0.0.1:8000/api/maintenance`

- [ ] **Step 3: Commit, push, CI, VPS**

Commit:

```text
feat: add maintenance screen
```

Push to `origin/main`, wait for the `CI/CD` workflow to succeed, then deploy on `minha-vps` with `./scripts/vps_deploy.sh` and smoke `/manutencao`, `/api/maintenance`, `/`, and `/legacy`.
