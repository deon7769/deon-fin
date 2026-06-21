# Revisão de Arquitetura & Saúde do Código — deon-fin

**Data:** 2026-06-21 · **Avaliador:** Codex · **Repo:** `deon7769/deon-fin`
**Escopo:** estado atual do projeto na `main`, na VPS e no backlog de próximas sprints.

---

## Veredito

🟢 **Saudável e avançando bem.** A nova UI saiu da fase de preview e já cobre o núcleo do produto:
Painel, Orçamento, Metas, Contas, Faturas, Transações, Tags, Perfil e FAQ. O backend continua com a
arquitetura esperada pelos specs: FastAPI com routers finos, repositórios por domínio, SQLite com migrations
idempotentes e módulos de domínio em `src/agent`. O CI/CD está versionado, o deploy seguro da VPS foi
executado e o container de produção foi recriado no commit mais recente entregue.

O próximo bloco de risco não é funcional, e sim operacional: **servir o Next same-origin em produção** sem
quebrar `/api`, Basic Auth, Traefik, Tailscale, backup do SQLite e o front legado durante a transição.

---

## 1. Estado observado

- **Branch ativa:** `main`, migrada para ser o fluxo principal de desenvolvimento.
- **HEAD entregue/deployado:** `860ab57 feat: add F2.6 metas screen`.
- **VPS:** `/opt/projetos/financas-agent`, serviço Docker Compose `financas-agent`, imagem recriada após
  backup do banco e pytest remoto (`222 passed, 4 skipped`).
- **CI/CD:** `.github/workflows/ci-cd.yml` roda pytest, Vitest, typecheck, lint, build Next e build Docker.
  O deploy automático existe e fica condicionado aos secrets SSH da VPS.
- **Working tree local:** documentação em atualização para refletir o novo estado e preparar a sprint F3.1.

### Specs → implementação

| Spec | Entregáveis principais | Status |
|---|---|---|
| F0.1 API + migrations | migrations, reference month, error envelope, routers/repos base, sign helpers | ✅ entregue |
| F0.2 Scaffold front | Next App Router, shell, design system, Tailwind, Vitest/TS/lint | ✅ entregue |
| F0.3 Estado global | período, ocultar valores, tema | ✅ entregue |
| F1.1 6 potes | buckets, regras, autoaplicação no sync | ✅ entregue |
| F1.2 Tags | tags repo/router, seletor e página | ✅ entregue |
| F2.1 Painel | KPIs, gráficos e resumo por período | ✅ entregue |
| F2.2 Transações | lista, filtros, edição inline | ✅ entregue |
| F2.3 Orçamento | renda, gastos, potes, não categorizadas | ✅ entregue |
| F2.4 Faturas | faturas por cartão/mês derivadas das transações | ✅ entregue |
| F2.5 Contas | bancos, cartões, saldos, sync e remoção preservando histórico | ✅ entregue |
| F2.6 Metas | previsto por pote e metas de poupança (`savings_goals`) | ✅ entregue |
| F2.7 Perfil | renda, e-mail/nome e início de mês | ✅ entregue |
| F3.1 Deploy same-origin | Next estático servido pela FastAPI em `/`, API em `/api`, legado em `/legacy` | ⏭ próxima |
| F3.2 Manutenção | nova tela para `/api/maintenance` | 📝 planejada |
| F3.3 Simulador | nova tela para `/api/simular` e `/api/amortizacao` | 📝 planejada |

---

## 2. Arquitetura atual

### Backend

```text
HTTP /api  ->  src/web/routers/*          entrada HTTP e validação
              src/web/repositories/*     consultas e persistência por domínio
              src/storage/*              SQLite, migrations e competência
domínio    ->  src/agent/*                cálculo financeiro, potes, cartões, simulação, manutenção
ingestão   ->  src/importers/* + Pluggy   OFX, CSV, Nubank e sync Open Finance
```

- A camada nova está bem separada: routers seguem finos e os repositórios concentram SQL.
- Endpoints legados seguem preservados para operação e rollback: `/`, `/api/dashboard`, `/api/cartao`,
  `/api/maintenance`, `/api/simular`, `/api/amortizacao`, `/api/analyze`.
- O pipeline de sync já aplica categorização, potes e competência antes das novas telas lerem os dados.

### Frontend

- `web/` usa Next.js App Router, React Query, Recharts, Tailwind e componentes locais reutilizáveis.
- O layout novo já cobre as telas principais; Manutenção e Simulador ainda não entraram no menu principal.
- Em dev, o Next roda em `:3000` consumindo a API em `:8000`. Em produção, F3.1 deve trocar esse modelo para
  same-origin: frontend estático em `/` e API em `/api`.

### Operação

- `scripts/vps_deploy.sh` já faz backup do SQLite, pytest, build Docker, `up -d` e smoke de `/api/health`.
- O workflow GitHub Actions repete a bateria local e tem job SSH para rodar o mesmo script na VPS quando os
  secrets forem configurados.
- A última implantação manual confirmou saúde dos principais endpoints: `/api/health`, `/api/buckets/plan`,
  `/api/savings-goals`, `/api/budget`, `/api/accounts` e `/api/maintenance`.

---

## 3. Riscos & dívida técnica

| # | Item | Severidade | Detalhe |
|---|---|---|---|
| R1 | `src/web/app.py` ainda concentra legado + wiring | Média | O arquivo mistura factory, rotas legadas, auto-sync e helpers antigos. F3.1 vai tocar nele; depois disso vale extrair `routers/legacy.py`. |
| R2 | Lógica financeira duplicada entre legado e novo | Média-Alta | As telas novas usam repos/helpers, mas endpoints antigos ainda calculam parte dos números. Risco de divergência enquanto o legado existir. |
| R3 | SQLite com auto-sync concorrente | Média | Ainda vale ativar WAL + `busy_timeout` para reduzir risco de `database is locked` durante sync e edição manual. |
| R4 | Dois fronts durante a transição | Média | F3.1 precisa deixar rollback simples (`LEGACY_UI=1` ou `/legacy`) e impedir que `/api/*` caia no fallback SPA. |
| R5 | Export estático do Next 16 | Média | Validar `output: 'export'`, rotas profundas, assets `/_next/*` e build Docker antes de subir para produção. |
| R6 | `@app.on_event("startup")` legado | Baixa | Migrar para lifespan depois que F3.1 estabilizar. |
| R7 | Manutenção/Simulador fora do novo layout | Baixa-Média | Funcionalidade existe nos endpoints, mas ainda sem experiência visual alinhada ao app novo. |

---

## 4. Recomendações priorizadas

**P1 — próxima sprint**

- Implementar F3.1 com TDD: testes de roteamento SPA, `/api` preservado, `/static` preservado, `/legacy` e
  toggle `LEGACY_UI`.
- Ajustar `web/lib/api.ts` para default `/api` em produção e documentar `.env.local` para dev.
- Tornar o Dockerfile multi-stage, copiando `web/out` para `web_dist`.
- Estender `scripts/vps_deploy.sh` com smoke do frontend em `/`.

**P2 — logo após F3.1**

- Especificar e implementar F3.2 Manutenção no layout novo, consumindo `/api/maintenance`.
- Especificar e implementar F3.3 Simulador, consumindo `/api/simular` e `/api/amortizacao`.
- Migrar Pluggy Connect do front legado para o Next para reduzir dependência da página antiga.

**P3 — consolidação**

- Extrair rotas legadas de `app.py` e documentar o sunset do legado.
- Centralizar cálculos financeiros em uma fonte única usada por legado e novo.
- Ativar WAL + `busy_timeout` no SQLite.
- Migrar `startup` para lifespan quando a superfície de deploy estiver estabilizada.

---

## 5. Conclusão

O projeto está em bom estado para entrar na fase F3. A prioridade agora é fechar a operação de produção da
nova UI: **Next same-origin, smoke de frontend, rollback claro e CI/CD sem intervenção manual**. Depois disso,
Manutenção e Simulador entram naturalmente como telas novas sobre endpoints já existentes.
