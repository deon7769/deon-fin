# Deon Fin - Status do projeto

Atualizado em: 2026-06-23

## Estado atual

- Branch principal: `main`.
- Deploy de produção na VPS: `/opt/projetos/financas-agent`.
- Container de produção: `financas-agent`.
- Último deploy funcional validado: `ff91082 feat: add maintenance classification health`.
- Banco atual: SQLite em volume persistente, com backup automático antes do deploy por `scripts/vps_deploy.sh`.
- Frontend novo: Next estático servido pela FastAPI, same-origin, com legado mantido em `/legacy`.

## O que foi entregue

### Fundação e deploy

- Runner de migrations idempotentes em `src/storage/migrations.py`.
- CI/CD da `main` com testes de backend, frontend e build Docker.
- Script de deploy VPS com backup do banco, testes, build da imagem, recriação do container e smoke de `/api/health` e `/`.
- Deploy same-origin: FastAPI serve `/api`, app Next exportado e `/legacy`.

### Nova UI

- Shell Next com layout escuro, sidebar, rotas principais e estado global de mês/ano.
- Ocultar valores sensíveis no frontend.
- Telas entregues no novo layout:
  - Painel.
  - Transações.
  - Orçamento.
  - Metas.
  - Contas.
  - Faturas.
  - Tags.
  - Perfil.
  - Manutenção.
  - Simulações.
  - Simulador redirecionado para Simulações.
  - Investimentos e subrotas.

### Domínio financeiro

- Helpers de sinal financeiro para separar receita, gasto, cartão e transferências.
- Competência financeira (`reference_month`) com recálculo por dia inicial do mês.
- Metas financeiras por 6 potes (`budget_buckets`) com previsto percentual/valor.
- Tags por transação, filtros e edição.
- Regras de Meta por transações similares (`bucket_rules`).
- Regras de Tag por transações similares (`tag_rules`).
- Proteção de classificações manuais por `bucket_source='manual'` e `tag_source='manual'`.
- Correção para exclusão de Tag limpar também `transactions.tag_source`.

### Classificação automática

- `apply_buckets_to_database(db)` aplica Meta por regra aprendida ou mapa de categoria.
- `apply_tags_to_database(db)` aplica Tag por:
  1. regra aprendida;
  2. de/para `categorias_pt`;
  3. fallback conservador por comerciante.
- Tags granulares criadas/reusadas a partir do de/para de Manutenção:
  - Ex.: `Food Delivery` -> `Delivery`.
  - Ex.: `Taxi and ride-hailing` -> `Táxi/App`.
  - Ex.: `Digital services` -> `Serviços digitais`.
- Tags granulares recebem Meta pai quando há regra no mapa categoria -> pote.
- `transactions.category` permanece como dado bruto da integração para auditoria.
- `python -m src.cli categorize` reaplica categoria, Meta, Tag e competência em dados já existentes.

### Manutenção

- Editor de dados fixos:
  - receitas;
  - caixa/reserva;
  - provisões;
  - metas;
  - wishlist;
  - imóveis;
  - tradução de categorias;
  - regras de recorrência.
- Políticas de totais do sistema:
  - incluir/excluir contas do saldo;
  - incluir/excluir contas dos movimentos;
  - incluir/excluir tipos de movimento dos totais.
- Auditoria de traduções:
  - `/api/maintenance.category_audit`;
  - tela mostra categorias vistas sem tradução.
- Saúde da classificação:
  - `/api/maintenance.classification_health`;
  - cobertura de Tags e Metas;
  - contagem por origem `manual`, `rule`, `auto`, `none`;
  - filas acionáveis de lançamentos sem Tag e sem Meta;
  - transferências/pagamentos intencionalmente fora da classificação não entram nas filas acionáveis.

### Contas e cartões

- Fallbacks para banco/cartão sem nome a partir de instituição, código bancário, bandeira/final e metadados Pluggy.
- Preservação de transações ao remover uma conexão.
- Sync por conta/conexão e abertura do Pluggy Connect/Hub.
- Saldos e dados de cartão normalizados em `account_balances`.

### Faturas

- Faturas derivadas de transações de cartão.
- Seleção/reordenação visual de cartões.
- Itens com categoria traduzida, Meta e Tag.
- Resumo por categoria preservado para visão agregada de gastos.

### Orçamento e renda

- Orçamento por mês e potes.
- Receita por transações com fallback de perfil/configuração.
- Ajuste de transferências:
  - PIX entre contas próprias não infla renda;
  - créditos vindos de contas externas podem contar como renda/movimentação.
- Correção de pagamentos de fatura importados como `Shopping`:
  - `PAGAMENTO ON LINE` negativo em cartão não reduz gasto de Meta;
  - movimento é tratado como pagamento de fatura nos totais;
  - `Pagamento de fatura` fica bloqueado para Meta/Tag automática por categoria.

### Investimentos

- Ingestão Pluggy de ativos e transações de investimentos.
- CRUD/manual adjustments de ativos.
- Cotações/cache.
- Alocação por classe.
- Perfis/metas de alocação.
- Perguntas e nota normalizada.
- Fluxo Aportar.
- Mapa de risco soberano por país.
- Correção específica para `AUVP11` como ETF.

## Documentos principais

- Arquitetura e specs: `docs/specs/README.md`.
- Deploy VPS: `docs/ops/vps-deploy.md`.
- Fundação VPS: `docs/superpowers/specs/2026-06-19-vps-foundation-design.md`.
- Classificação assistida Tag/Meta: `docs/superpowers/specs/2026-06-22-assisted-tag-meta-classification-design.md`.
- Tags granulares por de/para: `docs/superpowers/specs/2026-06-23-category-translated-tags-design.md`.
- Saúde da classificação: `docs/superpowers/plans/2026-06-23-maintenance-classification-health.md`.

## Pendências conhecidas

### Classificação e Manutenção

- Adicionar ações no painel de saúde para:
  - abrir Transações já filtrada por "sem Tag";
  - abrir Transações já filtrada por "sem Meta";
  - aplicar Tag/Meta em massa com revisão;
  - reprocessar classificação a partir da UI.
- Melhorar o fluxo "aplicar/sugerir para similares" no frontend:
  - deixar claro quantos registros foram afetados;
  - atualizar a lista sem recarregar a página inteira;
  - revisar casos em que o usuário percebeu que a classificação não propagou.
- Expandir o de/para de categorias com foco nas categorias ainda sem tradução.
- Criar fluxo de sugestão para categorias vistas sem tradução:
  - propor tradução;
  - propor Tag;
  - propor Meta pai.
- Criar revisão de regras aprendidas:
  - listar `bucket_rules`;
  - listar `tag_rules`;
  - permitir remover/editar regra incorreta.
- Separar claramente nas filas:
  - "sem Tag acionável";
  - "sem Meta acionável";
  - "ignorado por política" (transferências, fatura, impostos financeiros quando aplicável).

### Categorias, Tags e resumos

- Preservar resumos por categoria nas telas atuais, mas evoluir gradualmente para também mostrar resumos por Tag e por Meta.
- Decidir se Tags padrão amplas antigas (`Alimentação`, `Lazer`, etc.) continuam como opções manuais ou se serão migradas para Tags granulares.
- Melhorar cores de Tags criadas automaticamente pelo de/para.
- Adicionar filtros por `tag_source` e `bucket_source` em Transações.

### Renda e transferências

- Revisar casos reais como recebimentos da Koopere que não aparecem como entrada do mês atual.
- Validar a lógica de renda com:
  - transferências próprias;
  - PIX externo;
  - proventos/dividendos;
  - estornos;
  - cashback;
  - aportes/investimentos.
- Documentar uma matriz de decisão para `income_value` e `spending_value`.

### Contas, cartões e Pluggy

- Verificar se ainda existe banco ou cartão sem nome na produção.
- Melhorar diagnóstico por item Pluggy:
  - última sincronização;
  - status;
  - contas vinculadas;
  - erros recentes.
- Avaliar persistência de ordenação/reordenação de cartões se a preferência precisar sobreviver entre sessões.

### Faturas

- Evoluir datas de fechamento/vencimento quando a integração fornecer dados reais.
- Melhorar edição inline de Meta/Tag nos itens de fatura.
- Verificar traduções e Tags em todos os agrupamentos de fatura.

### Investimentos

- Aprofundar leitura dos JSONs de investimentos do BTG/Pluggy.
- Mapear todos os campos recebidos:
  - ativos;
  - posição;
  - quantidade;
  - preço;
  - classe/subtipo;
  - movimentações;
  - proventos.
- Evoluir a reconciliação entre ativos Pluggy e ativos manuais.
- Melhorar o fluxo de confirmação de aporte e atualização de posição.

### Produto e UX

- Melhorar responsividade em telas densas, especialmente Manutenção, Transações, Orçamento e Faturas.
- Fazer revisão visual mobile/tablet das tabelas largas.
- Continuar removendo dependências do legado quando houver paridade total.
- Avaliar se `/legacy` deve permanecer indefinidamente ou virar fallback temporário.

### Dados e arquitetura

- Planejar migração futura de SQLite para PostgreSQL quando multiusuário/escala exigir.
- Revisar retenção e rotação de backups.
- Adicionar jobs/rotinas observáveis para sync e reclassificação.
- Criar endpoint/admin seguro para reprocessar classificação sem precisar de SSH.

## Próximas sprints recomendadas

1. **Manutenção - ações de classificação**
   - Botões para abrir filas no contexto de Transações.
   - Ação "reprocessar classificação".
   - Aplicação em massa de Tag/Meta com prévia.

2. **Transações - filtros de qualidade**
   - Filtros `sem Tag`, `sem Meta`, `tag_source`, `bucket_source`.
   - Destaques para itens acionáveis vindos da Manutenção.

3. **Regras aprendidas**
   - Tela ou seção em Manutenção para revisar `tag_rules` e `bucket_rules`.
   - Remoção/edição segura de regras ruins.

4. **Renda e transferências**
   - Suite de testes com casos reais de PIX próprio, PIX externo, Koopere, dividendos, estorno e cashback.
   - Ajustes nos cálculos do mês atual.

5. **Investimentos BTG/Pluggy**
   - Documentar amostras reais de JSON.
   - Completar ingestão/reconciliação dos campos que ainda não aparecem na UI.

## Comandos operacionais úteis

```bash
python -m src.cli categorize
```

Reaplica categorização, Meta, Tag e competência no banco atual.

```bash
./scripts/vps_deploy.sh
```

Executa backup, testes, build Docker, recria o container e faz smoke de saúde/frontend na VPS.

```bash
python -m pytest
```

Roda a suite Python.

```bash
cd web && npm test && npm run build
```

Roda testes e build do frontend.
