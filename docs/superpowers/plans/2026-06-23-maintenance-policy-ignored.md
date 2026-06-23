# Maintenance Policy Ignored Classification Sprint

**Data:** 2026-06-23

**Objetivo:** separar, na Manutencao, os lancamentos que nao entram nas filas acionaveis de classificacao porque sao ignorados por politica.

**Escopo entregue:**

- Backend: `classification_health` ganhou:
  - `ignored_tag_policy_count`;
  - `ignored_bucket_policy_count`;
  - `ignored_tag_policy`;
  - `ignored_bucket_policy`.
- Backend: cada item ignorado traz `reason` e `reason_label`.
- Motivos cobertos inicialmente:
  - `internal_transfer` -> Transferencia interna;
  - `card_payment` -> Pagamento de fatura;
  - `investment` -> Investimento/aporte;
  - `income` -> Receita/entrada;
  - `financial_cost` -> Custo financeiro sem pote;
  - `blocked_bucket` -> Categoria sem pote por politica;
  - `non_spending` -> Movimento sem consumo.
- Frontend: `ClassificationHealthPanel` ganhou a secao "Ignorados por politica" com contagem e exemplos separados para Sem Tag e Sem Meta.
- Documentacao: README, `docs/STATUS.md`, `docs/specs/README.md` e este plano atualizados.

**Testes adicionados/alterados:**

- `tests/test_web_app.py::test_maintenance_endpoint_reports_classification_health`
  - cobre transferencia interna, pagamento de fatura e custo financeiro sem pote.
- `web/tests/maintenance.test.ts`
  - cobre renderizacao da secao "Ignorados por politica".

**Proxima sprint sugerida executada:**

- Auditoria persistida de classificacao:
  - registrar aplicacoes em massa;
  - registrar edicoes/remocoes de regras aprendidas;
  - exibir ultimas execucoes na tela Manutencao.
- Plano/registro: `docs/superpowers/plans/2026-06-23-maintenance-classification-audit.md`.
