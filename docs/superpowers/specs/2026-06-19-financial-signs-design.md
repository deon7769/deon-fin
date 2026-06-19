# Deon Fin financial signs design

Date: 2026-06-19
Project: `/opt/projetos/financas-agent`
Repository: `deon7769/deon-fin`
Runtime host: `minha-vps`

## Context

The app already runs in production on the VPS and uses the production checkout
as the operational source of truth. The user wants improvements to happen there,
without introducing separate local development environment files for now. The
current app is personal-use software, so the VPS `.env` remains the only real
runtime configuration source.

The first product improvement should fix the financial base before any UI or
budget work. The most important inconsistency is the sign convention for credit
card transactions, especially Nubank credit card imports.

Current code already has partial agreement about the intended convention:

- `src/agent/context.py` documents that bank debits are negative, bank credits
  are positive, credit card purchases are positive, and credit card payments or
  refunds are negative.
- `src/agent/cards.py` treats positive credit card amounts as purchases.
- Existing analyst/card tests include examples where credit card purchases are
  positive and card payments do not count as spending.

The contradiction is in `src/importers/csv_nubank.py`, where Nubank credit card
CSV imports currently flip positive imported amounts into negative amounts. The
test suite protects this old behavior, so the first implementation slice should
turn that test into the new contract.

## Problem

Financial reporting is hard to trust while different modules disagree on what a
signed amount means.

The app needs one canonical rule that can answer these questions consistently:

- Is a bank account debit an expense?
- Is a credit card purchase an expense?
- Is a credit card payment an expense, an adjustment, or both?
- How should refunds reduce spending?
- Which calculations should be used by summaries, reports, and future budget
  features?

Without this, budget tables or UI work would be built on unstable totals.

## Considered approaches

### Approach A: financial signs foundation first (recommended)

Define one canonical sign convention, update the Nubank credit importer to
respect it, add focused tests for checking accounts, credit cards, refunds, and
card payments, and align summary/report calculations that currently depend on
raw signed amounts.

Trade-off: this delays budget endpoints and visible UI changes. It is the best
first slice because future budget and dashboard work will depend on these
numbers.

### Approach B: minimal Nubank importer patch

Only remove the Nubank credit card sign flip and update the old importer test.

Trade-off: this is faster, but it risks leaving API summaries or reports with
the same conceptual bug in another layer.

### Approach C: full finance domain expansion

Fix signs and implement budget tables, category percentage rules, recurring
templates, manual entries, Pluggy association, and UI improvements in one
larger sprint.

Trade-off: this would create visible progress quickly, but it mixes foundation
work with new product surfaces and makes it harder to isolate regressions.

## Design

Use Approach A for Sprint 1. This sprint fixes the financial base only. It does
not introduce budget persistence, new UI screens, or a separate environment
configuration model.

### Canonical sign convention

The app will use this convention everywhere new code or changed code touches
financial totals:

- Bank/checking account income is positive.
- Bank/checking account outflow is negative.
- Credit card purchases, including installments, are positive spending.
- Credit card refunds, reversals, and card-side payments are negative
  adjustments.
- Bank-side credit card payments are negative cash outflow but are not spending.

Monthly spending is calculated as:

- bank debit expenses converted to positive spending values, plus
- positive credit card purchase amounts, plus
- negative credit card refunds or reversals when they belong to spending
  categories, which reduces the category total, while
- excluding internal transfers, investment movements, and credit card payments.

The important invariant is that paying a card invoice must never duplicate the
original purchase as a second expense.

### Components

The implementation should stay close to the current code structure:

- `src/importers/csv_nubank.py`: stop flipping Nubank credit card purchases to
  negative amounts. Keep the importer behavior explicit with a small comment or
  function name if needed.
- `src/agent/context.py`: keep this as the main source for normalized financial
  context. If the monthly spending rules are duplicated elsewhere, extract only
  the smallest useful helper rather than adding a broad domain layer.
- `src/agent/cards.py`: preserve the current positive-purchase behavior and add
  tests only if a regression gap is found.
- `src/web/app.py` and `src/cli.py`: align summary/report calculations if they
  still infer spending by raw sign in a way that conflicts with the canonical
  rule.
- Tests: update the Nubank credit test and add a focused financial-sign test
  suite that documents the canonical examples.

### Data flow

Imported transactions should enter the database already using the canonical sign
where the importer can know the account type.

The context/reporting layer should not assume that every negative value is an
expense or that every positive value is income. It should consider account type
and category. This is especially important for credit card accounts and card
payments.

The future budget feature should consume the normalized spending totals rather
than query raw transaction signs directly.

### Data migration

Do not automatically rewrite existing SQLite production data in Sprint 1.

The current database contains real personal data and may already include mixed
historical imports. A safe correction of old rows should be a separate audit or
migration after identifying exactly which transactions were produced by the old
Nubank credit importer and which negative credit card rows are legitimate
refunds or payments.

This sprint may add diagnostics or tests, but it should not run a production
data mutation beyond normal deploy/test operations.

### Error handling

Importer changes should fail loudly only for malformed CSV structure, not for
ordinary signed values. A CSV row with an explicit negative credit card amount
should be preserved as a negative adjustment instead of being forced positive.

Summary/report code should ignore or exclude known non-spending categories such
as credit card payments and transfers rather than silently turning them into
expenses.

### Testing

Add or update tests for these cases:

- Nubank credit CSV purchase imports as a positive credit card amount.
- Bank checking debit counts as positive spending in monthly totals.
- Bank checking income does not count as spending.
- Credit card purchase counts as spending.
- Credit card refund or negative adjustment reduces or does not inflate
  spending.
- Bank-side credit card payment does not duplicate spending.
- Card-side payment, when present, does not count as a purchase.
- Existing Pluggy, OFX, generic CSV, analyst context, and cards tests still
  pass.

Verification for the implementation plan should include full `pytest`, then the
existing VPS deploy script once behavior changes are ready for production.

### Out of scope

Sprint 1 does not include monthly budget tables or endpoints, category
percentage targets, recurring template generation, manual transaction UI,
Pluggy manual association UI, production SQLite sign migration, new `.env`
files, or a dev/prod configuration split. Those should follow after the
financial base is stable.
