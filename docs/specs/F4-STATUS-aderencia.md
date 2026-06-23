# F4 — Status de implementação & aderência (módulo Investimentos)

> Revisão de **aderência** entre os specs `F4.*` e o código já entregue (commits até
> `feat: add slider allocation editor for goals`). Documento de **status**, não de implementação.
> Data: 2026-06-22.

## Veredito

🟢 **O módulo de investimentos (F4.1–F4.5) está implementado e ADERENTE aos specs**, inclusive às decisões que
foram fechadas depois (nota normalizada, afordabilidade do aporte, badge manual, % da carteira, banco). Restam
apenas **follow-ups menores** (§3) e a feature nova **F2.8 (conciliação)** que ainda não existe.

## 1. Implementado (evidências no código)

| Spec | Evidência | Aderência |
|---|---|---|
| **F4.1 Ativos** | `m0015` (`manually_adjusted, manual_adjusted_at, price_source, price_updated_at`, `quote_cache`); `agent/portfolio/quotes.py` (`search_ticker`, `get_quotes`, `refresh_prices`); `portfolio_repo.create_manual_asset/update_asset/delete_asset/set_price`; router `/investments`, `/ticker-search`, `POST/PATCH/DELETE /assets`, `/refresh-quotes`; front `investimentos/page.tsx` + `InvestmentAssetModal`; `settings.brapi_token/quotes_provider/quotes_ttl_min` | ✅ |
| **F4.2 Metas (alocação)** | `m0016` (`allocation_targets`, `investment_profile`); router `GET/PUT /investments/targets`, `GET /investments/profiles`; front `investimentos/metas` + `InvestmentTargetsPanel` | ✅ |
| **F4.3 Perguntas/score** | `m0017` (`asset_questions`/`asset_answers` + seeds); `score_repo.compute_nota` = `(positivos−negativos)/peso_total×10` (**normalizada −10..+10**); router questions CRUD + `restore-defaults` + answers GET/PUT; front `investimentos/perguntas` + `InvestmentQuestionsPanel` | ✅ |
| **F4.4 Aportar (Método Burro)** | `agent/portfolio/aporte.py::calcular_aporte`: elegível só `nota>0` e `target>0`; alvo por classe × peso(nota); déficit; distribuição ∝ déficit (com excedente ∝ peso-alvo); **fracionário** direto e **lote inteiro guloso respeitando o caixa** (pula cota mais cara que o caixa); `total_apos_aporte_pct=(atual+sugest)/PL_alvo`; router `/aporte/calcular` e `/aporte/confirmar`; front `investimentos/aportar` + `InvestmentAportePanel` | ✅ (inclui a afordabilidade pedida) |
| **F4.5 Mapa** | `agent/portfolio/country_ratings.py`; router `/investments/map` e `/map/{code}`; front `investimentos/mapa` + `InvestmentMapPanel` + `LeafletCountryMap` | ✅ |
| **Extra entregue** | `m0018` (classe `etf`), `m0019` (`account_total_settings`/`movement_total_settings` — base p/ somar carteira sem duplicar, decisão §7b), `m0020` (`tag_rules`) | ✅ |

**Decisões tardias confirmadas no código:** nota normalizada por quantidade de perguntas ✅; aporte respeita
preço de cota/afordabilidade ✅; `manually_adjusted` + fontes de preço ✅; `% na carteira` ✅; brapi como provider ✅.

## 2. Pendências reais (novas — em docs próprios)
- **F2.8 — Conciliação transações ↔ metas de poupança** (não existe `transactions.savings_goal_id`). Spec:
  `F2.8-metas-conciliacao-transacoes.md`. **Próxima feature a executar.**
- **F5 — Hardening/consolidação** (WAL, app.py, etc.). Doc: `F5-hardening-consolidacao.md`.

## 3. Follow-ups menores do F4 (status atualizado em 2026-06-23)
Itens de polish a **conferir** contra os specs (podem já estar ok; checar e, se faltar, implementar):
1. ✅ **Metas (F4.2) — trava 100% + overflow:** confirmado que `PUT /investments/targets` **rejeita soma ≠ 100**
   (422 `targets_sum`) e que o front mostra **"Total: X%"** + **"O valor ultrapassou {X−100}% do valor das metas"**
   (>100%) / "Faltam {100−X}%" (<100%), com `Salvar` desabilitado fora de 100% (overview §8 / F4.2 §4).
2. ✅ **Renda Fixa:** cadastro por **valor informado** (`manual_value`) já existia; em 2026-06-23 o fluxo
   **Aportar** passou a sugerir RF sem preço por valor em R$ (`sugest_un == sugest_rs`) e confirmar esse valor
   atualiza `manual_value/current_value`.
3. ✅ **Aporte — classes sem score (rf/cripto/etf):** confirmado/ajustado: classes sem score recebem peso neutro
   quando têm meta; RF sem unidade distribui por valor; cripto/ETF continuam dependendo de preço/cota.
4. ✅ **Badge "manual" na lista** (front) e regra "Pluggy sobrescreve no próximo sync" no `upsert_pluggy_asset`
   (overview §6 / F4.1 §5) — confirmar UI + comportamento do sync.
5. ✅ **Mapa — dataset/UX:** dataset estático cobre US, BR, DE, IN, RU e principais já seedados; o payload leve
   de `/api/investments/map` agora inclui `name_intl`, `main_index` e `tier_label`, permitindo busca por país ou
   índice sem pré-carregar o detalhe de todos os países. Legenda visual cobre as 5 faixas do spec: AAA, AA/A,
   BBB/BB, B/CCC e Sem dados.
6. ✅ **`investido_total` aditivo sem duplicar:** o contexto/dashboard legado agora usa
   `portfolio_assets.current_value` como `investido_total` quando há carteira detalhada; os aportes detectados em
   transações ficam separados em `aportes_periodo_total` e continuam alimentando o 50/30/20 como fluxo mensal.
7. ✅ **Tema azul:** confirmado que o acento azul do módulo está aplicado em todas as abas (Ativos/Metas/Aportar/
   Perguntas/Mapa) e botões.

> Recomendação: rodar a suíte (`pytest -q`, `npm test`/`typecheck`/`lint`/`build`) e fazer um *smoke* de cada
> aba; transformar qualquer item acima que **falhar** em uma tarefa pontual. Os 7 itens acima são verificação,
> não reescrita.
