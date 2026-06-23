# Maintenance Classification Actions Sprint

**Data:** 2026-06-23

**Objetivo:** transformar o painel "Saude da classificacao" em area operacional, permitindo reprocessar classificacao automatica e aplicar Tag/Meta em massa com previa antes de salvar.

**Escopo entregue:**

- Backend: `POST /api/maintenance/classification/reprocess` executa `apply_buckets_to_database` e `apply_tags_to_database`, retornando estatisticas de alteracoes.
- Backend: `POST /api/maintenance/classification/bulk-preview` usa a mesma fila acionavel de Transacoes (`missing_tag` ou `missing_bucket`) e retorna contagem, total absoluto e amostra dos lancamentos.
- Backend: `POST /api/maintenance/classification/bulk-apply` aplica Tag ou Meta em massa na fila filtrada, marcando origem como manual.
- Frontend: `useMaintenance` ganhou hooks para reprocessar, gerar previa e aplicar em massa, invalidando Manutencao, Transacoes, Tags, Painel e Orcamento.
- UI: `ClassificationHealthPanel` ganhou controles para reprocessar, escolher fila, selecionar Tag/Meta, gerar previa e aplicar em massa.

**Testes adicionados:**

- `tests/test_maintenance_actions_api.py::test_maintenance_reprocess_classification_runs_bucket_and_tag_classifiers`
- `tests/test_maintenance_actions_api.py::test_maintenance_bulk_preview_and_apply_updates_classification_queue`
- `tests/test_maintenance_actions_api.py::test_maintenance_bulk_preview_validates_target`
- `web/tests/maintenance.test.ts` cobre os controles de reprocessamento e previa em massa no painel.

**Proximas sprints sugeridas:**

- Revisao e edicao de `bucket_rules` e `tag_rules` pela Manutencao foi entregue em `2026-06-23-maintenance-classification-rules.md`.
- Separar itens ignorados por politica nas filas de classificacao.
- Registrar historico/auditoria das aplicacoes em massa.
- Continuar a suite de renda e transferencias com casos reais de PIX externo, Koopere, dividendos, estorno e cashback.
