# deon-fin — Backlog de Prompts para Evoluir a UI

Backlog de tarefas para transformar o `deon7769/deon-fin` (hoje: agente Python — CLI Typer, SQLite, ingestão Pluggy/OFX/CSV, categorizador regex) no app financeiro mostrado no print: dashboard dark theme com Painel, Orçamento, Metas, Contas, Faturas, Transações, Tags e Perfil.

Cada seção abaixo é **uma tarefa = um prompt** pronto para colar no seu agente de código (Claude Code / Cursor / etc.). Faça uma tarefa por vez, na ordem das fases (há dependências). Os prompts estão em blocos delimitados por `~~~` — copie o conteúdo de dentro.

---

## Premissas de arquitetura (lê isto antes de começar)

- **Backend:** manter os módulos Python existentes (`src/pluggy`, `src/storage/db.py`, `src/importers`, `src/agent/categorizer.py`) e expor uma **API HTTP com FastAPI** em `src/api/` que o frontend consome. O comando `src.cli serve` passa a subir a API (e, opcionalmente, servir o build do front).
- **Frontend:** **Next.js 14+ (App Router) + TypeScript + Tailwind CSS**, dark theme por padrão, em `web/`. Estado de servidor com React Query (TanStack Query). Gráficos com Recharts.
- **Banco:** continuar em **SQLite** via a camada `storage/db.py`, estendendo o schema (migrations idempotentes em `src/storage/migrations.py`). O roadmap do README prevê migração futura para Supabase/Postgres — manter o acesso isolado atrás de funções de repositório para facilitar isso.
- **Moeda/locale:** tudo em **BRL** e **pt-BR** (`Intl.NumberFormat('pt-BR', { style:'currency', currency:'BRL' })`, datas `dd/MM/yyyy`).
- **Idempotência:** preservar o dedup por `fingerprint` já existente nas importações.

### Convenções de API
- Base: `/api`. JSON. Erros no formato `{ "error": { "code": string, "message": string } }`.
- Filtro temporal recorrente em vários endpoints: query params `?month=YYYY-MM` (mês de competência) **ou** `?from=YYYY-MM-DD&to=YYYY-MM-DD`.
- Paginação: `?page=1&page_size=10` → resposta `{ items, page, page_size, total }`.

---

## Modelo de dados consolidado (fonte da verdade p/ todos os prompts)

Estender o SQLite com as tabelas/colunas abaixo. Use isto como referência em **todas** as tarefas para manter consistência.

```sql
-- Categorias de orçamento ("Metas" no menu / coluna "Meta" / "Metas Financeiras" do Orçamento)
-- Buckets fixos do método: Liberdade Financeira, Custos Fixos, Conforto, Metas, Prazeres, Conhecimento
category (
  id INTEGER PK,
  name TEXT NOT NULL,
  color TEXT NOT NULL,            -- hex
  planned_kind TEXT NOT NULL,    -- 'percent' | 'amount'
  planned_value REAL NOT NULL,   -- % da renda OU valor fixo previsto
  sort_order INTEGER NOT NULL,
  is_system INTEGER DEFAULT 1
)

-- Tags livres (Alimentação, Conforto, Educação, Lazer, Saúde, Transporte, Vestuário...)
tag (
  id INTEGER PK,
  name TEXT NOT NULL UNIQUE,
  color TEXT NOT NULL
)

-- Transações (estender a tabela existente)
transaction (
  ...campos atuais (id, account_id, date, amount, description, fingerprint, type)...,
  reference_month TEXT,          -- 'YYYY-MM' (mês de competência; default = mês da data)
  category_id INTEGER NULL REFERENCES category(id),   -- "Meta"
  tag_id INTEGER NULL REFERENCES tag(id),
  note TEXT NULL,                -- "observação"
  hidden INTEGER DEFAULT 0       -- "Ocultar dos Relatórios"
)

-- Contas bancárias e cartões (estender/derivar das contas Pluggy)
account (
  id INTEGER PK,
  external_id TEXT,              -- itemId/accountId Pluggy quando houver
  kind TEXT NOT NULL,           -- 'bank' | 'card'
  name TEXT, bank_code TEXT, type TEXT,           -- ex.: 'Conta corrente'
  agency TEXT, number TEXT, brand TEXT,           -- card: 'MASTERCARD'
  last4 TEXT,                                       -- card: '2970'
  balance REAL,                                     -- bank
  credit_limit REAL, used REAL, available REAL,    -- card
  last_sync_at TEXT, sync_status TEXT,
  sort_order INTEGER
)

-- Faturas de cartão
invoice (
  id INTEGER PK,
  account_id INTEGER REFERENCES account(id),
  reference_month TEXT,         -- 'YYYY-MM'
  due_date TEXT, closing_date TEXT,
  total REAL, paid INTEGER DEFAULT 0
)

-- Perfil do usuário (linha única)
profile (
  id INTEGER PK CHECK (id=1),
  name TEXT, email TEXT,
  monthly_income REAL,
  financial_month_start_day INTEGER DEFAULT 1,   -- "Início do Mês Financeiro"
  goals_text TEXT
)
```

Regra de **mês de competência**: o "Mês de referência" de uma transação considera `profile.financial_month_start_day`. Ex.: se o início é dia 15, lançamentos de 15/jun a 14/jul pertencem a `2026-06`.

---

## Design system (use em todos os prompts de frontend)

Dark theme, base quase-preta com superfícies em cinza-escuro e **acento amarelo**. Tokens Tailwind sugeridos:

```
bg:        #0B0B0C   (app)        surface: #161618   (cards)   surface-2: #1F1F23 (inputs/hover)
border:    #2A2A2E
text:      #F5F5F6   text-muted: #9A9AA2
accent:    #F5B301 (amarelo — item ativo, botões primários)
positive:  #22C55E (entradas/receitas)   negative: #EF4444 (saídas/despesas)
radius: 12px (cards) / 9999px (pills)   font: Inter
```

- **Layout base:** sidebar fixa à esquerda (240px) com grupos `MENU` (Painel, Orçamento, Metas, Contas, Faturas, Transações, Tags) e `OUTROS` (Perfil, FAQ); item ativo com fundo amarelo. Rodapé da sidebar: **Tema** (claro/escuro) e **Ocultar** (oculta valores globalmente). Conteúdo à direita com header (saudação/título + filtro Mês/Ano).
- **Componentes reutilizáveis:** `KpiCard`, `SectionCard`, `MonthYearPicker`, `DataTable`, `Pill/Tag`, `ProgressBar`, `CategorySelect`, `TagSelect`, `MoneyText` (respeita o modo "Ocultar" exibindo `••••`).

---

## Mapa: tela do print → tarefa

| # | Tela / funcionalidade no print | Tarefa |
|---|---|---|
| — | API + scaffold + layout/sidebar | F0.1, F0.2 |
| — | Filtro Mês/Ano global + Ocultar + Tema | F0.3 |
| — | Categorias "Meta" + auto-sugestão | F1.1 |
| — | Tags (CRUD + seletor) | F1.2 |
| 1 | "Dashboard inicial com categoria e filtro mês atual" | F2.1 |
| 2 | "Filtro de transações efetuadas" + tabela/edição de meta | F2.2 |
| 3 | "O resultado do orçamento por mês" | F2.3 |
| 4 | "Faturas por mês por cartão" | F2.4 |
| 5 | "As contas conectadas" | F2.5 |
| 6 | "Metas" (configurar previsto por categoria) | F2.6 |
| 7 | "Perfil" | F2.7 |

---

# FASE 0 — Fundação

## F0.1 — Expor backend como API FastAPI

~~~text
Contexto: repositório deon7769/deon-fin. Hoje há módulos Python (src/pluggy/client.py, src/storage/db.py, src/importers/*, src/agent/categorizer.py) e uma CLI Typer (src/cli.py). Quero expor uma API HTTP que um frontend Next.js vai consumir, reaproveitando esses módulos sem reescrevê-los.

Objetivo: criar src/api/ com FastAPI servindo /api, e fazer `python -m src.cli serve` subir o uvicorn.

Tarefas:
1. Adicionar fastapi + uvicorn ao requirements.txt.
2. Criar src/api/app.py com create_app() (FastAPI), CORS liberado para http://localhost:3000, prefixo /api e um router por domínio (health, transactions, accounts, categories, tags, budget, invoices, dashboard, profile) — pode deixar os routers vazios por enquanto, só com GET /api/health retornando {status:"ok"}.
3. Criar camada src/api/repositories/ com funções que encapsulam o acesso ao SQLite (storage/db.py). Nenhum endpoint deve falar SQL direto.
4. Padronizar erros: handler que retorna {"error":{"code","message"}} e status adequado.
5. Atualizar src/cli.py: o comando `serve` agora sobe uvicorn src.api.app:app (manter flags --host/--port). Manter o widget Pluggy Connect acessível (ex.: servir em /connect ou manter rota atual).
6. Criar src/storage/migrations.py com migrations idempotentes (CREATE TABLE IF NOT EXISTS / ALTER ... checando colunas existentes) e rodá-las no startup da API e no validate_setup.py. Ainda NÃO crie as tabelas novas — só o esqueleto do runner.
7. Teste: tests/test_api_health.py subindo o app com TestClient e batendo em /api/health.

Critérios de aceite:
- `python -m src.cli serve` sobe a API; GET http://127.0.0.1:8000/api/health → 200 {status:"ok"}.
- pytest passa; nenhum endpoint acessa SQLite fora dos repositories.
- Pluggy Connect continua funcionando.
~~~

## F0.2 — Scaffold do frontend Next.js + layout e sidebar

~~~text
Contexto: backend FastAPI em http://127.0.0.1:8000/api (tarefa F0.1). Quero o frontend do app financeiro deon-fin.

Objetivo: criar web/ com Next.js 14 (App Router) + TypeScript + Tailwind, dark theme, e o shell de layout (sidebar + header) que todas as telas vão reutilizar.

Stack: Next.js App Router, TypeScript, Tailwind, TanStack Query, Recharts, lucide-react (ícones). Cliente HTTP em web/lib/api.ts apontando para NEXT_PUBLIC_API_URL (default http://127.0.0.1:8000/api).

Design tokens (Tailwind theme.extend.colors): bg #0B0B0C, surface #161618, surface2 #1F1F23, border #2A2A2E, text #F5F5F6, muted #9A9AA2, accent #F5B301, positive #22C55E, negative #EF4444. Radius cards 12px, pills full. Fonte Inter.

Entregar:
1. Layout raiz dark com <Sidebar> fixa (240px):
   - Grupo MENU: Painel(/), Orçamento(/orcamento), Metas(/metas), Contas(/contas), Faturas(/faturas), Transações(/transacoes), Tags(/tags).
   - Grupo OUTROS: Perfil(/perfil), FAQ(/faq).
   - Item ativo com fundo accent (amarelo) e texto escuro. Ícones lucide.
   - Rodapé da sidebar: botões "Tema" e "Ocultar" (só a UI por enquanto; comportamento vem na F0.3).
2. <Header> com slot de título/saudação à esquerda e slot de filtro à direita.
3. Componentes base reutilizáveis (stubs estilizados): KpiCard, SectionCard, ProgressBar, Pill, DataTable, MoneyText, EmptyState.
4. Util web/lib/format.ts: formatBRL, formatDate, formatPercent (pt-BR).
5. Provider do TanStack Query e uma página inicial placeholder.
6. README web/ com como rodar (npm i / npm run dev na porta 3000).

Critérios de aceite:
- `npm run dev` sobe em :3000, layout dark com sidebar navegável (rotas placeholder), item ativo destacado.
- Sem erros de TS/lint; componentes base prontos para reuso.
~~~

## F0.3 — Filtro global Mês/Ano + "Ocultar valores" + alternância de Tema

~~~text
Contexto: layout pronto (F0.2). Em quase toda tela há, no topo, um seletor "Mês/Ano" (ex.: "junho/2026"), e na sidebar há "Ocultar" (privacidade) e "Tema".

Objetivo: implementar 3 capacidades globais compartilhadas por todas as telas.

1. MonthYearPicker (componente + estado global):
   - Botão exibindo o mês atual ("junho/2026"); ao abrir, popover com navegação de ano (‹ 2026 ›) e grade de meses jan…dez; mês selecionado em amarelo.
   - Permite escolher meses anteriores, outros anos e período. Estado persistido em context + querystring (?month=YYYY-MM) e em localStorage.
   - Expor hook usePeriod() → { month, setMonth, range } para as telas montarem os filtros de API.
2. Ocultar valores (privacidade):
   - Toggle global (sidebar + ícone de olho ao lado do filtro). Quando ativo, MoneyText renderiza "••••" no lugar dos valores. Estado em context + localStorage. Aplica em todos os KPIs, tabelas e gráficos (tooltips).
3. Tema:
   - Alternância claro/escuro (default escuro) via classe no <html> e next-themes (ou equivalente). Persistir preferência. Tokens já existentes valem para o escuro; criar a variante clara dos tokens.

Critérios de aceite:
- Trocar o mês reflete na URL (?month=) e dispara refetch das telas que usam usePeriod().
- "Ocultar" mascara todos os valores monetários instantaneamente; recarregar mantém o estado.
- "Tema" alterna e persiste.
~~~

---

# FASE 1 — Dados base (categorias "Meta" e Tags)

## F1.1 — Categorias de orçamento ("Meta") + auto-sugestão

~~~text
Contexto: no print, transações têm uma coluna "Meta" (dropdown) e o Orçamento distribui a renda nessas mesmas categorias. São buckets fixos do método: Liberdade Financeira, Custos Fixos, Conforto, Metas, Prazeres, Conhecimento. Ao categorizar uma transação, o sistema deve sugerir a mesma "Meta" para transações do mesmo tipo (mesma descrição/contraparte).

Objetivo: modelar e expor as categorias "Meta", permitir atribuição por transação e auto-sugestão.

Backend (FastAPI + storage):
1. Migration: criar tabela `category` (id, name, color, planned_kind 'percent'|'amount', planned_value, sort_order, is_system) e seed dos 6 buckets com cores distintas. Adicionar coluna `category_id` em `transaction`.
2. Endpoints:
   - GET /api/categories → lista (ordenada por sort_order).
   - PATCH /api/categories/{id} → editar name/color/planned_kind/planned_value/sort_order.
   - PATCH /api/transactions/{id} { category_id } → define a "Meta" da transação.
   - POST /api/transactions/{id}/category { category_id, apply_to_similar?: bool } → ao setar, se apply_to_similar, aplica a mesma categoria às transações "similares" ainda sem meta.
3. Similaridade: normalizar a descrição (lowercase, remover números/datas/ids) e casar por chave normalizada + mesmo sinal (entrada/saída). Reaproveitar a lógica de regras do src/agent/categorizer.py; opcionalmente persistir a regra aprendida para futuras importações.
4. Estender categorizer para, na importação, preencher category_id automaticamente quando houver regra/aprendizado.

Critérios de aceite:
- GET /api/categories devolve os 6 buckets com cor e previsto.
- PATCH define a meta; com apply_to_similar=true, lançamentos equivalentes sem meta recebem a mesma categoria.
- Testes em tests/test_categories.py cobrindo atribuição e propagação por similaridade.
~~~

## F1.2 — Tags (CRUD + seletor)

~~~text
Contexto: o print mostra (a) um seletor de tag com busca "Buscar tag…", botão "+ Criar" e pills coloridas (Alimentação, Conforto, Educação, Lazer, Saúde, Transporte, Vestuário) e (b) uma página "Tags" listando "7 tags encontradas" com cor, nome e ações editar/excluir, além de "+ Criar Tag".

Objetivo: CRUD de tags + componente seletor reutilizável + página de gestão.

Backend:
1. Migration: tabela `tag` (id, name unique, color). Adicionar `tag_id` em `transaction`. Seed opcional com as 7 tags do print.
2. Endpoints: GET /api/tags, POST /api/tags {name,color}, PATCH /api/tags/{id}, DELETE /api/tags/{id} (ao excluir, set null nas transações). PATCH /api/transactions/{id} { tag_id }.

Frontend:
3. Página /tags: header "Aqui você pode criar e visualizar suas tags…", contador "N tags encontradas", tabela com bolinha de cor + nome + ações (editar inline / excluir com confirmação) e botão "+ Criar Tag" (amarelo) abrindo modal (nome + color picker de paleta).
4. Componente <TagSelect>: dropdown com campo "Buscar tag…", ação "+ Criar" no topo, lista de pills coloridas; usado na tabela de transações. Suporta "Selecione uma tag" como vazio.

Critérios de aceite:
- CRUD completo via UI; cores refletidas nas pills.
- <TagSelect> cria tag on-the-fly e a seleciona; busca filtra a lista.
~~~

---

# FASE 2 — Telas

## F2.1 — Painel / Dashboard ("Dashboard inicial com categoria e filtro mês atual")

~~~text
Contexto: tela inicial do print. Header "Boa noite, {Nome}!" + subtítulo "O que está acontecendo hoje?" e filtro Mês/Ano (F0.3) no topo direito, com ícone de ocultar valores.

Objetivo: construir a rota "/" (Painel) consumindo a API, respeitando o período global.

Conteúdo:
1. 4 KPI cards (cada um com ícone de info/tooltip), valores do mês selecionado:
   - "Resultado do Período" (receitas − despesas; verde se ≥0, vermelho se <0) — ex.: R$ 15,50
   - "Receitas" (verde) — ex.: R$ 5.400,00
   - "Despesas" (vermelho) — ex.: R$ 5.384,50
   - "Saldo em conta" (soma dos saldos das contas) — ex.: R$ 67,67
2. "Histórico Financeiro" — SectionCard com subtítulo "Comparativo mensal de entradas e saídas": gráfico de barras agrupadas (Entrada=verde, Saída=vermelho) por mês; toggle de janela 3M / 6M / 1A (default 6M); eixo Y em R$ mil; legenda Entrada/Saída.
3. "Transações por Tags" — SectionCard "Distribuição dos gastos do mês atual": donut chart por tag, com toggle Despesas/Receitas; valor central = total (ex.: R$ 5.384,50); legenda com itens e valores; fatia "Sem Tags" para não categorizadas; botão amarelo "Categorize todas as transações" (leva a /transacoes filtrado por sem tag).

Backend:
- GET /api/dashboard/summary?month=YYYY-MM → { result, income, expense, accounts_balance }.
- GET /api/dashboard/history?window=3m|6m|1a → [{ month, income, expense }].
- GET /api/dashboard/by-tag?month=YYYY-MM&type=expense|income → [{ tag_id, tag_name, color, total }] incluindo bucket "Sem Tags".

Critérios de aceite:
- KPIs, barras e donut refletem o mês do filtro global e o modo "Ocultar".
- Toggle 3M/6M/1A e Despesas/Receitas refazem a consulta/curva.
- Estados de loading (skeleton) e vazio.
~~~

## F2.2 — Transações: tabela + filtros avançados + edição inline ("Filtro de transações efetuadas")

~~~text
Contexto: telas do print "Filtro de transações efetuadas" e "Transações feitas nas contas com a meta categorizada, podendo editar manualmente, já sugerindo nas do mesmo tipo". Depende de F1.1 (categorias) e F1.2 (tags).

Objetivo: rota /transacoes com busca, filtros avançados, resumo, tabela editável e paginação.

Cabeçalho da página: título + subtítulo "Aqui você pode visualizar todas suas transações"; botões "Importar transações" e "Nova transação" (amarelo).

Bloco "Filtros e Busca":
- Campo "Pesquisar transação".
- Botão "Mais filtros" com badge da quantidade de filtros ativos → abre painel lateral "Filtros Avançados".
- Linha de filtros ativos como chips (ex.: "Mês: junho/2026 ✕") + link "Limpar tudo".

Painel "Filtros Avançados" (drawer à direita), com header "N filtro(s) será(ão) aplicado(s)":
- Período (date range) — "Selecione uma data" + Limpar.
- Mês de referência (MonthYearPicker) + Limpar/remover.
- Faixa de Valor: "Valor mínimo" / "Valor máximo".
- Tipo de Transação: botões Receitas / Despesas (multi/toggle) + Limpar.
- Metas: chips selecionáveis (Sem meta, Liberdade Financeira, Custos Fixos, Conforto, Metas, Prazeres, Conhecimento) + Limpar.
- Tags: chips + Limpar.
- Rodapé: "Aplicar filtros" (amarelo) e "Limpar tudo".

Resumo (acima da tabela): Entradas (verde), Saídas (vermelho), Saldo.

Tabela (DataTable) com colunas e ações:
- checkbox de seleção (em massa) + toggle/explicação "Ocultar dos Relatórios: use este toggle para excluir transações específicas dos seus relatórios e análises financeiras".
- Descrição (com link "+ Adicionar observação" → edita note).
- Valor (verde/vermelho por sinal), Data (dd/MM/yyyy), Mês de referência, Conta (ícone+nome).
- Meta: <CategorySelect> editável inline — dropdown com "Buscar meta…", opção "Sem meta" e os 6 buckets; ao escolher, perguntar/propagar para similares (apply_to_similar) conforme F1.1.
- Tag: <TagSelect> editável inline.
- Ocultar: toggle por linha (hidden).
- Ações: menu kebab (editar, excluir, duplicar).
- Rodapé: "Mostrando X-Y de Z", "Itens por página" (10/25/50), paginação "Página 1 de N".

Backend:
- GET /api/transactions?month=&from=&to=&q=&type=&min=&max=&category_ids=&tag_ids=&hidden=&page=&page_size= → { items, page, page_size, total, summary:{income,expense,balance} }.
- PATCH /api/transactions/{id} { category_id?, tag_id?, hidden?, note?, reference_month? }.
- POST /api/transactions (nova manual), DELETE /api/transactions/{id}.
- POST /api/transactions/import (multipart: OFX/CSV) reusando src/importers/* e respeitando dedup por fingerprint; retornar quantos importados/ignorados.

Critérios de aceite:
- Filtros avançados combináveis; chips ativos e badge corretos; "Limpar tudo" zera.
- Edição inline de Meta/Tag/Ocultar/observação persiste; ao definir Meta, oferece aplicar às similares.
- Resumo e paginação corretos; "Importar" e "Nova transação" funcionam.
~~~

## F2.3 — Orçamento ("O resultado do orçamento por mês")

~~~text
Contexto: tela "Orçamento" do print. Depende de F1.1 (categorias com "previsto") e das transações categorizadas.

Objetivo: rota /orcamento mostrando renda, gastos e distribuição por categoria no mês selecionado.

Conteúdo:
1. Header "Orçamento" + subtítulo "Controle seu orçamento com base em suas metas e rendimentos." + filtro Mês/Ano.
2. 3 KPI cards:
   - "Sua Renda" (ex.: R$ 10.490,41) — "Soma dos rendimentos deste mês".
   - "Gastos do Mês" (ex.: R$ 6.736,55) — subtítulo "64,22% da renda utilizada" (calcular).
   - "Saldo Restante" (ex.: R$ 3.753,86, verde) — "Valor livre para uso".
3. "Metas Financeiras" — subtítulo "Distribuição da sua renda mensal por categoria": grid de cards (um por categoria) com:
   - nome + % utilizado (canto direito; verde normal, vermelho quando excedido — rótulo "Excedido"); barra de progresso colorida.
   - "Gasto R$X" e "Previsto R$Y" (previsto = planned_value: % da renda OU valor fixo).
   - linha "R$Z restante" (ou "Sem gastos") + link "N transações" (vai para /transacoes filtrado por aquela meta e mês).
4. "Transações não categorizadas" — card colapsável: "N transações sem meta alocada", lista (descrição, data, valor) com ação rápida de atribuir Meta (reusa CategorySelect/F1.1).

Backend:
- GET /api/budget?month=YYYY-MM → {
    income, spent, remaining, used_pct,
    categories:[{ id,name,color, planned, spent, remaining, used_pct, exceeded, tx_count }],
    uncategorized:[{ id, description, date, amount }]
  }. "income" usa rendimentos do mês (ou profile.monthly_income como fallback).

Critérios de aceite:
- Soma dos "previstos" e os percentuais batem; categoria estourada aparece como "Excedido" em vermelho.
- Atribuir meta em "não categorizadas" remove o item da lista e atualiza os cards.
- Respeita período global e "Ocultar".
~~~

## F2.4 — Faturas ("Faturas por mês por cartão onde posso ver cada gasto e categoria")

~~~text
Contexto: tela "Faturas" do print — escolher um cartão e um mês e ver a fatura com cada gasto e sua categoria/tag.

Objetivo: rota /faturas para visualizar faturas de cartão por mês.

Conteúdo:
1. Seletor de cartão (cards visuais; ex.: "Cartão BTG BLACK", bandeira, final ****2970) + seletor de mês de referência.
2. Cabeçalho da fatura: total (ex.: R$ ...), datas de fechamento e vencimento, status (aberta/paga).
3. Tabela de lançamentos da fatura: Data, Descrição, Valor, Meta (categoria, com bolinha de cor), Tag, parcela (x/y quando houver). Permitir editar Meta/Tag inline (reusa F1.1/F1.2).
4. Rodapé: total e, se útil, agrupamento por categoria.

Backend:
- GET /api/cards → cartões (kind='card').
- GET /api/invoices?account_id=&month=YYYY-MM → { invoice:{ total, closing_date, due_date, paid }, items:[{ id, date, description, amount, category, tag, installment }] }.
- Derivar os itens da fatura a partir das transações do cartão no ciclo de competência (usar closing_date/financial_month).

Critérios de aceite:
- Trocar cartão/mês recarrega a fatura; total confere com a soma dos itens.
- Edição de Meta/Tag inline persiste e reflete no Orçamento/Dashboard.
~~~

## F2.5 — Contas ("As contas conectadas")

~~~text
Contexto: tela "Contas" do print: contas bancárias e cartões conectados (Pluggy), com saldos e status de sincronização.

Objetivo: rota /contas para gerenciar contas e cartões.

Conteúdo:
1. Header "Contas" + subtítulo "Gerencie suas contas bancárias e cartões." Ações à direita: alternância de visão Cards/Lista, ícone Ocultar, "Ordenar Contas", "+ Nova conta" (amarelo, abre Pluggy Connect).
2. 3 KPI cards: "Saldo em contas" (ex.: R$ 67,67), "Dívidas em cartões" (vermelho; ex.: R$ 0,00), "Resultado do período" (verde; ex.: R$ 67,67).
3. "Contas Bancárias (N)" — tabela: Banco (sigla+nome), Tipo (ex.: Conta corrente), Agência/Conta, Saldo, Sincronização (data/hora + "Sincronizado"), Ações (kebab: Sincronizar agora, Atualizar credenciais, Remover).
4. "Cartões (N)" — tabela: Cartão, Final, Bandeira, Limite Total, Utilizado, Disponível, Uso (barra de %), Ações.

Backend (reusar src/pluggy e a sync existente):
- GET /api/accounts → { banks:[...], cards:[...], totals:{ balance, card_debt, period_result } }.
- POST /api/accounts/{id}/sync → dispara sincronização (background) e atualiza last_sync_at/sync_status.
- POST /api/accounts/{id}/credentials → reabre widget p/ a mesma conexão (connect_token).
- DELETE /api/accounts/{id}. PATCH /api/accounts/sort (ordenação). POST /api/connect/token p/ "Nova conta".

Critérios de aceite:
- Listas e KPIs corretos; alternância Cards/Lista; ordenação persiste.
- "Sincronizar" atualiza saldo e timestamp; "Nova conta" abre o Pluggy Connect e, ao concluir, a conta aparece.
~~~

## F2.6 — Metas (configurar "Previsto" por categoria)

~~~text
Contexto: item "Metas" no menu lateral. É onde se define a distribuição planejada da renda entre os buckets (Liberdade Financeira, Custos Fixos, Conforto, Metas, Prazeres, Conhecimento) — o "Previsto" usado pelo Orçamento (F2.3). Depende de F1.1.

Objetivo: rota /metas para configurar as categorias e seus valores previstos.

Conteúdo:
1. Lista das 6 categorias, cada uma com: nome, cor (editável), tipo de previsto (% da renda OU valor fixo) e valor previsto; barra mostrando o realizado do mês como referência.
2. Indicador de soma das %: alertar se a soma dos percentuais ≠ 100% (apenas aviso).
3. Reordenar categorias (drag-and-drop → sort_order). Salvar.
4. (Opcional) Permitir criar categorias extras não-sistema.

Backend: reusar GET/PATCH /api/categories (F1.1); adicionar PATCH /api/categories/sort se necessário.

Critérios de aceite:
- Editar previsto/cor/ordem persiste e reflete imediatamente no Orçamento.
- Aviso de soma ≠ 100% aparece quando aplicável; nada quebra se faltar renda definida.
~~~

## F2.7 — Perfil

~~~text
Contexto: tela "Perfil" do print: "Informações Pessoais — Atualize suas informações de perfil." Depende de F0.1.

Objetivo: rota /perfil para editar os dados do usuário (tabela profile, linha única).

Conteúdo:
1. Avatar com iniciais (ex.: "DA").
2. Formulário: Nome, E-mail, Renda Mensal (BRL), "Início do Mês Financeiro" (dia 1–28, com tooltip explicando o mês de competência), Objetivos Financeiros (textarea). Botão "Salvar" (amarelo).
3. Usar a Renda Mensal como fallback de renda no Orçamento (F2.3) e o "Início do Mês Financeiro" no cálculo de reference_month.

Backend:
- GET /api/profile → dados (criar linha default se não existir).
- PUT /api/profile { name, email, monthly_income, financial_month_start_day, goals_text }.

Critérios de aceite:
- Salvar persiste e reflete na saudação do Painel (nome) e nos cálculos de competência/renda.
- Validações (e-mail válido, dia 1–28, renda ≥ 0) com feedback.
~~~

---

## Sugestão de ordem de execução

1. **F0.1 → F0.2 → F0.3** (fundação: sem isso nada renderiza com dados reais).
2. **F1.1 → F1.2** (categorias e tags são usadas por quase todas as telas).
3. **F2.7 Perfil** (renda + início do mês alimentam Orçamento e competência) — pode vir cedo.
4. **F2.2 Transações** (núcleo do app; valida edição inline e filtros).
5. **F2.1 Painel**, **F2.3 Orçamento**, **F2.6 Metas** (consomem os dados acima).
6. **F2.5 Contas**, **F2.4 Faturas** (dependem de sync/cartões).

## Itens transversais (aplicar em cada tarefa de frontend)
- Estados de **loading** (skeletons), **vazio** (EmptyState com CTA) e **erro** (retry).
- **Responsivo**: sidebar colapsável em telas estreitas; tabelas com scroll horizontal.
- **Acessibilidade**: foco visível, labels em inputs, contraste AA.
- Respeitar **período global** (usePeriod) e **Ocultar valores** em todos os números.
- **Testes**: pytest no backend (por endpoint) e, no mínimo, smoke tests no front.
