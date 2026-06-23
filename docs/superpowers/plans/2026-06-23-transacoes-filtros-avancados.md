# Transacoes Advanced Filters Sprint

**Data:** 2026-06-23

**Objetivo:** aproximar a tela de Transacoes dos prints de referencia, expondo os filtros avancados que ja existiam parcial ou totalmente no backend e adicionando filtro dedicado para transferencias internas.

**Escopo entregue:**

- UI: card "Filtros e Busca" com busca sempre visivel e botao "Mais filtros".
- UI: drawer "Filtros Avancados" com periodo, mes de referencia, faixa de valor, tipo, Metas, Tags, Contas, Ocultar dos Relatorios, transferencias internas, qualidade de classificacao e metas de poupanca.
- Frontend: serializacao de `account_ids`, `min`, `max`, `bucket_ids`, `tag_ids`, `internal_transfer`, `quality` e demais filtros avancados.
- Backend: `/api/transactions` aceita `account_ids` e `internal_transfer=only|exclude`.
- Repositorio: filtro de transferencia interna detecta pares PIX entre contas conectadas e debitos de mesma titularidade quando a descricao indica o titular.

**Testes adicionados:**

- `tests/test_transactions_repo.py::test_list_transactions_filters_internal_transfer_pairs`
- `tests/test_transactions_api.py::test_get_transactions_filters_internal_transfers`
- `web/tests/transactions.test.ts` cobre serializacao e badges do drawer avancado.
- `web/tests/transaction-advanced-filters.test.ts` cobre os rotulos principais do drawer dos prints.

**Fora do escopo / proximas sprints:**

- Filtros por origem `tag_source` e `bucket_source`.
- Multiselect customizado com busca para Tags/Contas se a lista ficar longa demais.
- Bulk actions no mesmo padrao do print antigo.
