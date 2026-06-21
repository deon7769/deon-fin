# Specs da nova UI do deon-fin — índice

Backlog de especificações para evoluir o `deon-fin` (backend Python/FastAPI + SQLite + Pluggy) para a
interface do print: dashboard dark com Painel, Orçamento, Metas, Contas, Faturas, Transações, Tags e Perfil,
com um frontend **Next.js** consumindo a API. Após a paridade das telas principais, Manutenção e Simulador
entram como extensões do mesmo layout.

**Cada arquivo `Fx.y` é uma tarefa** — detalhada o suficiente para um agente/dev implementar de ponta a ponta
(backend + frontend + testes). Comece sempre pelo **`00-contexto-e-arquitetura.md`** (o primer): ele fixa o
modelo de dados, as reconciliações com o código atual, as convenções de API e o design system que todos os
specs assumem.

> O código real foi clonado de `deon7769/deon-fin` e analisado. As specs citam arquivos/funções reais
> (`src/web/app.py`, `src/storage/db.py`, `src/agent/context.py|budget.py|cards.py|categorizer.py`,
> `src/importers/pluggy_sync.py`, `src/pluggy/client.py`). O print de referência e o backlog antigo (genérico)
> ficam em `docs/specs/../_print-reference/` (em `docs/_print-reference/`).

## Arquivos

| # | Spec | Tela do print | Depende de |
|---|---|---|---|
| 00 | `00-contexto-e-arquitetura.md` | — (primer/fundação) | — |
| F0.1 | `F0.1-api-e-migrations.md` | base de API + schema | 00 |
| F0.2 | `F0.2-scaffold-frontend.md` | shell (sidebar/header/design system) | 00, F0.1 |
| F0.3 | `F0.3-estado-global-periodo-ocultar-tema.md` | filtro Mês/Ano, Ocultar, Tema | 00, F0.1, F0.2 |
| F1.1 | `F1.1-meta-6-potes-e-auto-sugestao.md` | coluna/seletor **Meta** (6 potes) | 00, F0.1, F0.2 |
| F1.2 | `F1.2-tags.md` | seletor de tag + página Tags | 00, F0.1, F0.2 |
| F2.1 | `F2.1-painel-dashboard.md` | **Painel** (KPIs, histórico, donut por tag) | F0.*, F1.2 (saldo de F2.5) |
| F2.2 | `F2.2-transacoes.md` | **Transações** (lista, filtros, edição inline) | F0.*, F1.1, F1.2 |
| F2.3 | `F2.3-orcamento.md` | **Orçamento** (renda/gastos, potes, não categorizadas) | F0.*, F1.1 (renda F2.7, previsto F2.6) |
| F2.4 | `F2.4-faturas.md` | **Faturas** (por cartão/mês) | F0.*, F1.1, F1.2 (cartão F2.5) |
| F2.5 | `F2.5-contas.md` | **Contas** (bancos + cartões, saldos, sync) | F0.* (reusa endpoints de item) |
| F2.6 | `F2.6-metas.md` | **Metas** (previsto por pote + poupança) | F0.*, F1.1 |
| F2.7 | `F2.7-perfil.md` | **Perfil** (nome, e-mail, renda, início do mês) | 00, F0.1, F0.2 |
| F3.1 | `F3.1-deploy-vps-same-origin.md` | — (deploy: Next estático same-origin com `/api` na VPS) | 00, F0.1, F0.2 |
| F3.2 | `F3.2-manutencao.md` | **Manutenção** (saúde, ajustes e rotinas operacionais) | F3.1 |
| F3.3 | `F3.3-simulador.md` | **Simulador** (cenários e amortização) | F3.1 |

## Status em 2026-06-21

| Spec | Estado | Observação |
|---|---|---|
| F0.1 | ✅ entregue | API, migrations e convenções financeiras versionadas. |
| F0.2 | ✅ entregue | App Next, design system, toolchain e shell implementados. |
| F0.3 | ✅ entregue | Período global, ocultar valores e tema disponíveis no frontend. |
| F1.1 | ✅ entregue | 6 potes, regras e aplicação no pipeline de sync. |
| F1.2 | ✅ entregue | Tags no backend e frontend. |
| F2.1 | ✅ entregue | Painel novo com KPIs e gráficos. |
| F2.2 | ✅ entregue | Transações com filtros e edição. |
| F2.3 | ✅ entregue | Orçamento por mês e potes. |
| F2.4 | ✅ entregue | Faturas derivadas das transações de cartão. |
| F2.5 | ✅ entregue | Contas, cartões, saldos e ações de sync/remover. |
| F2.6 | ✅ entregue | Metas por pote e metas de poupança (`savings_goals`). |
| F2.7 | ✅ entregue | Perfil familiar/renda exposto na nova UI. |
| F3.1 | ✅ entregue | Next exportado na imagem Docker, servido pela FastAPI com `/legacy` e smoke de `/`. |
| F3.2 | ✅ entregue | Tela Next de saúde/visão operacional sobre `/api/maintenance`; edição segue no legado. |
| F3.3 | ✅ entregue | Simulador no Next com cenários e amortização sobre `/api/simular` e `/api/amortizacao`. |

## Ordem de execução recomendada

1. **Fundação:** F0.1 → F0.2 → F0.3 (sem isso nada renderiza com dados reais).
2. **Domínio:** F1.1 (potes/Meta) → F1.2 (tags). São usados por quase todas as telas.
3. **Perfil cedo:** F2.7 (renda + início do mês alimentam Orçamento e a competência).
4. **Núcleo:** F2.2 (Transações) valida edição inline e filtros.
5. **Derivadas:** F2.1 (Painel), F2.3 (Orçamento), F2.6 (Metas).
6. **Conexões:** F2.5 (Contas — preenche saldo) → F2.4 (Faturas — usa cartão).
7. **Deploy:** F3.1 (Next estático servido pela FastAPI, same-origin, na VPS).
8. **Extensões do layout:** F3.2 (Manutenção) → F3.3 (Simulador).

> Estado atual: F0.1 até F3.3 estão entregues na `main`. A sequência agora é migração das ações de edição
> ainda presas ao legado e Pluggy Connect no Next.

> F2.1 e F2.4 funcionam antes de F2.5, degradando o que depende de saldo/limite (KPI "Saldo em conta"
> mostra "indisponível"; cartão sem limite mostra "—"). F2.5 ativa esses números sem mudar contratos.

## Mecanismo de migrations (importante)

F0.1 cria **um runner de migrations idempotentes** (`src/storage/migrations.py`) chamado no `Database.__init__`.
Specs de feature **acrescentam migrations a essa lista** (nunca destrutivas, guardadas por `PRAGMA table_info`):
- F0.1: colunas novas em `transactions` (`bucket_id, bucket_source, tag_id, reference_month, hidden, note`) + tabelas `budget_buckets, tags, bucket_rules, profile, account_balances` + backfill de `reference_month`.
- F1.1 / F1.2: **seeds** dos 6 potes e das 7 tags.
- F2.5: `accounts.sort_order`, `accounts.pluggy_item_id` + backfill de `account_balances` a partir de `accounts.metadata_json`.
- F2.6: `savings_goals` (metas de poupança — **confirmado**) + import inicial de `family_profile["metas"]`.

## Decisões/reconciliações descobertas na análise do código (registro)

Estas são as divergências entre o "ideal de UI" e o código atual, e como cada spec as resolve:

1. **Sign helpers não existem ainda.** `spending_value`/`income_value` (primer §5.3) só estavam *propostos* no
   plano `docs/superpowers/plans/2026-06-19-financial-signs.md`; `context.py` usa lógica inline. **F0.1**
   materializa esses helpers (refactor comportamento-preservante) e todos os cálculos de receita/despesa os usam.
2. **Não há tabela `invoice`.** **F2.4** deriva a fatura das transações do cartão no ciclo (reusando
   `CREDIT_TYPES`/`_EXCLUDE` de `cards.py`), com datas de fechamento/vencimento aproximadas e marcadas como tais
   até o Pluggy/F2.5 fornecerem datas reais. Sem tabela nova no MVP.
3. **Saldo de conta não é persistido** (lacuna §5.2) — mas o dado **já chega** do Pluggy e é guardado cru em
   `accounts.metadata_json`. **F2.5** normaliza em `account_balances` no `_sync_account` e faz backfill da base
   existente; **F2.1/F2.4** passam a ler dali.
4. **6 potes × 50/30/20.** O print usa 6 potes (`budget_buckets` + `transactions.bucket_id`); o código tem
   50/30/20 (`budget.py`). Mantidos **separados**: os 6 potes são a camada primária da nova UI; `budget.py`
   continua como visão alternativa (não removido). **F1.1** cria o mapa default categoria→pote.
5. **Tela "Metas" não está no print.** **F2.6** cobre os **dois** blocos (decisão do usuário): configurar o
   **Previsto** por pote (alimenta F2.3) **e** metas de poupança reusando `summarize_wishlist` (tabela
   `savings_goals` + import inicial de `family_profile["metas"]`).
6. **Endpoints novos vs legados.** Para não quebrar o front legado ("Raio-X Financeiro"), specs criam endpoints
   novos quando o shape muda: Painel usa `/api/painel/*` (não altera `/api/dashboard`); Faturas/Contas embrulham
   `/api/cartao` e `/api/items*` sem alterá-los (primer §3.3).
7. **Front legado convive.** `src/web` (Jinja + app.js) permanece funcional; o Next vive em `web/`. A
   descontinuação do legado, se desejada, é um spec à parte.

## Decisões fechadas pelo usuário (2026-06-20)

- ✅ **F2.6 inclui metas de poupança** — além da distribuição por pote. Specado por inteiro (`savings_goals` + `summarize_wishlist`).
- ✅ **Remover conexão (F2.5) mantém as transações** já importadas — a conta vira "desconectada", o histórico permanece. Sem opção destrutiva nesta versão.
- ✅ **Deploy same-origin** — o build do Next é servido pela própria FastAPI sob o mesmo domínio/`/api`. Detalhado em `F3.1-deploy-vps-same-origin.md` (Next estático embutido na imagem, Traefik/Tailscale/TLS inalterados).
- ✅ **CI do frontend já habilitado** — o workflow da `main` roda `npm ci`, testes, typecheck, lint e build em `web/`, além do pytest/Docker do backend.
- ✅ **Manutenção e Simulador ficam no novo layout** — entrarão após F3.1 para reaproveitar o deploy same-origin e encerrar dependências visuais do legado.

## Perguntas em aberto (não bloqueiam; revisitar na implementação)

- **Front legado:** manter em `/legacy` indefinidamente ou agendar descontinuação após paridade da nova UI? (spec à parte)
- **Junção renda Perfil × perfil familiar:** hoje `profile.monthly_income` e `family_profile` coexistem (precedência em F2.3); unificar é follow-up.
