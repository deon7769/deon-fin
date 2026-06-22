# F4 — Carteira de Investimentos ("Diagrama do Cerrado")

> **Leia antes:** `00-contexto-e-arquitetura.md`, `F0.1-api-e-migrations.md` (migrations/repos/erros/auth),
> `F0.2-scaffold-frontend.md` (design system/componentes), `F0.3` (período/Ocultar/tema), `F2.5-contas.md`
> (contas/`account_balances`, sync Pluggy). Fonte: `docs/specs/Adição das funções de carteira de investimentos.pdf`.

| Campo | Valor |
|---|---|
| **ID** | F4 (módulo) — fatiado em **F4.1…F4.5** (ver §15) |
| **Título** | Módulo de carteira de investimentos com alocação-alvo, scoring por perguntas e rebalanceamento por aporte |
| **Origem** | Fusão de um programa terceiro estilo **Diagrama do Cerrado** dentro do deon-fin |
| **Telas (abas)** | **Ativos · Metas · Aportar · Perguntas · Mapa** |
| **Depende de** | F0.* (fundação), F2.5 (Pluggy/contas). Novo domínio `src/agent/portfolio/` + `web/app/(app)/investimentos/*` |
| **Não quebrar** | `/api/dashboard` (KPIs `investido_total`), `family_profile`/`/api/maintenance`, contas/sync |

> ✅ **Todas as decisões fechadas** (cotações brapi, Método Burro com fixtures, ingestão Pluggy, Mapa, Renda
> Fixa, banco — §16). **Sprints detalhadas em arquivos próprios** (tarefas para o agente executar):
> `F4.1-investimentos-ativos.md`, `F4.2-investimentos-metas.md`, `F4.3-investimentos-perguntas.md`,
> `F4.4-investimentos-aportar.md`, `F4.5-investimentos-mapa.md`. **Este arquivo é o overview/contrato comum.**
>
> 🎨 **Design do módulo — acento AZUL** (no lugar do amarelo global `accent #F5B301`): defina tokens próprios do
> módulo `/investimentos` —  `invest-accent #3B82F6` (blue-500 → botões, abas ativas, links, "Calcular"/"Aportar"/
> "Salvar"), `invest-accent-hover #2563EB` (blue-600), `invest-ring #38BDF8` (sky-400 → anel do donut/realces),
> `invest-soft #60A5FA`. Mantém **positivo #22C55E / negativo #EF4444**; alerta das Metas **âmbar→vermelho**.
> Todo o módulo de investimentos usa o azul; o resto do app segue amarelo. (Implementar como classe/scope, ex.:
> wrapper `.theme-invest` com as CSS vars, ou variantes `blue` dos componentes `Button`/`Pill`/`Tabs`.)
>
> 🔗 **Alinhamento com o código JÁ ENTREGUE** (commit `feat: add Pluggy investment portfolio`): a ingestão e a
> aba Ativos básica **já existem** — `src/pluggy/client.py::list_investments`, `portfolio_repo`
> (`classify_pluggy_investment`, `upsert_pluggy_asset/transaction`, `list_assets`, `portfolio_summary`),
> `routers/portfolio.py` (`GET /api/investments`), migração **`m0014_portfolio`** com `portfolio_assets`
> (colunas reais: **`current_value, unit_price, manual_value, provider_type/subtype, status, as_of_date,
> metadata_json`**) e `portfolio_transactions`. **Os specs F4.x ESTENDEM** isso (novas migrations **m0015+**;
> nada de recriar tabela). Detalhes de RF (issuer/rate/dueDate) ficam em **`metadata_json`**. Onde este overview
> citar nomes diferentes (ex.: `pluggy_value`), **vale o nome real do código** (`current_value`).

---

## 1. Contexto & objetivo

O deon-fin **já conhece investimentos de forma agregada**: `src/agent/context.py` expõe `investido_total`,
`investimentos_caixa` e `perfil_familiar.patrimonio_consolidado` (de `data/family_profile.json`), e o Pluggy
sincroniza contas (algumas do tipo investimento). Mas **não existe a camada de _posições_** (quantos papéis de
cada ativo, a que preço, qual a alocação por classe). Este módulo adiciona essa camada e um **fluxo de decisão
de aporte** baseado no método "Diagrama do Cerrado":

1. O usuário define **metas de alocação por classe** (ex.: Ações Nacionais 40%, FIIs 15%…), somando 100%.
2. Cada ativo recebe uma **nota** a partir de **perguntas Sim/Não** (qualidade do ativo).
3. Ao informar um **aporte**, o sistema sugere **quais ativos comprar e quanto** (em R$ e em unidades) para
   reequilibrar a carteira em direção às metas, priorizando ativos de **maior nota** e mais **abaixo da meta**.
4. Preços são **consultados em tempo real** para calcular o valor atual e os percentuais.

**Objetivo:** trazer esse fluxo para dentro do deon-fin reaproveitando o que já existe (Pluggy, design system,
camadas routers/repositories), com persistência própria das posições/perguntas/metas e um provedor de cotações.

## 2. Visão geral (abas) e glossário

Seção nova no menu: **"Investimentos"** (rota base `/investimentos`) com sub-navegação:

| Aba | Rota | O que faz |
|---|---|---|
| **Ativos** | `/investimentos` | Lista de ativos que você possui, valor total do patrimônio, % por ativo e por classe (donut), filtro por classe, CRUD de ativo. |
| **Metas** | `/investimentos/metas` | Alocação-alvo por **classe** (sliders, soma 100%) + perfis **Conservador/Moderado/Arrojado**. |
| **Aportar** | `/investimentos/aportar` | Informa o valor do aporte → sugestões de compra por ativo (R$ + unidades) → confirmar por ativo ou "Aportar tudo". |
| **Perguntas** | `/investimentos/perguntas` | CRUD das perguntas de scoring, por **tipo de diagrama** (Ações / Fundos Imobiliários). |
| **Mapa** | `/investimentos/mapa` | **[a definir — §16]** provável visualização (treemap/heatmap) da carteira. |

> **Cuidado de nomenclatura:** o menu já tem **"Metas"** (6 potes do orçamento, F2.6). A aba de investimentos
> chama-se **"Metas"** também, mas vive sob **/investimentos/metas** (alocação de carteira) — são coisas
> diferentes. Manter rótulos no contexto ("Metas da carteira") para não confundir.

Glossário: **Classe** = categoria de ativo (ver §3). **Nota/Pontuação** = score do ativo a partir das
perguntas. **Meta (alocação)** = % alvo por classe. **Aporte** = compra mensal a distribuir. **Método Burro** =
heurística de aporte que só compra (nunca vende) sempre o que está mais abaixo da meta.

## 3. Classes de ativo

As 7 classes do print (dropdown "Tipo de investimento"):
`Ações Nacionais`, `Ações Internacionais`, `Fundos Imobiliários` (FIIs), `REITs`, `Criptomoedas`,
`Renda Fixa`, `Renda Fixa Internacional`.

- **Com cotação por ticker** (preço em tempo real): Ações Nacionais/Internacionais, FIIs, REITs, Criptomoedas.
- **Renda Fixa / RF Internacional**: normalmente **sem ticker/preço de mercado** — tratar por **valor
  informado** (saldo atual), opcionalmente atualizável por marcação (reusar F3.6 Marcação a Mercado). Ver §16.
- **Tipo de diagrama (perguntas):** o PDF mostra dois conjuntos — **"Diagrama do cerrado"** (ações) e
  **"Investimentos imobiliários"** (FIIs). Mapear cada classe a um conjunto de perguntas (ações→cerrado;
  FIIs/REITs→imobiliário; cripto/renda fixa → §16).

## 4. Modelo de dados (novas tabelas — migrations aditivas via runner de F0.1)

```sql
-- Uma posição/ativo da carteira (uma linha por ticker)
CREATE TABLE IF NOT EXISTS portfolio_assets (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_class   TEXT NOT NULL,         -- 'acoes_nac' | 'acoes_int' | 'fii' | 'reit' | 'cripto' | 'rf' | 'rf_int'
  ticker        TEXT,                  -- 'PETR4', 'HGLG11', 'BTC'… (null p/ renda fixa sem ticker)
  name          TEXT,
  quantity      REAL NOT NULL DEFAULT 0,
  source        TEXT NOT NULL DEFAULT 'manual',  -- 'manual' | 'pluggy'
  external_id   TEXT,                  -- id Pluggy quando 'pluggy' (dedup)
  status        TEXT DEFAULT 'ACTIVE', -- Pluggy: ACTIVE | TOTAL_WITHDRAWAL (só ACTIVE entra no cálculo)
  manually_adjusted INTEGER DEFAULT 0, manual_adjusted_at TEXT,  -- usuário editou qtd na mão (Pluggy é + confiável; §6)
  manual_value  REAL,                  -- p/ renda fixa: valor informado (sem cotação)
  pluggy_value  REAL, pluggy_balance REAL,  -- value/balance do snapshot Pluggy (fallback de preço p/ RF)
  -- renda fixa (quando vier do Pluggy):
  issuer        TEXT, rate REAL, rate_type TEXT, fixed_annual_rate REAL, due_date TEXT,
  currency      TEXT DEFAULT 'BRL',
  created_at    TEXT DEFAULT (datetime('now')),
  updated_at    TEXT DEFAULT (datetime('now')),
  UNIQUE(asset_class, ticker)
);

-- Movimentações por ativo (GET /investments/{id}/transactions) — histórico/auditoria de aportes/resgates
CREATE TABLE IF NOT EXISTS portfolio_transactions (
  id            TEXT PRIMARY KEY,      -- id Pluggy (ou hash p/ manual)
  asset_id      INTEGER NOT NULL REFERENCES portfolio_assets(id) ON DELETE CASCADE,
  type          TEXT,                  -- BUY | SELL
  movement_type TEXT,                  -- CREDIT | DEBIT
  trade_date    TEXT,
  quantity      REAL, value REAL, amount REAL, net_amount REAL,
  source        TEXT NOT NULL DEFAULT 'pluggy',
  created_at    TEXT DEFAULT (datetime('now'))
);

-- Perguntas de scoring (por tipo de diagrama)
CREATE TABLE IF NOT EXISTS asset_questions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  diagram_type  TEXT NOT NULL,         -- 'acoes' | 'imobiliario'  (estende em §16)
  criterio      TEXT,                  -- rótulo curto: 'ROE', 'CAGR'…
  pergunta      TEXT NOT NULL,         -- texto da pergunta
  peso          REAL NOT NULL DEFAULT 1,   -- peso da pergunta (default 1)
  sort_order    INTEGER NOT NULL DEFAULT 0,
  ativo         INTEGER NOT NULL DEFAULT 1
);

-- Respostas Sim/Não por ativo (compõem a nota)
CREATE TABLE IF NOT EXISTS asset_answers (
  asset_id      INTEGER NOT NULL REFERENCES portfolio_assets(id) ON DELETE CASCADE,
  question_id   INTEGER NOT NULL REFERENCES asset_questions(id) ON DELETE CASCADE,
  resposta      INTEGER NOT NULL DEFAULT 0,   -- 1 = sim, 0 = não
  PRIMARY KEY (asset_id, question_id)
);

-- Meta de alocação por classe (linha por classe; soma deve dar 100%)
CREATE TABLE IF NOT EXISTS allocation_targets (
  asset_class   TEXT PRIMARY KEY,
  target_pct    REAL NOT NULL DEFAULT 0
);

-- Perfil de investimento selecionado + último aporte
CREATE TABLE IF NOT EXISTS investment_profile (
  id            INTEGER PRIMARY KEY CHECK (id=1),
  perfil        TEXT,                  -- 'conservador'|'moderado'|'arrojado'|'custom'
  ultimo_aporte REAL,                  -- valor salvo do último aporte (UX)
  updated_at    TEXT DEFAULT (datetime('now'))
);
```

- **Nota do ativo** (derivada): `peso_total = Σ peso` das **perguntas ativas** do diagrama da classe;
  `pontos_positivos = Σ peso(Sim)`, `pontos_negativos = Σ peso(Não)`; `bruta = positivos − negativos`
  (∈ [−peso_total, +peso_total]). **Normaliza para uma escala fixa −10..+10, independente da quantidade de
  perguntas:** **`nota = bruta / peso_total × 10`**. Assim "começa em −10 e cada Sim caminha para +10" vale
  sempre — com 10 perguntas de peso 1 cada Sim = +2 (reproduz o print). As perguntas podem ser **mais ou menos
  que 10**; cada uma vale um peso aplicado **conforme o total** (o denominador `peso_total`). A "Nota" exibida é
  `nota`; **só nota > 0 recebe aporte** (§10).
- **Seeds:** as perguntas padrão dos dois diagramas (ROE, CAGR, dividendos, P&D, tempo de mercado; e
  líder/perenidade/governança/independência/endividamento) e as 7 classes em `allocation_targets` (0% inicial).
  Botões "Restaurar padrões" e "Usar modelo" repõem/aplicam esses seeds.

## 5. Dados de mercado (cotações em tempo real)

> **Decisão (confirmada):** provedor primário **`brapi.dev`** (B3 ações/FIIs + cripto); internacionais
> (REITs/ações/RF int) complementados por **Yahoo/Finnhub**. A chave fica no **servidor** (`BRAPI_TOKEN`).

Necessário para preço atual de ações/FIIs/REITs/cripto:
- **Camada provider** `src/agent/portfolio/quotes.py` com interface `get_quote(ticker, asset_class) -> {price, currency, ts}`
  e busca de ticker `search_ticker(q, asset_class) -> [{ticker, name}]` (autocomplete da tela "Adicionar ativo").
- **Provider primário sugerido:** **brapi.dev** (B3: ações/FIIs; tem cripto) — chave gratuita/paga; endpoints
  `/quote/{tickers}` e `/available?search=`. Cripto via brapi ou **CoinGecko**. Ações/REITs internacionais via
  brapi (limitado) ou **Finnhub/Yahoo** (complemento para ativos internacionais).
- **Cache** (ex.: 15 min) em tabela/メmória para não estourar limites e manter a UI rápida; "última atualização"
  por ativo (coluna na lista). Chamadas saem do **backend** (httpx), nunca do browser (chave fica no servidor).
- Config: `QUOTES_PROVIDER`, `BRAPI_TOKEN`, etc. em `settings`. Funções de cálculo permanecem testáveis com
  preços injetados (sem rede em teste).
- **B3 "Área do Investidor" (≠ cotação) — esclarecimento do manual técnico (12/12/2024):** essa API da B3
  retorna a **posição/movimentação do próprio investidor** (Tesouro Direto = `TreasuryBonds`, Renda Fixa =
  `FixedIncome`, etc.), por **licença/autorização do investidor** (OAuth; fluxo *Pacote de Acesso* → *Guia* →
  *Posição*/*Movimentação*; ambiente de Certificação grátis, **produção R$ 500/mês**). Ou seja, é uma
  **alternativa ao Pluggy** para **posições** de RF/Tesouro — **não** fornece preço de ticker arbitrário.
  Decisão: **brapi** segue como provider de **cotações**; a API B3 fica como **opção futura** para enriquecer
  RF/Tesouro do usuário caso o Pluggy não cubra (avaliar o custo de R$ 500/mês antes).

## 6. Fusão com o deon-fin e com o Pluggy

- **O que já existe** (não quebrar): `context.investido_total` (de transações marcadas investimento) e
  `family_profile.caixas_investimentos`/`patrimonio_consolidado`. O módulo novo é a fonte **detalhada** de
  posições; o `investido_total` do dashboard pode passar a **somar** o `valor_total` da carteira (decisão §16).
- **Pluggy traz investimentos (✅ confirmado).** O BTG sincronizado retornou **22 investimentos** via
  `GET /investments?itemId=...` (movimentações por `GET /investments/{id}/transactions`) — endpoints que o app
  **ainda não chama** (hoje só `/accounts` e `/v2/transactions`: `pluggy_sync.py:17`, `client.py:128`). Ação:
  **adicionar `list_investments(item_id)` e `list_investment_transactions(investment_id)`** ao cliente e
  persistir em `portfolio_assets` + `portfolio_transactions` (§4), dedup por `external_id` (id Pluggy).
- **Campos do investimento (mapear):** `code`→`ticker`, `name`→`name`, `type`/`subtype`→`asset_class` (mapa
  abaixo), `quantity`, `value`, `balance`, `status` (**só `ACTIVE` é posição**; `TOTAL_WITHDRAWAL` = encerrado).
  Para renda fixa: `issuer`, `rate`/`rateType`/`fixedAnnualRate`, `issueDate`/`dueDate`. Transações do ativo:
  `type` (BUY/SELL), `movementType`, `tradeDate`, `quantity`, `value`, `amount`, `netAmount`.
- **Mapa type/subtype → classe:** `EQUITY/STOCK` → Ações (Nacional se ticker B3; **sufixo "11" = FII/ETF** →
  Fundos Imobiliários, salvo ETF conhecido); `FIXED_INCOME/CDB|LCI|LCA…` → Renda Fixa; cripto/internacional por
  `currencyCode`/mercado. A classe vinda do Pluggy é **sugerida** e o usuário pode **corrigir** (vários FIIs
  chegam como `EQUITY`). Lista real do BTG p/ teste: ISAE3, BBDC3, GGRC11, AUVP11, WEGE3, TRXF11, HYPE3,
  BTLG11, SAPR3, KLBN3, LEVE3, MXRF11, BBAS3, ITSA3 (+ 2 CDB).
- **Regra de merge:** a **quantidade** do ativo Pluggy vem do sync (read-mostly); **perguntas/nota e classe**
  são editáveis. Manual e Pluggy coexistem (campo `source`); dedup por `(asset_class,ticker)` e por `external_id`.
- **Ajuste manual de quantidade × Pluggy (confiança):** o usuário pode **editar um ativo a qualquer momento
  adicionando/ajustando cotas** — isso muda o valor na carteira e marca `manually_adjusted=1` (+ `manual_adjusted_at`).
  Como **o que vem do Pluggy é mais confiável**, no **próximo sync** a quantidade do Pluggy **prevalece** e
  **limpa o flag** (com aviso de que o valor manual foi sobrescrito). Ou seja, o ajuste manual vale **até o
  próximo sync**; para ativos só-manuais (sem Pluggy) ele persiste.

## 7. Aba **Ativos** (`/investimentos`)

**UI (do print):** título "Ativos — Gerencie os ativos que você possui", busca, botão **"Adicionar ativo"**,
seletor de moeda (BRL), **pills de filtro por classe** (Todos + as 7 classes), **Lista de Ativos** e **donut
"Carteira"** com total e % por classe.

- **Tabela "Lista de Ativos":** colunas **Tipo** (badge da classe), **Ticker**, **Valor atual** (`qtd*preço`),
  **Percentual (%) na carteira** (`valor_atual/PL` — o mesmo % do donut; o peso **dentro da classe** p/ o aporte
  vem das **notas**, não deste %), **Nota**,
  **Quantidade**, **Última atualização** (do preço), **Ação** (Editar). Ordenar por nota/percentual.
- **Donut "Carteira":** `valor_total = Σ valor_atual`; fatias por classe com %. Legenda lista as 7 classes.
- **Adicionar ativo (modal):** dropdown "Tipo de investimento" (7 classes) → campo **Ticker** com
  **autocomplete** (`search_ticker`, ex.: "pet" → PETR3/PETR4/PETZ3) → **Quantidade** → "Adicionar". Para
  Renda Fixa, em vez de ticker/qtd, **valor informado** (§3/§16).
- **Editar ativo (modal):** Tipo, Ticker, Quantidade, cartões **Pontos positivos / Pontos negativos /
  Pontuação final**, e a **lista de perguntas com toggles** (Sim/Não) do diagrama da classe. Botões
  **Remover** (vermelho) e **Atualizar e fechar**. Editar a **quantidade** marca o ativo como **ajuste manual**.
- **Badge de "ajuste manual":** ativos com `manually_adjusted=1` mostram um **selo/ícone** (ex.: lápis "✏️
  manual") na lista e no card, com tooltip "valor ajustado manualmente; o Pluggy sobrescreve no próximo sync".
  Sinaliza **menor certeza** que os dados vindos do Pluggy (§6).
- Respeita **Ocultar** (F0.3) nos valores; estados loading/vazio/erro.

## 8. Aba **Metas** (`/investimentos/metas`)

**UI:** "Metas de Investimento — Edite os itens abaixo para ajustar suas metas." Bloco "Perfil de Investimento"
com 3 cards **Conservador / Moderado / Arrojado** (cada um aplica um preset de %), **donut "Total: 100%"**, e
**sliders 0–100%** por classe. Botões **Resetar valores** e **Salvar**.

- Persistir em `allocation_targets` (uma linha por classe) + `investment_profile.perfil`.
- **Validação (trava em 100%):** o **donut central mostra "Total: X%"**. **Salvar** (e **Aportar**) só são
  permitidos com **soma = 100%**. Se **> 100%**: alerta no centro **"O valor ultrapassou {X−100}% do valor das
  metas"** com o anel em cor de alerta (âmbar→vermelho) e o excedente "transbordando" o anel; se **< 100%**:
  **"Faltam {100−X}% para 100%"** (tom suave). Visual sugerido: número grande "Total: X%" no centro, anel
  preenchendo até 100% e um arco de alerta para o excedente, com micro-animação ao cruzar 100%; botão `Salvar`
  desabilitado fora de 100%.
- **Presets** (valores a confirmar §16): ex.: Conservador (RF alta), Moderado (equilíbrio), Arrojado (ações/cripto altas).

## 9. Aba **Perguntas** (`/investimentos/perguntas`)

**UI:** "Perguntas — Adicione perguntas que deverão ser feitas quando você adicionar um ativo." Botões
**Restaurar padrões**, **Usar modelo**, busca; **toggle "Tipo de diagrama"** (Diagrama do cerrado / Investimentos
imobiliários); tabela **Critério · Pergunta · Ação (Editar)**; botão **Adicionar pergunta**.

- CRUD em `asset_questions` por `diagram_type`. Cada pergunta: `criterio`, `pergunta`, `peso` (default 1),
  `sort_order`, `ativo`.
- **Seeds padrão** (do print):
  - *Ações (cerrado):* ROE>8%? · CAGR receitas/lucro >5% em 5 anos? · histórico de dividendos? · investe em
    P&D? (setor obsoleto = sempre não) · >30 anos de mercado?
  - *Imobiliário/FII:* é líder no setor? · setor com >100 anos? · boa governança? (corrupção = sempre não) ·
    livre de controle estatal/cliente único? · Dív.Líq/EBITDA < 3 em 5 anos?
- Adicionar/editar/remover reflete no **score** de todos os ativos daquele diagrama (recalcular nota).

## 10. Aba **Aportar** (`/investimentos/aportar`) — rebalanceamento "Método Burro"

**UI:** "Novo Aporte — Quanto você vai investir?" input do valor + **Calcular**; donut "Distribuição do
Investimento / Patrimônio total"; tabela **"Sugestões de investimento"**: Tipo, Ticker, **Atual ($)**, **Preço
atual ($)**, **Nota**, **Total após aporte (%)**, **Sugest. de aporte ($)**, **Sugest. de aporte (un)**,
**Aportar!** (botão por linha); botão **"Aportar tudo"**. O botão por linha abre **modal de confirmação**
(Ativo, Unidades em carteira, Quantidade a ser aportada [editável], "Quantidade sugerida: N, equivale a R$ X",
**Aportar**).

### 10.1 Algoritmo (✅ confirmado pelos exemplos do usuário — PDF "metodo burro")
**Nota do ativo:** com N perguntas (peso 1), a nota **começa em −N e soma +2 a cada "Sim"** →
`nota = positivas − negativas`. Ex. (6 ações int., 10 perguntas): ACNB 1✔→ −8; BSVN 4✔→ −2; MET 6✔→ +2;
OSBC 8✔→ +6; WTBA 10✔→ +10.

**Elegibilidade:** só entram no aporte os ativos com **nota > 0** (negativos/zero ficam de fora — confirmado:
ACNB/BMI/BSVN nunca aparecem nas sugestões). Entre os positivos, a **nota também ordena** e pondera o %.

**Passos:**
1. `PL_atual = Σ(quantity × preço_atual)` (+ valores informados de RF); `PL_alvo = PL_atual + aporte`.
2. **Alvo por classe:** `alvo_classe = PL_alvo × target_pct(classe)` (Metas, §8).
3. **Alvo por ativo** (dentro da classe, só notas > 0): `peso = nota / Σ(notas>0 da classe)`;
   `alvo_ativo = alvo_classe × peso`.
4. **Déficit:** `deficit_ativo = max(0, alvo_ativo − valor_atual_ativo)`.
5. **Distribuição do aporte ∝ déficit:** `aporte_ativo = aporte × deficit_ativo / Σ(deficit)`.
   - `Σ(deficit) ≥ aporte` (comum): distribui proporcional ao déficit.
   - `Σ(deficit) < aporte` (aporte cobre todos os alvos): preenche os déficits e rateia o **excedente**
     proporcional ao **peso-alvo** dos ativos elegíveis.
6. **Unidades respeitando o preço da cota** (não dá para quebrar exatamente por valor quando as cotas têm
   preços diferentes):
   - **Internacional / cripto (fracionável):** `un = aporte_ativo / preço` (fração permitida) — o valor ideal
     é atingível direto. Confirmado no print: un 18.0985 / 3.8214 / 0.5042 / 5.9136 / 8.6577.
   - **B3 — ações nacionais e FIIs (cota inteira):** comprar **lotes inteiros** via **alocação gulosa que
     respeita preço e o caixa do aporte**:
     a. calcule alvo/déficit (passos 1–5);
     b. **enquanto sobrar caixa:** compre **+1 cota** do ativo elegível **mais abaixo do alvo** (maior
        `alvo−atual` recalculado a cada compra) **cuja cota caiba no caixa** (`preço ≤ caixa_restante`);
        **pule** ativos cuja cota seja mais cara que o caixa;
     c. pare quando **nenhuma cota elegível couber**; o restante é **troco** (informado, soma ao próximo aporte).
   - **Regra-chave (você apontou):** **nunca sugerir uma cota de valor maior que o caixa disponível** para o
     aporte. Ex.: aporte **R$ 100** com WTBA a R$ 128 → WTBA recebe **0**; o sistema sugere as **cotas mais
     baratas** que ainda fecham a meta (ou informa que nada coube → vira troco).
   - Em ambos os casos `sugest_rs = un × preço` (realizado, que pode ser **menor** que o `aporte_ativo` ideal
     pelo arredondamento de cota). Ao longo de **vários aportes**, a carteira **converge** para as metas.
7. **Saída por ativo:** `atual_rs`, `preco_atual`, `nota`, `sugest_rs`, `sugest_un`, `total_apos_aporte_pct`.
   **Implementar `total_apos_aporte_pct = (valor_atual + sugest_rs) / PL_alvo`** (peso final do ativo; soma
   100%). Obs.: na ferramenta de referência essa coluna apareceu proporcional à nota mas com denominador ~73%
   (ex.: ACNB 19,47% em vez de 26,67%) — provável inconsistência do tool de origem; o deon-fin usa a versão
   correta que fecha 100%.

> **Verificação 1 (sem carteira prévia, classe 100% internacional):** notas 2/6/10 → déficit = alvo =
> aporte×{2,6,10}/18. Aporte 1000 → R$ 111,05 / 333,15 / 555,26 (≈2:6:10) ✔; aporte 10.000 →
> R$ 1.111,11 / 3.333,33 / 5.555,56 ✔.
>
> **Verificação 2 (com carteira prévia, 5 ativos com nota > 0, classe 100% int.) — fixture oficial:** notas
> ACNB 8 / BMI 4 / MET 2 / OSBC 6 / WTBA 10 (Σ=30). Atual: ACNB 0 / BMI 0 / MET 1.111,10 / OSBC 3.333,34 /
> WTBA 5.555,56 (PL=10.000). Aporte 10.000 → PL-alvo 20.000. Alvo = 20.000×nota/30; déficit = alvo − atual
> (Σdéficit = 10.000 = aporte). Sugestão = R$ **5.333,33 / 2.666,67 / 222,24 / 666,66 / 1.111,11** (un =
> sugest/preço). ✔ Confere com o print. Mostra a hierarquia **categoria → nota dentro da categoria**.
>
> Com Metas multi-classe + carteira (ex.: aporte 25.000, Int 56% + FII 44%), o déficit por classe redistribui e
> FIIs de nota igual (6) recebem fatias ~iguais ✔.

**Intenção (do PDF):** se a Renda Fixa ou os FIIs sobem **acima** do alvo, o método **direciona os próximos
aportes para as classes/ativos abaixo do alvo** (ex.: ações) — sempre rebalanceando, **sem vender**.

**Confirmação:** por ativo (modal, qtd editável) ou "Aportar tudo" → **apenas aumenta a `quantity`** da posição
(decisão: **não** lança transação em Transações/Orçamento). Salva `ultimo_aporte`.

> A **fórmula exata de peso por nota** (proporcional? por faixas? nota mínima? como tratar classe sem ativo com
> nota>0?) e a **regra de distribuição** (guloso × proporcional) são o ponto que o usuário ofereceu exemplificar.
> **Confirmar antes de implementar o cálculo** (§16). A UI e o resto independem disso.

## 11. Aba **Mapa** (`/investimentos/mapa`) — ✅ definido

Tela **de referência** (read-only) para avaliar **qualidade/segurança por país** — "saber os índices e as notas
por país", **nada além disso**. Não entra no cálculo do aporte; serve de apoio para escolher ativos das classes
internacionais (Ações Int., REITs, RF Internacional).

**UI (dos prints):**
- Título "Mapa — Verifique abaixo a saúde financeira de cada País." + busca "Buscar por país ou índice…".
- **Mapa-múndi Leaflet** (tiles OpenStreetMap/CARTO) — **choropleth**: cada país colorido pelo **tier de rating
  soberano** (ex.: verde = alta qualidade, azul = máxima/forte, laranja = médio risco, vermelho = especulativo,
  cinza = sem dado). Clique no país (ou busca) seleciona.
- **Painel lateral** do país selecionado: nome + **selo de risco** (ex.: "AAA (Máxima Qualidade)", "AA (Alta
  Qualidade)", "BBB (Média Capacidade)", "BB (Médio Risco)", "B (Altamente Especulativo)") e **3 abas**:
  - **Índices:** Principal Índice (ex.: S&P 500, Ibovespa, DAX, Nifty 50, MOEX), Nome internacional, e
    **Classificações de Risco** das agências **S&P / Moody's / Fitch** (ex.: EUA AA+/Aaa/AAA; Brasil BB/Ba2/BB-;
    Rússia CCC-/Caa1/B; Índia BBB-/Baa3/BBB-; Alemanha AAA/Aaa/AAA).
  - **Empresas:** lista de empresas notáveis (nome, ticker, setor) — ex.: Apple/AAPL/Tecnologia, Microsoft/MSFT,
    Nvidia/NVDA, Amazon/AMZN.
  - **ETFs:** lista de ETFs (ticker + rótulo) — ex.: SPY, IVV, VOO ("ETF Americano").

**Dados (simples — "nada demais"):** dataset de referência **seedado** (ex.: `data/country_ratings.json`):
`{ country_code, name, name_intl, main_index, ratings:{sp,moody,fitch}, tier_label, tier_color, empresas:[{name,ticker,setor}], etfs:[{ticker,label}] }`. Ratings de soberano mudam **raramente** → atualização
manual (ou rotina futura). **Sem cálculo**; é leitura.

**API:** `GET /api/investimentos/mapa` → lista de países (code, tier, color) p/ pintar o choropleth;
`GET /api/investimentos/mapa/{country_code}` → detalhe (índice, ratings, empresas, ETFs). (Ou um único payload
se o dataset for pequeno.)

**Frontend:** nova dep **`leaflet` + `react-leaflet`** + um GeoJSON de fronteiras dos países; camada de cor por
`tier_color`; busca por país/índice; painel com as 3 abas. Sem `MoneyText`/Ocultar (não há valores do usuário).

**Fora de escopo:** preços/variação em tempo real no mapa, séries históricas, integração com a carteira do
usuário — é só referência de qualidade/segurança soberana.

## 12. API (consolidado sob `/api/investimentos/*`)
Envelope de erro e convenções de F0.1; repositórios em `src/web/repositories/portfolio_*`.
- `GET /api/investimentos/ativos` → `{ ativos:[{id,classe,ticker,name,quantity,preco_atual,valor_atual,nota,pct_classe,pct_carteira,ultima_atualizacao,source}], total, por_classe:[{classe,total,pct}] }`.
- `POST /api/investimentos/ativos` `{ classe, ticker, quantity }` (ou `valor` p/ RF) · `PATCH /…/{id}` · `DELETE /…/{id}`.
- `GET /api/investimentos/ticker-search?q=&classe=` → autocomplete.
- `GET /api/investimentos/metas` · `PUT /api/investimentos/metas` `{ targets:{classe:pct}, perfil }`.
- `GET /api/investimentos/perguntas?diagram_type=` · `POST` · `PATCH /{id}` · `DELETE /{id}` · `POST /restaurar-padroes`.
- `PUT /api/investimentos/ativos/{id}/respostas` `{ [question_id]: bool }` (atualiza score).
- `POST /api/investimentos/aportar/calcular` `{ aporte }` → sugestões (§10) · `POST /api/investimentos/aportar/confirmar` `{ compras:[{asset_id, quantidade}] }`.
- `GET /api/investimentos/cotacoes?tickers=` (interno; com cache).

## 13. Frontend
- Seção `web/app/(app)/investimentos/(ativos|metas|aportar|perguntas|mapa)/page.tsx` com sub-nav própria
  (tabs). Componentes em `web/components/investimentos/*`; hooks `web/hooks/useInvestimentos.ts`; libs de
  formatação/algoritmo em `web/lib/investimentos.ts`; testes `web/tests/investimentos.test.ts`.
- Reuso: `SectionCard`, `DataTable`, `Pill`, donut Recharts, `MoneyText`/Ocultar, modais. Item de menu novo
  **"Investimentos"** (ícone gráfico/pizza).

## 14. Regras / edge cases
- Soma das metas ≠ 100% → Aportar bloqueado/avisado. Classe com meta > 0 mas **sem ativo de nota > 0** → aporte
  daquela classe fica retido/realocado (definir §16).
- Ativo sem preço (cotação falhou) → marcar "preço indisponível", excluir do cálculo até atualizar.
- Renda Fixa sem ticker → valor informado entra no PL e nas metas, mas não recebe sugestão por unidade.
- Nota negativa/zero → não recebe aporte (e % menor), conforme o texto do print.
- Aporte menor que o preço de 1 unidade do ativo mais deficitário → sugerir o próximo elegível / informar troco.
- Pluggy e manual para o mesmo ticker → dedup por `(classe,ticker)`; preferir somar quantidades ou manter
  separado (definir §16).
- Cotações: rate limit/erro do provider → usar cache + "última atualização"; nunca travar a tela.

## 15. Plano de implementação (fatias)
- **F4.1 — Ativos & dados de mercado:** migrations (`portfolio_assets`), provider de cotações + autocomplete,
  aba Ativos (lista/donut/filtro/CRUD/adicionar), merge Pluggy (se §16 confirmar). Testes de repo + cálculo de %.
- **F4.2 — Metas de alocação:** `allocation_targets`+`investment_profile`, aba Metas (sliders/perfis/validação 100%).
- **F4.3 — Perguntas & score:** `asset_questions`/`asset_answers`, aba Perguntas (CRUD/seeds/diagram_type),
  cálculo de nota, toggles no editar ativo.
- **F4.4 — Aportar (rebalanceamento):** algoritmo (após §16), aba Aportar (sugestões/modal/aportar tudo),
  confirmação grava quantidades.
- **F4.5 — Mapa:** após definição (§16).
Cada fatia segue TDD (pytest no backend, Vitest no front) e os contratos de §12.

## 16. Decisões em aberto (preciso confirmar com você)
**Resolvidas (2026-06-21/22):**
1. ✅ **Cotações:** **brapi.dev** (B3 ações/FIIs + cripto) como primário; internacionais via **Yahoo/Finnhub**.
   Você fornece a chave (`BRAPI_TOKEN`, fica no servidor).
2. ✅ **Fórmula do "Método Burro":** confirmada pelos exemplos (§10.1) — nota = positivas−negativas (começa em
   −N, +2 por "Sim"); só notas > 0; aporte distribuído **∝ déficit** (sem carteira vira ∝ nota); unidades
   inteiras na B3 e fracionárias em internacional/cripto; sem venda.
3. ✅ **Pluggy investimentos:** confirmado que o Pluggy retorna investimentos (`GET /investments?itemId=`). v1
   já **ingere** as posições (novos métodos no cliente + `portfolio_assets`/`portfolio_transactions`, §6).
7a. ✅ **Aporte → app:** aporte confirmado **só atualiza a posição** (não lança transação).
9. ✅ **Banco de dados:** ver **`ADR-001-banco-de-dados.md`** (recomendação: SQLite agora c/ WAL → **Postgres**
   como alvo; MySQL viável mas não preferido).

4. ✅ **Aba "Mapa":** referência read-only (mapa-múndi por rating soberano + painel Índices/Empresas/ETFs por
   país) — detalhado em §11. Sem cálculo.

5. ✅ **Renda Fixa:** o que **não vier do Pluggy** é cadastrado **na mão por valor informado** (`manual_value`);
   esse valor **entra no PL e nas Metas** (alocação), mas **fica fora da sugestão por unidade** (sem cota).
   Atualização opcional via Marcação a Mercado (F3.6). Fonte futura p/ posições: API B3 Área do Investidor (§5).

6. ✅ **% da lista = da carteira inteira** (`valor_atual/PL`, mesmo % do donut). **Dentro da classe** quem pondera
   é a **nota** (pesos das perguntas) — §4/§7. As perguntas podem ser **≠ 10**; o peso de cada uma é aplicado
   **conforme o total** (nota normalizada −10..+10, §4).
7b. ✅ **`investido_total` do dashboard** passa a **somar** o valor da carteira — **aditivo e sem duplicar** (não
   contar de novo o que já entra como investimento via transações/`investido_total` atual; reconciliar na fonte).
8. ✅ **Metas travam em 100%:** `Salvar`/`Aportar` só com soma = 100%; donut central "Total: X%" e, se passar,
   **"O valor ultrapassou {X−100}% do valor das metas"** (anel em alerta) — §8.

✅ **Ajuste manual de cotas:** editar quantidade na mão marca `manually_adjusted` + **badge** "✏️ manual"; o
Pluggy (mais confiável) **sobrescreve no próximo sync** — §6/§7.

**Nada bloqueando a F4 — todas as decisões fechadas.**
