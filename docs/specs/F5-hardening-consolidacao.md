# F5 — Hardening & Consolidação (dívida técnica)

> Consolida o backlog técnico da **revisão de arquitetura** (`docs/arquitetura-review-2026-06-21.md`) e do
> **ADR-001** em sprints executáveis, separadas das features. Ordem lógica abaixo. Não bloqueia produto, mas
> reduz risco e dívida.

| Slice | Tema | Origem |
|---|---|---|
| **F5.1** | SQLite hardening (WAL + busy_timeout) | ADR-001 / R3 |
| **F5.2** | Fonte única de cálculo financeiro | R2 |
| **F5.3** | Decompor `app.py` (extrair legado) | R1 |
| **F5.4** | `startup`/`shutdown` → `lifespan` | R6 |
| **F5.5** | Sunset do front/endpoints legados | R4/R7 |

---

## F5.1 — SQLite hardening (WAL + busy_timeout) · **prioridade alta, custo baixo**
**Por quê:** `get_db` abre conexão por request e o auto-sync escreve em thread paralela → risco de
`database is locked`.
**Tarefas:**
- [ ] No `Database.__init__` (após `executescript(SCHEMA)` e migrations): `PRAGMA journal_mode=WAL;`
  `PRAGMA busy_timeout=5000;` `PRAGMA synchronous=NORMAL;` `PRAGMA foreign_keys=ON;`.
- [ ] Serializar escritas concorrentes (reusar o lock do auto-sync; transações curtas).
- [ ] `vps_deploy.sh`: garantir backup dos arquivos `-wal`/`-shm` junto do `.db`.
- [ ] Teste `tests/test_db_concurrency.py`: sync simulado + escrita de request sem `SQLITE_BUSY`.
**Aceite:** sem `database is locked` sob sync + edição; WAL ativo.

## F5.2 — Fonte única de cálculo financeiro · **prioridade média-alta**
**Por quê:** sinais/renda/competência aparecem no `app.py` legado (`/api/dashboard`, `/api/summary`) **e** nos
repositórios novos → risco de divergência.
**Tarefas:**
- [ ] Centralizar em um módulo de domínio (ex.: `src/agent/finance.py`): `income`/`expense`/`result`,
  precedência de renda, competência — reusando os sign helpers existentes (`income_value`/`spending_value`).
- [ ] Migrar `/api/dashboard` e `/api/summary` legados para consumir esse módulo (comportamento preservado).
- [ ] Teste de **paridade**: mesmo input → mesmo número no legado e no novo (`/api/painel` × `/api/dashboard`).
**Aceite:** nenhum cálculo financeiro duplicado fora do módulo único; teste de paridade verde.

## F5.3 — Decompor `app.py` · **prioridade média**
**Por quê:** `create_app()` ainda concentra factory + endpoints legados + helpers de nomeação + auto-sync + SPA.
**Tarefas:**
- [ ] Extrair endpoints legados para `src/web/routers/legacy.py` (`/api/summary|dashboard|cartao|maintenance|simular|amortizacao|analyze` e itens Pluggy se aplicável).
- [ ] Extrair helpers de nomeação de banco/cartão para `src/web/account_labels.py`.
- [ ] `create_app()` fica só com wiring (middlewares, include_router, SPA, startup).
- [ ] Regressão: `tests/test_web_app.py` verde; rotas inalteradas.
**Aceite:** `app.py` enxuto (só wiring); endpoints e testes intactos.

## F5.4 — `lifespan` (substituir `on_event`) · **prioridade baixa**
**Tarefas:**
- [ ] Trocar `@app.on_event("startup")` por handler `lifespan` (FastAPI atual), mantendo o auto-sync e o guard de pytest.
- [ ] Regressão dos testes de app/health.
**Aceite:** sem `DeprecationWarning`; auto-sync/health iguais.

## F5.5 — Sunset do front/endpoints legados · **quando houver paridade**
**Por quê:** Jinja `/legacy` + endpoints legados coexistem com a nova UI (rollback). Reduzir superfície quando a
nova UI atingir paridade (Painel+Faturas+Orçamento+Contas+Investimentos).
**Tarefas:**
- [ ] Checklist de paridade da nova UI vs legado.
- [ ] Mover/garantir o legado em `/legacy` (toggle `LEGACY_UI`) e marcar endpoints legados como **deprecated**
  (cabeçalho/銘doc), com data de remoção.
- [ ] Migrar o que ainda depende do legado (ex.: widget Pluggy Connect, se aplicável) para o Next.
- [ ] Remover após 1 ciclo estável.
**Aceite:** nova UI cobre tudo; legado isolado/deprecated com plano de remoção.

---

## Itens de produto correlatos (já em andamento — fora deste doc técnico)
Registrados na revisão de arquitetura (R9/R10) e já endereçados por commits recentes; acompanhar, não duplicar:
nomes de banco/cartão sem fallback, traduções de categorias na Manutenção, classificação assistida de tag/meta.
