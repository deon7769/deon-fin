# Deon Fin - Status do projeto

Atualizado em: 2026-06-23

## Estado atual

- Branch principal: `main`.
- Deploy de produção na VPS: `/opt/projetos/financas-agent`.
- Container de produção: `financas-agent`.
- Último deploy funcional validado: 2026-06-23, após a sprint de filtros acionáveis de classificação.
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
- Metas passou a usar editor visual de alocação por sliders:
  - visão em anel com total alocado;
  - sliders por pote com valor estimado em R$;
  - salvamento em lote bloqueado até fechar 100%.
- Metas de poupança agora conciliam transações reais:
  - `transactions.savings_goal_id` vincula uma transação a no máximo uma meta;
  - Guardado efetivo usa `saved_total = saved_manual + saved_from_tx`;
  - transações ocultas não contam no total vinculado;
  - `/metas` tem modal de conciliação com vinculadas/candidatas e ações em lote;
  - `/transacoes` tem coluna inline e filtro por Meta poupança.

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
- Tags criadas automaticamente recebem cor determinística e `seed_tags` faz backfill de cores ausentes sem sobrescrever cores editadas.
- Custos financeiros reais sem Meta, como `Tax on financial operations` -> `IOF`, agora recebem Tag automática sem forçar vínculo a um pote.
- Fallback conservador por lojista cobre padrões óbvios sem categoria Pluggy, como Apple billing, Ifood/IFD, Uber, GNV/posto, Netflix/Spotify, OpenAI/OpenRouter/Microsoft.
- `transactions.category` permanece como dado bruto da integração para auditoria.
- `python -m src.cli categorize` reaplica categoria, Meta, Tag e competência em dados já existentes.
- Validação em produção após reclassificação:
  - `49` Tags cadastradas;
  - `0` Tags sem cor;
  - gastos reais sem Tag no histórico: `83` -> `35`;
  - gastos reais sem Tag em `2026-06`: `6` -> `4`.

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
  - a fila "sem Tag" usa gasto real via `spending_value`, evitando pagamento de fatura, transferências e movimentações que não são consumo;
  - a fila "sem Meta" também usa gasto real, mas continua respeitando categorias bloqueadas para pote;
  - botões abrem Transações já filtrada por `quality=missing_tag` ou `quality=missing_bucket`.

### Transações

- Painel "Filtros e Busca" com busca rápida e drawer "Mais filtros" inspirado nos prints:
  - período por data exata;
  - mês de referência;
  - faixa de valor;
  - tipo Receita/Despesa;
  - Metas/potes, incluindo "Sem meta";
  - Tags, incluindo "Sem tag";
  - Contas;
  - Ocultar dos relatórios;
  - transferências de mesma titularidade/internas.
- Filtros acionáveis de qualidade da classificação:
  - `quality=missing_tag` lista gastos reais sem Tag, excluindo transferências e pagamentos de fatura;
  - `quality=missing_bucket` lista gastos reais sem Meta, excluindo transferências, pagamentos de fatura e categorias bloqueadas para pote;
  - badges indicam "Sem Tag acionável" ou "Sem Meta acionável" quando o filtro vem da Manutenção.
- Filtro `internal_transfer=only|exclude` para revisar ou remover da visão as transferências internas detectadas por par conectado ou titularidade.

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
- Correção de transferência própria com categoria incorreta:
  - débito bancário para titular conectado por nome não entra como gasto;
  - caso real coberto: `Transferência enviada|DAVI DE OLIVEIRA NETO...` vindo como `Education`.

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
- Aporte em Renda Fixa sem preço unitário:
  - RF cadastrada por `manual_value` entra no PL e nas Metas;
  - o fluxo Aportar sugere valor em R$ (`sugest_un == sugest_rs`);
  - a confirmação soma o valor em `manual_value/current_value`.
- KPI `investido_total` sem duplicar:
  - quando há carteira detalhada, usa `portfolio_assets.current_value`;
  - aportes detectados no extrato ficam em `aportes_periodo_total`;
  - orçamento 50/30/20 continua usando os aportes do período como fluxo mensal.
- Mapa F4 refinado:
  - payload leve inclui nome internacional, índice principal e selo de risco;
  - busca por índice funciona sem pré-carregar todos os detalhes;
  - legenda mostra AAA, AA/A, BBB/BB, B/CCC e Sem dados.

## Documentos principais

- Arquitetura e specs: `docs/specs/README.md`.
- Deploy VPS: `docs/ops/vps-deploy.md`.
- Fundação VPS: `docs/superpowers/specs/2026-06-19-vps-foundation-design.md`.
- Classificação assistida Tag/Meta: `docs/superpowers/specs/2026-06-22-assisted-tag-meta-classification-design.md`.
- Tags granulares por de/para: `docs/superpowers/specs/2026-06-23-category-translated-tags-design.md`.
- Saúde da classificação: `docs/superpowers/plans/2026-06-23-maintenance-classification-health.md`.
- Conciliação de metas de poupança: `docs/specs/F2.8-metas-conciliacao-transacoes.md`.

## Pendências conhecidas

### Classificação e Manutenção

- Adicionar ações restantes no painel de saúde para:
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
  - "ignorado por política" (transferências, fatura, impostos financeiros quando aplicável).
- Persistir e auditar regras de Tag aprendidas na produção; levantamento atual indicou `tag_rules=0`, então o aprendizado visual ainda precisa ser validado ponta a ponta.

### Categorias, Tags e resumos

- Preservar resumos por categoria nas telas atuais, mas evoluir gradualmente para também mostrar resumos por Tag e por Meta.
- Decidir se Tags padrão amplas antigas (`Alimentação`, `Lazer`, etc.) continuam como opções manuais ou se serão migradas para Tags granulares.
- Revisar a paleta automática de Tags depois de validar visualmente com dados reais.
- Adicionar filtros por `tag_source` e `bucket_source` em Transações.
- Melhorar o componente visual de multiseleção de Tags/Contas caso a lista cresça muito; a primeira versão usa multiselect nativo no drawer avançado.

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

### Metas de poupança

- Melhorar sugestão de candidatas para conciliação:
  - priorizar transações de aporte, transferência externa e pote "Metas";
  - manter opção para mostrar todas as não vinculadas do período.
- Adicionar preview mais completo do total antes de salvar vínculos no modal.
- Modelar direção de resgate/subtração; a v1 soma `abs(amount)` das transações vinculadas.

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

1. **F4 follow-ups de Investimentos**
   - Revisar detalhamento dos JSONs BTG/Pluggy para proventos e movimentações.

2. **Manutenção - ações de classificação**
   - Ação "reprocessar classificação".
   - Aplicação em massa de Tag/Meta com prévia.

3. **Transações - filtros de qualidade**
   - Filtros por origem `tag_source` e `bucket_source`.
   - Destaques visuais para itens acionáveis vindos da Manutenção.

4. **Regras aprendidas**
   - Tela ou seção em Manutenção para revisar `tag_rules` e `bucket_rules`.
   - Remoção/edição segura de regras ruins.

5. **Renda e transferências**
   - Suite de testes com casos reais de PIX próprio, PIX externo, Koopere, dividendos, estorno e cashback.
   - Ajustes nos cálculos do mês atual.

6. **Investimentos BTG/Pluggy**
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
