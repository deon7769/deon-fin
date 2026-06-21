# 00 — Contexto e Arquitetura (primer dos specs da nova UI)

> **Leia este documento antes de qualquer spec `Fx.y`.** Ele é a fonte da verdade
> compartilhada: mapa do código atual, modelo de dados estendido, convenções de API,
> design tokens e as decisões de reconciliação entre a nova UI (print) e o código que
> já existe. Cada spec assume o que está aqui e **não** repete estas definições.

Data: 2026-06-20 · Repositório: `deon7769/deon-fin` · Branch alvo sugerido: `feat/ui-nova`

---

## 1. Objetivo

Evoluir o `deon-fin` para a interface mostrada no print do usuário (dashboard dark com
Painel, Orçamento, Metas, Contas, Faturas, Transações, Tags e Perfil), **reaproveitando ao
máximo o backend Python já existente** (FastAPI + módulos de domínio) e adicionando um
frontend **Next.js** que consome uma API HTTP.

O trabalho está fatiado em specs independentes (`docs/specs/Fx.y-*.md`), uma por tarefa.
Cada spec é detalhado o suficiente para um agente/dev implementar de ponta a ponta
(backend + frontend + testes) sem precisar reinterpretar o print.

---

## 2. Estado atual do código (mapeado em 2026-06-20)

> Resumo factual do que existe hoje. Confirme lendo os arquivos citados antes de codar.

### 2.1 Backend (Python 3.12, FastAPI, SQLite, Typer)

- **App FastAPI:** `src/web/app.py` → `create_app()` (factory). Tem:
  - Dependências `get_db()` (cria `Database(settings.database_path)` por request, `check_same_thread=False`) e `get_pluggy()`.
  - Middleware **Basic Auth** (liga quando `APP_PASSWORD` definido; libera só `/api/health`).
  - **Auto-sync** Pluggy no startup + agendador em thread daemon (`_start_auto_sync`, `_sync_all_items`), e `BackgroundTasks` para sync por item.
  - **Endpoints existentes:** `GET /`, `GET /api/health`, `POST /api/connect-token`, `POST /api/items`, `GET /api/items`, `GET /api/sync-status`, `POST /api/sync-all`, `POST /api/items/{id}/sync`, `DELETE /api/items/{id}`, `GET /api/summary?days=`, `GET /api/dashboard?meses=`, `GET /api/cartao`, `GET/POST /api/maintenance`, `POST /api/simular`, `POST /api/amortizacao`, `POST /api/analyze` (streaming LLM).
- **Domínio (`src/agent/`):**
  - `context.py` → `build_financial_context(db, monthly_income, goals, period_months, family_profile)` retorna um dict rico via `.to_dict()`: `contas` (lista `{nome, tipo}` — **anonimizada**, sem saldo), `fluxo_mensal` (`{ 'YYYY-MM': {renda, gasto, investido} }`), `gasto_por_categoria` (`{categoria, total, qtd, media_mensal}`), `recorrencias_provaveis`, `custo_financeiro`, `compromissos_futuros` (`total`, `por_categoria`, `por_mes`), `investido_total`, `pagamentos_cartao_total`, `media_gasto_mensal`, `media_renda_mensal`, `meses_cobertos`, `perfil_familiar` (patrimônio, provisões, metas, receitas). Também expõe helpers de **sinal** (ver §5.3) e `_merchant_key`, `NON_SPENDING_CATEGORIES`.
  - `budget.py` → **50/30/20** (`summarize_5030`: blocos `essencial/desejos/financeiro` via `BUDGET_MAP`), KPIs executivos (`summarize_executivo`: `fixa/variavel/patrimonial`), `summarize_wishlist`. **Não existe** o modelo de 6 potes do print (ver §5.1).
  - `cards.py` → `card_monthly_breakdown(db, today, cat_map, income)`: agrega contas de crédito por mês (`tipo` = `realizado|atual|futuro`), `por_categoria`, `por_cartao`, `top_comerciantes`, `alertas`, `resumo` (`fatura_mes_atual`, `gasto_realizado`, `futuro_parcelado`, `media_faturas`, `pct_renda_comprometida`). É a base de **Faturas** (F2.4).
  - `categorizer.py` → `Categorizer` com `DEFAULT_RULES` (regex → categorias PT granulares, ex.: `"Alimentação - Restaurante"`, `"Transporte - App"`) e `apply_to_database(db, overwrite_pluggy=False)`. Base da auto-sugestão de **Meta** (F1.1).
  - `analyst.py` (LLM multi-provedor), `simulator.py`, `anonymize.py`, `maintenance.py` (`load_family_profile`, `save_family_profile`, `load_overrides`, `save_overrides`, `translate_category`, `income_from_profile`, `apply_recurrence_overrides`), `context.py`.
- **Storage (`src/storage/db.py`):** classe `Database` com `SCHEMA` (executado no `__init__` via `executescript`). Tabelas atuais: `accounts`, `transactions`, `pluggy_items` (detalhe em §4.1). Métodos: `upsert_account`, `insert_transactions` (dedup por `id`=fingerprint sha1), `list_accounts`, `list_transactions(account_id, since, limit)`, `count_transactions`, upsert/list/get/delete de `pluggy_items`, `_cursor()` (contextmanager). **Não há** migrations versionadas — o schema é idempotente via `CREATE TABLE IF NOT EXISTS`.
- **Config (`src/config.py`):** `Settings` (frozen dataclass) + `settings` global. Campos relevantes: `database_url`/`database_path` (`sqlite:///data/financas.db`), `monthly_income`, `financial_goals`, `family_profile` (de `data/family_profile.json`), `analyst_*` (multi-LLM), `auto_sync_*`, `app_user`/`app_password`.
- **Importers (`src/importers/`):** `ofx.py`, `csv_generic.py`, `csv_nubank.py`, `pluggy_sync.py` (`sync_pluggy_item`), `base.py`. Dedup por fingerprint preservado.
- **CLI (`src/cli.py`, Typer):** `connectors`, `sync`, `import-ofx`, `import-nubank`, `categorize`, `report`, `serve`.
- **Testes (`tests/`):** pytest cobrindo storage, categorizer, importers, budget, cards, analyst, simulator, maintenance, web_app, etc. `tests/conftest.py` tem fixtures de DB. **Todo spec deve adicionar/expandir testes** (o projeto valoriza TDD — ver `docs/superpowers/plans/`).

### 2.2 Frontend atual (legado)

- Server-rendered: `src/web/templates/index.html` (377 linhas) + `src/web/static/app.js` (1010) + `app.css` (214), com **Chart.js** e **marked.js**. Abas: Dashboard, Cartões, Simulador, Manutenção, Conexões. Título "Raio-X Financeiro".
- **Este front legado permanece funcionando** durante a migração. A nova UI Next.js é construída em paralelo (ver §3.2). Não apague `src/web/` sem um spec dedicado de descontinuação.

### 2.3 Infra

- `Dockerfile` + `docker-compose.yml`; deploy em VPS (`docs/ops/vps-deploy.md`, `scripts/vps_deploy.sh`). A produção é a fonte operacional (ver `docs/superpowers/specs/2026-06-19-*`). Mudanças de schema precisam ser seguras em produção (migrations idempotentes, sem destruir dados).

---

## 3. Decisões de arquitetura

### 3.1 Stack escolhida
- **Backend:** manter Python/FastAPI; expor os dados via API JSON sob **`/api`** (estender o app existente; ver F0.1). Não reescrever os módulos de domínio — encapsular o acesso a dados em uma **camada de repositórios** (`src/web/repositories/` ou `src/storage/queries.py`) para que os routers não falem SQL cru.
- **Frontend:** **Next.js 14+ (App Router) + TypeScript + Tailwind CSS**, **TanStack Query** (estado de servidor), **Recharts** (gráficos), **lucide-react** (ícones). Pasta **`web/`** na raiz do repo.
- **Banco:** continuar **SQLite** via `Database`. O roadmap prevê Postgres/Supabase no futuro — manter SQL isolado nos repositórios.

### 3.2 Onde o frontend roda
- **Dev:** Next em `http://localhost:3000`, API em `http://127.0.0.1:8000`. `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api`. CORS liberado para `localhost:3000` (F0.1).
- **Prod/VPS:** build estático/SSR do Next servido atrás do mesmo domínio; a API continua em `/api`. Documentar no spec de deploy (fora do escopo destes specs de UI, mas F0.2 deixa o `next.config` pronto para `basePath`/proxy).
- **Auth:** o Basic Auth atual protege tudo exceto `/api/health`. O front deve suportar enviar credenciais (em dev, via proxy ou header). F0.1 detalha (ex.: permitir `APP_PASSWORD` vazio em dev).

### 3.3 Versionamento de API
- Novos endpoints da nova UI vão sob **`/api`** (mesmo prefixo). Quando um endpoint novo tiver shape diferente de um já usado pelo front legado (ex.: `/api/dashboard`), **criar um endpoint novo** (ex.: `/api/v2/dashboard` ou `/api/painel`) em vez de quebrar o existente. Cada spec declara explicitamente se cria novo ou estende.

---

## 4. Modelo de dados consolidado (fonte da verdade)

> Toda mudança de schema é feita por **migrations idempotentes**. Como hoje não há runner,
> **F0.1 cria `src/storage/migrations.py`** (lista ordenada de migrations + `apply_migrations(conn)`
> chamado no `Database.__init__` após o `SCHEMA`). Migrations usam `CREATE TABLE IF NOT EXISTS`
> e `ALTER TABLE ADD COLUMN` guardado por checagem em `PRAGMA table_info`. Nunca destrutivas.

### 4.1 Tabelas existentes (não quebrar)
```
accounts(id TEXT PK, source, institution, name, type, currency, metadata_json, created_at)
transactions(id TEXT PK, account_id, posted_at, amount REAL, description, raw_description,
             category, category_source, source, external_id, metadata_json, created_at)
pluggy_items(id TEXT PK, connector_id, connector_name, status, client_user_id,
             last_synced_at, metadata_json, created_at, updated_at)
```

### 4.2 Colunas novas em `transactions` (F0.1, usadas por F1.1/F1.2/F2.2)
| coluna | tipo | semântica | tela |
|---|---|---|---|
| `bucket_id` | INTEGER NULL → `budget_buckets(id)` | a **"Meta"** (1 dos 6 potes) | Transações, Orçamento |
| `bucket_source` | TEXT | `'auto' \| 'manual' \| 'rule'` | F1.1 |
| `tag_id` | INTEGER NULL → `tags(id)` | tag única exibida | Transações, Tags |
| `reference_month` | TEXT `'YYYY-MM'` | **mês de competência** (ver §5.4); default = mês de `posted_at` | filtros, Orçamento |
| `hidden` | INTEGER DEFAULT 0 | "Ocultar dos Relatórios" | Transações |
| `note` | TEXT NULL | "observação" do usuário | Transações |

> Mantemos `category` (granular, do categorizer/Pluggy) **e** adicionamos `bucket_id` (macro/6 potes).
> São camadas diferentes: `category` é o "o quê" (Restaurante, Farmácia); `bucket` é o "para que serve no orçamento".

### 4.3 Tabelas novas
```
-- 6 potes do método (F1.1). Seed fixo + editável (previsto) na tela Metas (F2.6).
budget_buckets(
  id INTEGER PK, key TEXT UNIQUE,        -- 'liberdade_financeira','custos_fixos','conforto','metas','prazeres','conhecimento'
  name TEXT, color TEXT,                 -- cor hex p/ a UI
  planned_kind TEXT,                     -- 'percent' | 'amount'
  planned_value REAL,                    -- % da renda OU valor fixo previsto
  sort_order INTEGER, is_system INTEGER DEFAULT 1
)

-- Tags livres (F1.2). Seed opcional com as 7 do print.
tags(id INTEGER PK, name TEXT UNIQUE, color TEXT, created_at TEXT)

-- Regras aprendidas de Meta por comerciante/descrição normalizada (F1.1 auto-sugestão).
bucket_rules(id INTEGER PK, match_key TEXT UNIQUE, bucket_id INTEGER, created_at TEXT)

-- Perfil do usuário, linha única (F2.7). Substitui/escora o uso de family_profile.json p/ os campos da tela.
profile(id INTEGER PK CHECK(id=1), name TEXT, email TEXT, monthly_income REAL,
        financial_month_start_day INTEGER DEFAULT 1, goals_text TEXT, updated_at TEXT)

-- Snapshot de saldo/limite por conta (F2.5) — resolve a lacuna de saldo (ver §5.2).
account_balances(account_id TEXT PK → accounts(id), balance REAL, credit_limit REAL,
                 used REAL, available REAL, last_sync_at TEXT, sync_status TEXT, updated_at TEXT)
```

> **Os 6 potes (seed):** `Liberdade Financeira`, `Custos Fixos`, `Conforto`, `Metas`, `Prazeres`, `Conhecimento`.
> Cores sugeridas (ajustáveis): verde, azul-aço, ciano, roxo, laranja, vermelho-vinho.

### 4.4 As 7 tags do print (seed de F1.2)
`Alimentação` (amarelo), `Conforto` (vermelho), `Educação` (azul-claro), `Lazer` (vinho), `Saúde` (azul), `Transporte` (laranja), `Vestuário` (roxo).

---

## 5. Reconciliações importantes (onde a UI nova encontra o código atual)

### 5.1 "Meta" (6 potes) × 50/30/20 existente
- O print usa **6 potes** por transação. O código tem **50/30/20** (`budget.py`) derivado de `category`.
- Decisão: introduzir `budget_buckets` + `transactions.bucket_id` como **camada primária** da nova UI.
  Criar um **mapa default `category → bucket`** (em F1.1, reaproveitando o espírito do `BUDGET_MAP`) para
  pré-preencher `bucket_id` na importação/categorização; o usuário pode sobrescrever (manual) e a sugestão
  propaga para similares. O 50/30/20 continua disponível como visão alternativa (não remover `budget.py`).

### 5.2 Saldo das contas (lacuna real)
- `accounts` **não** guarda saldo; `context.contas` é anonimizado (`{nome, tipo}`). A tela **Contas** (F2.5) e o
  KPI "Saldo em conta" (F2.1) precisam de saldo/limite reais.
- Decisão: F2.5 cria `account_balances` e popula no sync do Pluggy (estender `pluggy_sync` para gravar saldo/limite
  do payload de contas do Pluggy). Para contas manuais (OFX/CSV), permitir saldo informado. Os KPIs leem `account_balances`.

### 5.3 Sinais (receita vs despesa)
- Convenção canônica do projeto (ver `docs/superpowers/specs/2026-06-19-financial-signs-design.md`): banco — débito negativo, crédito positivo; **cartão — compra positiva, pagamento/estorno negativo**. Use os helpers de sinal de `context.py` (ex.: `spending_value`, `income_value`) — **não** interprete `amount` cru. Receitas/Despesas/Resultado nos KPIs e na lista derivam desses helpers.

### 5.4 Mês de competência ("Mês de referência")
- O filtro global é por **competência**, não data civil pura. Usa `profile.financial_month_start_day` (tela Perfil, F2.7):
  se o início é dia 15, lançamentos de 15/jun..14/jul pertencem a `2026-06`. F0.1 fornece um util
  `reference_month(posted_at, start_day) -> 'YYYY-MM'` (Python) e F0.3 o equivalente no front. `transactions.reference_month`
  é materializado na importação e recalculável por um comando/endpoint quando `start_day` muda.

### 5.5 Identidade do usuário
- App é uso pessoal/familiar (1 perfil). Não há multiusuário. `profile` é linha única (`id=1`). Auth é Basic Auth opcional.

---

## 6. Convenções de API (todas as tarefas seguem)

- Base `/api`, JSON, `Content-Type: application/json`.
- **Erros:** `{ "error": { "code": string, "message": string } }` + status HTTP adequado (handler global em F0.1).
- **Período (recorrente):** `?month=YYYY-MM` (competência) **ou** `?from=YYYY-MM-DD&to=YYYY-MM-DD`. Quando ambos ausentes, default = mês de competência atual.
- **Paginação:** `?page=1&page_size=10` → `{ items, page, page_size, total }`.
- **Money:** números (float) em BRL; o **frontend** formata (`Intl.NumberFormat('pt-BR', {style:'currency',currency:'BRL'})`). Nada de string de moeda na API.
- **Datas:** ISO `YYYY-MM-DD` na API; front exibe `dd/MM/yyyy`.
- **Mutação de transação:** sempre `PATCH /api/transactions/{id}` com campos parciais (`bucket_id?`, `tag_id?`, `hidden?`, `note?`, `reference_month?`).
- **Compat:** não alterar shape de `/api/summary`, `/api/dashboard`, `/api/cartao` usados pelo front legado; criar endpoints novos quando o shape mudar (§3.3).

---

## 7. Design system (todas as telas)

Dark theme, base quase-preta, superfícies cinza-escuro, **acento amarelo**. Tokens (Tailwind `theme.extend`):
```
bg #0B0B0C · surface #161618 · surface2 #1F1F23 · border #2A2A2E
text #F5F5F6 · muted #9A9AA2 · accent #F5B301 (amarelo)
positive #22C55E (entradas) · negative #EF4444 (saídas)
radius: card 12px, pill 9999px · fonte Inter
```
- **Layout:** sidebar fixa 240px — grupo `MENU` (Painel `/`, Orçamento `/orcamento`, Metas `/metas`, Contas `/contas`, Faturas `/faturas`, Transações `/transacoes`, Tags `/tags`) e `OUTROS` (Perfil `/perfil`, FAQ `/faq`); item ativo em amarelo. Rodapé da sidebar: **Tema** e **Ocultar**. Conteúdo com `<Header>` (título/saudação + `MonthYearPicker` + olho de privacidade).
- **Componentes base (F0.2):** `KpiCard`, `SectionCard`, `MonthYearPicker`, `DataTable`, `Pill`, `ProgressBar`, `BucketSelect`, `TagSelect`, `MoneyText` (respeita "Ocultar" → `••••`), `EmptyState`.
- **Estados:** loading (skeleton), vazio (EmptyState + CTA), erro (retry). Responsivo (sidebar colapsável, tabela com scroll-x). Acessível (foco visível, labels, contraste AA).

---

## 8. Glossário (print → conceito no código)

| Termo na UI | Significado | Onde vive |
|---|---|---|
| **Meta** (coluna/seletor) | 1 dos 6 potes | `budget_buckets` + `transactions.bucket_id` |
| **Metas Financeiras** (Orçamento) | gasto vs previsto por pote | F2.3 + `budget_buckets.planned_*` |
| **Metas** (menu) | configurar o previsto por pote | F2.6 |
| **Tag** | rótulo livre colorido | `tags` + `transactions.tag_id` |
| **Categoria** | classificação granular (Restaurante…) | `transactions.category` (categorizer/Pluggy) |
| **Mês de referência** | competência | `transactions.reference_month` (§5.4) |
| **Ocultar dos Relatórios** | excluir tx de somatórios | `transactions.hidden` |
| **Saldo em conta** | soma de saldos | `account_balances` (§5.2) |
| **Fatura** | gastos do cartão no ciclo | `cards.py` / F2.4 |

---

## 9. Organização dos specs e template

Arquivos em `docs/specs/`:

```
00-contexto-e-arquitetura.md   (este)
README.md                      (índice + ordem + dependências)
F0.1-api-e-migrations.md
F0.2-scaffold-frontend.md
F0.3-estado-global-periodo-ocultar-tema.md
F1.1-meta-6-potes-e-auto-sugestao.md
F1.2-tags.md
F2.1-painel-dashboard.md
F2.2-transacoes.md
F2.3-orcamento.md
F2.4-faturas.md
F2.5-contas.md
F2.6-metas.md
F2.7-perfil.md
F3.1-deploy-vps-same-origin.md
```

**Template que todo spec segue** (inspirado no estilo `docs/superpowers/`):
1. **Cabeçalho** — id, título, depende de, telas do print cobertas.
2. **Contexto & objetivo** — o que a tela faz, como se liga ao código atual (cite arquivos).
3. **Escopo / fora de escopo.**
4. **Backend** — migrations (se houver), modelo de dados tocado, **contrato de cada endpoint** (método, rota, query/body, resposta JSON de exemplo, erros), reaproveitamento de módulos existentes.
5. **Frontend** — rota, componentes, estados, interações, dados consumidos, comportamento de "Ocultar"/período.
6. **Regras de negócio / edge cases** (sinais, competência, vazio, excedido…).
7. **Plano de implementação** — passos em checkbox `- [ ]`, na ordem (TDD: teste antes), arquivos a criar/modificar.
8. **Critérios de aceite** — verificáveis.
9. **Testes** — unit/integração mínimos.

**Ordem de execução / dependências:** ver `README.md`. Regra geral: F0.* → F1.* → F2.*. F2.1/F2.3 dependem de F1.1; F2.2 depende de F1.1+F1.2; F2.3/F2.6 compartilham `budget_buckets`; F2.4/F2.5 dependem de saldos/cards.
