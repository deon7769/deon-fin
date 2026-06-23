# Maintenance Transaction Quality Filters Sprint

**Data:** 2026-06-23

**Objetivo:** ligar a saude da classificacao em Manutencao ao fluxo operacional de Transacoes, permitindo abrir filas acionaveis de gastos reais sem Tag ou sem Meta.

**Escopo entregue:**

- Backend: `/api/transactions` aceita `quality=missing_tag` e `quality=missing_bucket`.
- Repositorio: os filtros de qualidade usam `spending_value`, respeitam politicas de transferencia/pagamento de fatura e aplicam o bloqueio de categorias sem pote para a fila sem Meta.
- Frontend: `useTransactionFilters`, serializacao de query, badges e seletor de qualidade foram atualizados.
- Manutencao: o painel "Saude da classificacao" ganhou links para abrir as filas em `/transacoes`, preservando o mes selecionado.

**Testes adicionados:**

- `tests/test_transactions_repo.py::test_list_transactions_quality_filters_only_actionable_classification_rows`
- `tests/test_transactions_api.py::test_get_transactions_quality_filter_returns_actionable_missing_tag_rows`
- `web/tests/transactions.test.ts` cobre serializacao e rotulos dos filtros.
- `web/tests/maintenance.test.ts` cobre os links "Abrir fila sem Tag" e "Abrir fila sem Meta".

**Fora do escopo / proximas sprints:**

- Reprocessar classificacao pela UI.
- Aplicar Tag/Meta em massa com pre-visualizacao.
- Filtrar Transacoes por `tag_source` e `bucket_source` foi entregue na sprint `2026-06-23-transacoes-filtros-origem-classificacao.md`.
- Mostrar grupo separado de itens ignorados por politica.
