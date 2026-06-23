# Maintenance Classification Audit Sprint

**Data:** 2026-06-23

**Objetivo:** registrar e exibir, na Manutencao, o historico recente das acoes que alteram classificacao assistida.

**Escopo entregue:**

- Migration `m0022_classification_audit_log`:
  - tabela `classification_audit_log`;
  - indice `idx_classification_audit_created`.
- Repositorio `classification_audit_repo`:
  - `record(...)` grava a acao;
  - `list_recent(...)` lista eventos recentes com `metadata` parseado.
- API:
  - `POST /api/maintenance/classification/bulk-apply` registra `bulk_apply`;
  - `PATCH /api/maintenance/classification/rules` registra `rule_update` e `rule_delete`;
  - `GET /api/maintenance/classification/audit` retorna o historico recente.
- Frontend:
  - hook `useMaintenanceClassificationAudit`;
  - painel `ClassificationAuditPanel`;
  - tela `/manutencao` exibe a auditoria logo apos regras aprendidas.
- Eventos registrados:
  - tipo da acao;
  - `kind` (`tag` ou `bucket`);
  - destino e nome do destino;
  - `match_key` para regras;
  - quantidade afetada e total da previa;
  - metadados como `month` e `not_found`.

**Testes adicionados/alterados:**

- `tests/test_migrations.py`
  - cobre schema e indice de `classification_audit_log`;
  - atualiza a expectativa de migrations para 22.
- `tests/test_maintenance_actions_api.py::test_maintenance_classification_audit_tracks_bulk_apply_and_rule_changes`
  - cobre `bulk_apply`, `rule_update`, `rule_delete` e ordem recente do endpoint de auditoria.
- `web/tests/maintenance.test.ts`
  - cobre renderizacao do painel "Auditoria de classificacao".

**Proximas validacoes:**

- Validar com dados reais em producao se a auditoria ajuda a explicar as aplicacoes em massa.
- Confirmar se o fluxo de "aplicar/sugerir para similares" cria `tag_rules`/`bucket_rules` nos cenarios esperados.
- Evoluir auditoria para execucoes automaticas de reprocessamento se for util para diagnostico.
