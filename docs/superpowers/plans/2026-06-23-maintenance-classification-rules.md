# Maintenance Classification Rules Sprint

**Data:** 2026-06-23

**Objetivo:** permitir revisar, corrigir e remover regras aprendidas de classificacao por Tag e Meta diretamente na Manutencao.

**Contexto:**

- `bucket_rules` guarda associacoes aprendidas de descricao normalizada para Meta/pote.
- `tag_rules` guarda associacoes aprendidas de descricao normalizada para Tag.
- A sprint anterior ja permitia reprocessar classificacao e aplicar Tag/Meta em massa com previa.
- Esta sprint fecha a governanca das regras antes de novos reprocessamentos.

**Escopo entregue:**

- Backend: `GET /api/maintenance/classification/rules` lista `tag_rules` e `bucket_rules`, incluindo destino, nome e cor.
- Backend: `PATCH /api/maintenance/classification/rules` atualiza o destino da regra ou remove a regra quando `target_id=null`.
- Backend: validacao de destino invalido para Tag/Meta com erro 422.
- Frontend: `useMaintenanceClassificationRules` e `useSaveMaintenanceClassificationRule` em `useMaintenance`.
- UI: `ClassificationRulesPanel` em `/manutencao`, com secoes de Tags e Metas, seletor de destino, salvar e remover regra.
- Documentacao: README, `docs/STATUS.md`, `docs/specs/README.md` e este plano atualizados.

**Testes adicionados:**

- `tests/test_maintenance_actions_api.py::test_maintenance_classification_rules_can_be_listed_updated_and_deleted`
- `tests/test_maintenance_actions_api.py::test_maintenance_classification_rules_validate_targets`
- `web/tests/maintenance.test.ts` cobre a renderizacao do painel de regras aprendidas.

**Proximas sprints sugeridas:**

- Separar explicitamente itens ignorados por politica nas filas de classificacao.
- Registrar historico/auditoria das aplicacoes em massa e edicoes de regras.
- Validar em producao se o fluxo "aplicar similares" esta criando `tag_rules` como esperado.
- Melhorar feedback visual quando a propagacao para similares atualiza registros fora da pagina atual.
