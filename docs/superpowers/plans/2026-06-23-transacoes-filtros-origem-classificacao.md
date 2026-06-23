# Transacoes Classification Source Filters Sprint

**Data:** 2026-06-23

**Objetivo:** permitir revisar transacoes pela origem da classificacao de Meta e Tag, separando registros manuais, por regra, automaticos e sem origem.

**Escopo entregue:**

- Backend: `/api/transactions` aceita `bucket_source` e `tag_source` como listas separadas por virgula.
- Backend: valores aceitos sao `manual`, `rule`, `auto` e `none`; valor invalido retorna 422.
- Repositorio: os filtros entram no mesmo `WHERE` usado pela listagem e pelo resumo, entao totais acompanham a visao filtrada.
- Frontend: `transactionQuery`, parse da URL, badges e `hasTransactionFilters` conhecem `bucket_source` e `tag_source`.
- UI: drawer de filtros avancados ganhou "Origem da Meta" e "Origem da Tag" com multiselect nativo.

**Testes adicionados:**

- `tests/test_transactions_repo.py::test_list_transactions_filters_bucket_and_tag_sources`
- `tests/test_transactions_api.py::test_get_transactions_filters_classification_sources`
- `tests/test_transactions_api.py::test_get_transactions_shape_and_bad_params` cobre origem invalida.
- `web/tests/transactions.test.ts` cobre serializacao, parse e badges.
- `web/tests/transaction-advanced-filters.test.ts` cobre os novos campos do drawer.

**Proximas sprints sugeridas:**

- Reprocessar classificacao pela UI em Manutencao, com feedback de quantos registros mudaram.
- Aplicacao em massa de Meta/Tag com previa antes de salvar.
- Revisao e edicao de `bucket_rules` e `tag_rules`.
- Multiselect customizado com busca para Tags, Contas e origem caso a lista real fique longa demais.
