# ADR-001 — Banco de dados: SQLite (agora) → PostgreSQL (alvo); por que não MySQL

**Status:** Proposto · **Data:** 2026-06-22 · **Decisores:** Davi (owner) + revisão de engenharia
**Contexto-gatilho:** entrada do módulo de **Carteira de Investimentos (F4)** + a pergunta "às vezes um MySQL
roda bem se otimizado, ou Postgres direto?".

---

## Contexto

Hoje o deon-fin usa **SQLite** (`DATABASE_URL=sqlite:///data/financas.db`, `src/config.py`/`src/storage/db.py`),
em **um único container** Docker (`financas-agent`) atrás do Traefik na VPS, uso **pessoal/familiar**
(1–poucos usuários). Características relevantes já no código:

- `Database` abre uma conexão por request (`check_same_thread=False`) e o **auto-sync do Pluggy roda numa thread
  paralela** que também escreve (`_sync_all_items`). Ou seja, **há escrita concorrente** (sync + edição manual).
- A camada **`src/web/repositories/*` isola o SQL** — os routers não falam SQL cru. Isso torna uma eventual
  troca de banco **localizada**.
- O `metadata_json` (contas, transações, e agora investimentos do Pluggy) é guardado como **JSON em texto**.
- O `vps_deploy.sh` faz **backup do arquivo** `data/financas.db` antes de cada deploy.
- O README já previa "**Migração SQLite → Supabase Postgres**" como próximo passo.

O F4 adiciona: `portfolio_assets`, `portfolio_transactions`, e um **cache de cotações** (escrito a cada
atualização de preço — potencialmente frequente), aumentando a pressão de escrita concorrente.

**Volume:** pequeno (milhares de transações, dezenas de ativos). **Gargalo real não é volume, é concorrência de
escrita** (sync + cache de cotações + edição) e o caminho para **multiusuário/observabilidade** no futuro.

## Decisão

1. **Curto prazo — manter SQLite, mas endurecido:** ativar **WAL + `busy_timeout`** e **serializar escritas**
   (ver §Consequências). Resolve o risco de `database is locked` (R3 da revisão de arquitetura) a custo ~zero e
   sem nova infra. Suficiente para uso pessoal/familiar e para entregar a F4.
2. **Alvo — PostgreSQL** (self-hosted na VPS **ou** Supabase), adotado quando **um gatilho** ocorrer (§Quando
   migrar). Mantemos o **repositório como única fronteira de SQL** e tornamos o `Database`/migrations
   **dialect-aware** para que a migração seja incremental.
3. **Não adotar MySQL/MariaDB.** Funciona, mas **não traz vantagem** neste app e **diverge do roadmap**
   (Supabase/Postgres). Postgres é melhor encaixe técnico (abaixo).

## Opções consideradas

### Opção A — SQLite endurecido (recomendado **agora**)
| Dimensão | Avaliação |
|---|---|
| Complexidade | **Baixa** (já em uso) |
| Custo/infra | **Zero** (arquivo no volume) |
| Concorrência | Limitada: WAL = N leitores + **1 escritor**; exige serializar escritas |
| Escala/multiusuário | Fraca (sem acesso em rede; 1 processo) |
| Backup | Trivial (cópia de arquivo — já no `vps_deploy.sh`) |

**Prós:** nada novo para operar; rápido para dados pequenos; backup/restore simples; mantém o foco no produto.
**Contras:** escrita concorrente limitada; não evolui para multiusuário; tipos frouxos; JSON só como texto.

### Opção B — PostgreSQL (recomendado como **alvo**)
| Dimensão | Avaliação |
|---|---|
| Complexidade | Média (1 container `postgres` no compose **ou** Supabase gerenciado) |
| Custo/infra | Baixo (container) / plano Supabase |
| Concorrência | **Forte** (MVCC: muitos leitores e escritores sem lock global) |
| Escala/multiusuário | **Boa**; caminho natural p/ Supabase (auth/realtime/REST) |
| Backup | `pg_dump`/PITR (muda o `vps_deploy.sh`) |

**Prós:** **JSONB** (ideal para os `metadata_json`/payloads Pluggy, com índices GIN); **índices parciais e por
expressão** (ex.: ativos com `nota>0`, por `reference_month`, por `status='ACTIVE'`); funções de janela para
analytics da carteira; alinha com o roadmap (Supabase); concorrência real elimina o lock do SQLite.
**Contras:** mais uma peça para operar; backup/observabilidade mudam; **overkill para 1 usuário hoje**.

### Opção C — MySQL/MariaDB ("otimizado")
| Dimensão | Avaliação |
|---|---|
| Complexidade | Média (container + tuning) |
| Concorrência | Boa (InnoDB) |
| Ergonomia p/ este app | **Inferior ao Postgres** |

**Prós:** robusto, amplamente hospedado, boa performance com schema/índices bem feitos.
**Contras:** **JSON menos ergonômico** que o JSONB do Postgres (sem índice GIN equivalente direto); **sem índices
parciais**; **diverge do roadmap** (que já aponta Supabase/Postgres) — adotá-lo criaria um segundo padrão sem
ganho. "Otimizar para o formato" daria trabalho e entregaria menos do que o Postgres entrega por padrão neste
caso de uso (muito JSON semiestruturado + analytics).

## Trade-off / racional

O gargalo deste app não é throughput, é **(1) concorrência de escrita** (sync + cotações + edição) e **(2) o
caminho para multiusuário/Supabase**. Para (1), WAL no SQLite já resolve agora. Para (2) e para o uso intensivo
de **JSON semiestruturado** (payloads Pluggy) + **analytics de carteira**, o **Postgres** é estritamente melhor
que o MySQL (JSONB + GIN + índices parciais + janela) e está alinhado ao roadmap. Logo: **SQLite agora,
Postgres como alvo, MySQL fora**.

## Quando migrar para Postgres (gatilhos)
Migrar quando **qualquer** um ocorrer: (a) expor além da família/multiusuário; (b) contenção de lock mesmo com
WAL (ex.: cache de cotações muito frequente competindo com o sync); (c) querer recursos do **Supabase**
(auth/realtime/REST/backup gerenciado); (d) analytics da carteira/relatórios crescerem além do confortável no
SQLite.

## Consequências

**Agora (SQLite endurecido):**
- No `Database.__init__` (após o `executescript(SCHEMA)`): `PRAGMA journal_mode=WAL;`,
  `PRAGMA busy_timeout=5000;`, `PRAGMA synchronous=NORMAL;`, `PRAGMA foreign_keys=ON;`.
- **Serializar escritas**: usar um único writer (ex.: `threading.Lock` de escrita já existente no auto-sync +
  transações curtas) para evitar `SQLITE_BUSY` entre sync e requests.
- Backup do `vps_deploy.sh` permanece (cópia do arquivo + WAL/`-wal`/`-shm`).

**Para o alvo (Postgres), preparar sem migrar ainda:**
- Manter **todo SQL nos repositórios** (`src/web/repositories/*`) — nenhuma query crua em routers/agent.
- Tornar `DATABASE_URL` o ponto único de configuração (já é) e o runner de migrations **dialect-aware**
  (ou adotar **Alembic** ao mover para PG). Usar SQL portátil; isolar o que for específico (ex.: `JSONB`,
  `ON CONFLICT`) atrás do repositório.
- Ao migrar: subir `postgres` no `docker-compose` (ou Supabase), `metadata_json`→**`JSONB`**, criar índices
  (GIN no JSONB; parciais p/ `status='ACTIVE'`, `nota>0`, por `reference_month`), e rodar um **script único de
  cópia** SQLite→Postgres. Trocar o backup para `pg_dump`.

## Action items
1. [ ] **Agora:** aplicar os `PRAGMA` (WAL/busy_timeout/synchronous/foreign_keys) no `Database.__init__` + teste
   de concorrência (sync + escrita) — fecha o R3 da revisão de arquitetura.
2. [ ] **Agora:** garantir que F4 (e demais features) não escrevam SQL fora dos repositórios (lint/checagem).
3. [ ] **Preparar:** runner de migrations dialect-aware (ou plano Alembic) e SQL portátil nas novas tabelas do F4.
4. [ ] **Quando um gatilho ocorrer:** subir Postgres (compose/Supabase), migrar `metadata_json`→JSONB + índices,
   script de cópia, ajustar `vps_deploy.sh` (pg_dump) e `DATABASE_URL`.
