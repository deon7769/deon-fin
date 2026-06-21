# F2.1 Painel Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar a tela inicial `/` com KPIs, historico financeiro e distribuicao por tags, consumindo endpoints novos em `/api/painel/*`.

**Architecture:** O backend ganha um repositorio focado em agregacoes por `transactions.reference_month`, usando os helpers canonicos `income_value` e `spending_value` e sem alterar `/api/dashboard` ou `/api/summary`. O frontend substitui o placeholder por um dashboard operacional com hooks TanStack em `web/hooks`, componentes Recharts pequenos e estados loading/erro/vazio. O CTA de "Sem Tags" tambem passa a abrir `/transacoes?semTag=1` ja filtrado.

**Tech Stack:** FastAPI, SQLite, pytest, Next.js App Router, TanStack Query, Recharts, Vitest, TypeScript.

---

## File Structure

- Create `tests/test_painel.py`: testes de repositorio e HTTP para o contrato F2.1, incluindo regressao dos endpoints legados.
- Create `src/web/repositories/painel_repo.py`: validacao de mes, janelas, sumarizacao, historico, composicao por tag e leitura de `account_balances`.
- Create `src/web/routers/painel.py`: rotas `/api/painel/summary`, `/api/painel/history`, `/api/painel/by-tag`.
- Modify `src/web/app.py`: registrar `painel.router` junto dos routers de dominio.
- Modify `tests/test_router_structure.py`: declarar `painel.py` como router esperado.
- Modify `web/lib/types.ts`: tipos `PainelSummary`, `PainelHistoryPoint`, `PainelByTag`, `PainelTagSlice`.
- Modify `web/lib/format.ts`: adicionar `formatMonthShort`.
- Create `web/lib/greeting.ts`: saudacao deterministica por hora e nome.
- Create `web/hooks/usePainel.ts`: hooks `usePainelSummary`, `usePainelHistory`, `usePainelByTag`.
- Create `web/hooks/useProfileName.ts`: nome tolerante a endpoint indisponivel.
- Create `web/components/ui/InfoTip.tsx`, `WindowToggle.tsx`, `TypeToggle.tsx`.
- Create `web/components/charts/HistoryBarChart.tsx`, `TagDonut.tsx`.
- Modify `web/components/layout/Header.tsx`: aceitar subtitulo sem quebrar paginas existentes.
- Modify `web/app/(app)/page.tsx`: implementar o Painel.
- Modify `web/lib/transactions.ts` and `web/hooks/useTransactionFilters.ts`: suportar `semTag=1` como `tag_ids=none`.
- Modify `web/tests/format.test.ts`, `web/tests/transactions.test.ts`; create `web/tests/greeting.test.ts`.

## Tasks

### Task 1: Backend Contract Tests

**Files:**
- Create: `tests/test_painel.py`

- [ ] **Step 1: Write failing repository tests**

Add tests that seed one bank account, one credit account, transactions in `2026-06`, hidden transactions, tags, and account balances. Assertions:

```python
assert painel_repo.month_summary(tmp_db, "2026-06") == {
    "month": "2026-06",
    "result": 5100.0,
    "income": 5400.0,
    "expense": 300.0,
    "accounts_balance": 0.0,
    "accounts_balance_available": False,
}
```

Also cover hidden exclusion, `account_balances` availability, continuous history window length, parity with `build_financial_context(...).to_dict()["fluxo_mensal"]`, `by_tag` including `{tag_id: None, tag_name: "Sem Tags"}`, and `resolve_month`.

- [ ] **Step 2: Write failing endpoint tests**

Use `TestClient(create_app())` with dependency overrides for `get_db` and `get_pluggy`. Assert:

```python
response = client.get("/api/painel/summary?month=2026-06")
assert response.status_code == 200
assert set(response.json()) == {
    "month",
    "result",
    "income",
    "expense",
    "accounts_balance",
    "accounts_balance_available",
}
```

Add tests for invalid `month`, default history length `6`, invalid by-tag `type`, and legacy `/api/dashboard` plus `/api/summary` shape.

- [ ] **Step 3: Verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_painel.py -q
```

Expected: fails because `painel_repo` and `src.web.routers.painel` do not exist.

### Task 2: Backend Implementation

**Files:**
- Create: `src/web/repositories/painel_repo.py`
- Create: `src/web/routers/painel.py`
- Modify: `src/web/app.py`
- Modify: `tests/test_router_structure.py`

- [ ] **Step 1: Implement repository helpers**

Implement:

```python
def resolve_month(db: Database, month: str | None) -> str | None: ...
def window_to_months(window: str | None) -> int: ...
def month_summary(db: Database, month: str) -> dict[str, float | str | bool]: ...
def history(db: Database, months: int) -> list[dict[str, float | str]]: ...
def by_tag(db: Database, month: str, type: Literal["expense", "income"]) -> dict[str, Any]: ...
```

Use SQL only in the repository, `COALESCE(t.hidden, 0) = 0`, joins to `accounts` and `tags`, and helpers `income_value` / `spending_value`.

- [ ] **Step 2: Implement router**

Expose:

```python
@router.get("/painel/summary")
@router.get("/painel/history")
@router.get("/painel/by-tag")
```

Invalid `month` and invalid `type` return HTTP 422. Unknown `window` defaults to 6 months.

- [ ] **Step 3: Register router and structure test**

Import `painel` in `src/web/app.py` and call `app.include_router(painel.router)`. Add `painel.py` to `test_domain_router_modules_exist`.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_painel.py tests\test_router_structure.py -q
```

Expected: all tests in those files pass.

### Task 3: Frontend Utility Tests

**Files:**
- Modify: `web/lib/format.ts`
- Create: `web/lib/greeting.ts`
- Modify: `web/lib/transactions.ts`
- Modify: `web/tests/format.test.ts`
- Create: `web/tests/greeting.test.ts`
- Modify: `web/tests/transactions.test.ts`

- [ ] **Step 1: Write failing tests**

Add Vitest expectations:

```ts
expect(formatMonthShort("2026-06")).toBe("jun");
expect(greetingForHour(8, "Davi")).toBe("Bom dia, Davi!");
expect(greetingForHour(21, "")).toBe("Boa noite!");
expect(semTagFilterFromSearch("1")).toEqual([null]);
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
npm test -- --run web/tests/format.test.ts web/tests/greeting.test.ts web/tests/transactions.test.ts
```

from `web/`.

- [ ] **Step 3: Implement utilities**

Add `formatMonthShort`, `greetingForHour`, and `semTagFilterFromSearch`.

- [ ] **Step 4: Verify GREEN**

Run the same Vitest command and expect the selected tests to pass.

### Task 4: Frontend Dashboard Implementation

**Files:**
- Modify: `web/lib/types.ts`
- Create: `web/hooks/usePainel.ts`
- Create: `web/hooks/useProfileName.ts`
- Create: `web/components/ui/InfoTip.tsx`
- Create: `web/components/ui/WindowToggle.tsx`
- Create: `web/components/ui/TypeToggle.tsx`
- Create: `web/components/charts/HistoryBarChart.tsx`
- Create: `web/components/charts/TagDonut.tsx`
- Modify: `web/components/layout/Header.tsx`
- Modify: `web/hooks/useTransactionFilters.ts`
- Modify: `web/app/(app)/page.tsx`

- [ ] **Step 1: Add typed API hooks**

Create hooks with keys:

```ts
["painel", "summary", month]
["painel", "history", window]
["painel", "by-tag", month, type]
```

- [ ] **Step 2: Add UI controls and charts**

Create small client components. `HistoryBarChart` uses grouped bars for `income` and `expense`; `TagDonut` uses `PieChart`, center total, and a custom legend. Tooltips use `useMoneyFormatter`.

- [ ] **Step 3: Build page**

Replace the placeholder in `web/app/(app)/page.tsx` with:
- `Header` using greeting plus subtitle.
- 4 KPI cards.
- `SectionCard` for historico with `WindowToggle`.
- `SectionCard` for tags with `TypeToggle`, donut, legend, empty/error states, and CTA `/transacoes?semTag=1`.

- [ ] **Step 4: Support semTag on Transacoes**

In `useTransactionFilters`, when `semTag=1`, set `filters.tagIds` to `[null]`; `clearFilters` removes `semTag`.

- [ ] **Step 5: Verify frontend checks**

Run:

```powershell
npm test -- --run
npm run typecheck
npm run lint
npm run build
```

from `web/`.

### Task 5: Full Verification, Review, Deploy

**Files:**
- All touched files.

- [ ] **Step 1: Run full backend verification**

```powershell
.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 2: Run full frontend verification**

```powershell
npm test -- --run
npm run typecheck
npm run lint
npm run build
```

- [ ] **Step 3: Review diff**

Run `git diff --check` and inspect changed files for accidental unrelated edits.

- [ ] **Step 4: Commit and push main**

```powershell
git add docs/superpowers/plans/2026-06-21-f2-1-painel-dashboard.md tests/test_painel.py src/web/repositories/painel_repo.py src/web/routers/painel.py src/web/app.py tests/test_router_structure.py web
git commit -m "feat: add F2.1 painel dashboard"
git push origin main
```

- [ ] **Step 5: Wait CI/CD and deploy VPS**

After GitHub Actions succeeds on `main`, SSH to the VPS and run the deploy script from `/opt/projetos/financas-agent`, then smoke-test `/api/health` and `/api/painel/summary`.

## Self-Review

- Spec coverage: backend summary/history/by-tag, hidden exclusion, account balance degradation, legacy endpoints, greeting, KPIs, charts, privacy-aware formatting, empty/error states, and semTag CTA are represented.
- Placeholder scan: no task uses TBD/TODO/fill later language.
- Type consistency: backend response fields match `PainelSummary`, `PainelHistoryPoint`, and `PainelByTag`; route names match `/api/painel/*`.
