# Gestão Financeira — MVP

Agente Python para ingestão e análise de movimentações financeiras pessoais.

Suporta:
- **Pluggy** (Open Finance BR) — ingestão automática de contas, cartões e investimentos
- **OFX** — importação manual (extratos baixados do banco)
- **CSV Nubank** — fatura de cartão e extrato de conta
- **CSV genérico** — qualquer banco, basta mapear colunas

## Estado atual do projeto

Status em **2026-06-21**:

- Backend FastAPI + SQLite + Pluggy segue como núcleo operacional.
- Frontend novo em Next.js vive em `web/` e já cobre Painel, Orçamento, Metas, Simulador, Contas, Faturas, Transações, Tags, Perfil, Manutenção com editor e FAQ.
- As specs F0.1 até F3.3 foram implementadas, testadas e publicadas na `main`.
- A VPS está em `/opt/projetos/financas-agent`, serviço Docker Compose `financas-agent`, atualizada pelo fluxo seguro de backup, pytest, build Docker e smoke.
- Em desenvolvimento local, a API roda em `http://127.0.0.1:8000` e o Next em `http://127.0.0.1:3000`.
- A partir da F3.1, a imagem Docker embute o build estático do Next: `/` serve a nova UI, `/api` segue na FastAPI e o legado fica em `/legacy` com rollback via `LEGACY_UI=1`.
- O workflow `.github/workflows/ci-cd.yml` roda pytest, testes/build do frontend e build Docker. O deploy automático para a VPS já existe e executa `scripts/vps_deploy.sh` quando os secrets SSH estiverem configurados.

## Setup rápido

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # preencha PLUGGY_CLIENT_ID / PLUGGY_CLIENT_SECRET
```

## Validar tudo (procedimento de checagem)

```powershell
.venv\Scripts\python scripts\validate_setup.py
```

Esse script roda em ordem:
1. Valida `.env`
2. Autentica no Pluggy
3. Lista conectores sandbox + produção
4. Gera connect_token (necessário pra UI web)
5. Roda `pytest` (unit + integração)
6. Importa OFX e CSVs de fixture
7. Aplica categorização automática
8. Imprime relatório

Saída esperada: `Tudo certo — projeto validado.`

## Conectar um banco real (UI web)

```powershell
.venv\Scripts\python -m src.cli serve
```

Abre `http://127.0.0.1:8000`. Lá você:
1. Clica em **Abrir Pluggy Connect** → modal abre, você escolhe o banco e loga
2. O `itemId` é salvo localmente e a sincronização das transações roda em background
3. A tela mostra a lista de contas conectadas e o resumo dos últimos 30 dias por categoria
4. Botões por linha: **Sync** (re-puxa), **Atualizar credenciais** (re-abre widget pra mesma conexão), **Remover**

A página usa o widget oficial do Pluggy carregado do CDN.

## Comandos da CLI

```powershell
# Ver conectores Pluggy
.venv\Scripts\python -m src.cli connectors

# Sincronizar uma conexão Pluggy (item) existente
.venv\Scripts\python -m src.cli sync <ITEM_ID> --days 90

# Importação manual
.venv\Scripts\python -m src.cli import-ofx caminho\extrato.ofx
.venv\Scripts\python -m src.cli import-nubank fatura.csv --kind credit
.venv\Scripts\python -m src.cli import-nubank extrato.csv --kind debit

# Aplicar categorização automática
.venv\Scripts\python -m src.cli categorize

# Relatório dos últimos 30 dias
.venv\Scripts\python -m src.cli report --days 30

# UI web (Pluggy Connect Widget)
.venv\Scripts\python -m src.cli serve --host 127.0.0.1 --port 8000
```

## Estrutura

```
src/
  config.py           # carrega .env
  pluggy/client.py    # cliente HTTP Pluggy (httpx)
  storage/db.py       # SQLite + dedup por fingerprint
  importers/
    ofx.py            # OFX (ofxparse)
    csv_generic.py    # CSV configurável
    csv_nubank.py     # presets Nubank
    pluggy_sync.py    # ingestão de item Pluggy
  agent/
    categorizer.py    # regras (regex) por categoria
  cli.py              # Typer CLI

tests/
  fixtures/           # OFX e CSV de exemplo
  test_storage.py
  test_categorizer.py
  test_importers.py
  test_pluggy_integration.py  # marcado @integration

scripts/
  validate_setup.py   # procedimento de validação end-to-end
```

## Próximos passos planejados

Ordem atual das próximas sprints:

1. **Pluggy Connect no Next:** migrar o fluxo de conexão bancária do front legado para o frontend novo.
2. **Melhorias de categorização/manutenção:** completar traduções, sugerir tipos de gasto automaticamente e reduzir edição manual repetitiva.
3. **Fixes de conexões:** investigar fallback de nome para banco/cartão sem nome.
4. **Consolidação técnica:** sunset gradual do legado, unificação de cálculos financeiros, WAL/busy timeout no SQLite e migração futura para Supabase/Postgres se necessário.
5. **Inteligência financeira:** recorrências automáticas, projeção de fluxo 30/60/90 dias e categorização ML como fallback das regras.

Notas de fixes observados em 2026-06-21:

- **Manutenção / traduções:** ainda faltam várias traduções e de/para de categorias que existiam no fluxo antigo; a próxima versão deve preservar o que já funcionava e facilitar complemento.
- **Categorias automatizadas:** evoluir a classificação dos tipos de gastos de forma mais automática, usando regras/recorrências e revisão manual só para exceções.
- **Conexões bancárias:** investigar por que há um banco e um cartão sem nome no novo layout; provavelmente falta fallback/normalização de metadados Pluggy.
- **Resumos por categoria:** manter os agregados por categoria como visão importante para entender gastos consolidados.

## Segurança

- `.env` está no `.gitignore`. Nunca commite credenciais.

