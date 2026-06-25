# Deon Fin

Deon Fin e uma aplicacao local-first para organizar financas pessoais e familiares.
Ela combina ingestao de dados financeiros, classificacao operacional, paineis de
acompanhamento e ferramentas de planejamento em uma interface web unica.

O projeto nasceu como um agente Python de importacao e analise financeira e evoluiu
para uma aplicacao completa com backend FastAPI, banco SQLite e frontend Next.js.

## Principais recursos

- Conexao via Pluggy / Open Finance Brasil para contas, cartoes e investimentos.
- Importacao manual de OFX, CSV Nubank e CSV generico.
- Painel financeiro com saldos, renda, gastos, metas e indicadores por periodo.
- Gestao de transacoes com filtros avancados, tags, metas e ajustes manuais.
- Orcamento por categorias de meta, incluindo acompanhamento planejado x realizado.
- Faturas de cartao com ordenacao, parcelas, filtros e revisao por competencia.
- Carteira de investimentos com ativos, metas, perguntas, mapa e aportes.
- Manutencao operacional para revisar classificacoes, regras aprendidas e filas de qualidade.
- Simuladores financeiros para juros compostos, independencia financeira e amortizacao.
- Analise por IA opcional, usando provedores configuraveis ou Ollama local.

## Stack

Backend:

- Python 3.12
- FastAPI
- SQLite
- Typer CLI
- Pluggy API
- pytest

Frontend:

- Next.js
- React
- TypeScript
- Tailwind CSS
- Vitest

Infra:

- Docker multi-stage build
- Docker Compose
- GitHub Actions para testes e build

## Privacidade e seguranca

Este projeto lida com dados financeiros reais. Antes de usar ou publicar uma
instancia propria:

- Nunca versione `.env`, bancos SQLite, backups, OFX, CSVs reais ou capturas com dados pessoais.
- Use credenciais Pluggy proprias e mantenha `PLUGGY_CLIENT_SECRET` fora do Git.
- Defina `APP_PASSWORD` forte se a aplicacao ficar acessivel fora da maquina local.
- Revise `docker-compose.yml` antes de publicar um deploy, pois dominios, redes e labels de proxy variam por ambiente.
- Considere remover ou anonimizar fixtures, screenshots e documentos que possam conter dados reais.

Arquivos ignorados pelo Git incluem `.env`, `data/`, bancos `*.db`, logs e pastas de ambiente virtual.

Este software e uma ferramenta de organizacao e estudo. Ele nao substitui
consultoria financeira, contabil, tributaria ou juridica.

## Requisitos

- Python 3.12+
- Node.js 20.9+
- npm
- Credenciais Pluggy para sincronizacao Open Finance

Docker e Docker Compose sao opcionais para execucao conteinerizada.

## Configuracao local

Crie o ambiente Python:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Crie o arquivo de ambiente:

```powershell
copy .env.example .env
```

Preencha ao menos:

```env
PLUGGY_CLIENT_ID=...
PLUGGY_CLIENT_SECRET=...
PLUGGY_USE_SANDBOX=true
DATABASE_URL=sqlite:///data/financas.db
```

Para analise por IA, configure um provedor opcional no `.env`, como
`OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `ZAI_API_KEY`,
`OPENAI_API_KEY` ou use Ollama local.

## Rodando a aplicacao

Backend FastAPI:

```powershell
.venv\Scripts\python -m src.cli serve --host 127.0.0.1 --port 8000
```

Frontend Next.js em modo desenvolvimento:

```powershell
cd web
npm install
npm run dev
```

Por padrao, o frontend de desenvolvimento usa `NEXT_PUBLIC_API_URL` para falar
com a API. Veja `web/.env.example`.

URLs locais comuns:

- API e build estatico servido pelo FastAPI: `http://127.0.0.1:8000`
- Next dev server: `http://127.0.0.1:3000`
- Health check: `http://127.0.0.1:8000/api/health`

## Pluggy Connect

Com o backend rodando, a tela de Contas abre o Pluggy Connect para criar ou
atualizar conexoes bancarias. Apos uma conexao bem sucedida, o item Pluggy e
registrado localmente e a sincronizacao e agendada em background.

Fluxo resumido:

1. Abra a aplicacao web.
2. Acesse Contas.
3. Clique em Nova conta.
4. Autentique no widget oficial da Pluggy.
5. Aguarde a sincronizacao inicial.

O botao Atualizar credenciais reabre o Hub Pluggy para o mesmo item conectado.

## CLI

Algumas rotinas podem ser executadas pelo terminal:

```powershell
# Listar conectores Pluggy
.venv\Scripts\python -m src.cli connectors

# Sincronizar um item Pluggy existente
.venv\Scripts\python -m src.cli sync <ITEM_ID> --days 90

# Importar arquivos manuais
.venv\Scripts\python -m src.cli import-ofx caminho\extrato.ofx
.venv\Scripts\python -m src.cli import-nubank caminho\fatura.csv --kind credit
.venv\Scripts\python -m src.cli import-nubank caminho\extrato.csv --kind debit

# Aplicar classificacoes automaticas
.venv\Scripts\python -m src.cli categorize

# Gerar relatorio simples por periodo
.venv\Scripts\python -m src.cli report --days 30

# Rodar analise por IA, se configurada
.venv\Scripts\python -m src.cli analyze --kind all
```

## Testes e qualidade

Backend:

```powershell
.venv\Scripts\python -m pytest -q
```

Frontend:

```powershell
npm.cmd --prefix web test -- --run
npm.cmd --prefix web run typecheck
npm.cmd --prefix web run lint
npm.cmd --prefix web run build
```

Validacao de setup:

```powershell
.venv\Scripts\python scripts\validate_setup.py
```

Essa validacao depende de credenciais Pluggy configuradas e executa checagens
end-to-end do ambiente local.

## Docker

Build da imagem:

```powershell
docker build -t deon-fin:local .
```

Execucao basica:

```powershell
docker run --rm -p 8000:8000 --env-file .env -v ${PWD}\data:/app/data deon-fin:local
```

O Dockerfile compila o frontend Next.js e copia o export estatico para o backend.
Em producao, o FastAPI serve a UI em `/` e a API em `/api`.

O `docker-compose.yml` do repositorio e um ponto de partida para deploy. Ajuste
rede, labels, dominio e proxy reverso conforme o seu ambiente antes de usar.

## Estrutura do repositorio

```text
src/
  agent/              Regras, contexto financeiro e analise por IA
  importers/          OFX, CSV e sincronizacao Pluggy
  pluggy/             Cliente HTTP da Pluggy
  storage/            SQLite, migracoes e persistencia
  web/                FastAPI, rotas, repositorios e UI legada
  cli.py              CLI principal

web/
  app/                Rotas da interface Next.js
  components/         Componentes de UI
  hooks/              Hooks de dados e mutacoes
  lib/                Tipos, API client e utilitarios
  tests/              Testes Vitest

tests/                Testes Python
docs/specs/           Especificacoes funcionais e ADRs
scripts/              Validacao, deploy e utilitarios
```

## Documentacao funcional

As especificacoes ficam em `docs/specs/`. Elas descrevem as fases de evolucao da
aplicacao, incluindo painel, transacoes, orcamento, faturas, contas, metas,
manutencao, simuladores e investimentos.

## Licenca

Defina uma licenca antes de aceitar contribuicoes externas ou reutilizacao por
terceiros. Enquanto nao houver um arquivo `LICENSE`, todos os direitos permanecem
reservados ao autor do repositorio.
