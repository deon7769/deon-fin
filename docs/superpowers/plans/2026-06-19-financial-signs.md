# Financial Signs Sprint 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make transaction signs consistent across Nubank credit imports, financial context, the legacy summary endpoint, and the CLI report.

**Architecture:** Keep `src/agent/context.py` as the canonical finance-domain layer by adding small sign helper functions there. Importers will persist transactions using the canonical sign convention, while web/CLI consumers use the helpers to avoid interpreting raw signs directly.

**Tech Stack:** Python 3.12, SQLite, FastAPI, Typer, pandas CSV imports, pytest.

---

## File Structure

- Modify `src/agent/context.py`: add canonical sign helpers and use them inside `build_financial_context`.
- Modify `src/importers/csv_nubank.py`: stop flipping credit card purchases to negative values.
- Modify `src/web/app.py`: calculate `/api/summary` through canonical helper functions while preserving the existing response shape.
- Modify `src/cli.py`: calculate `report` output through canonical helper functions.
- Modify `tests/test_importers.py`: replace the old Nubank credit sign expectation and add a negative-adjustment fixture test.
- Create `tests/test_financial_signs.py`: document the canonical sign contract independently from importer details.
- Modify `tests/test_web_app.py`: add a regression test for `/api/summary` with bank debit, card purchase, refund, and card payment.

Do not modify `.env`, production SQLite data, budget tables, UI layout, Pluggy credentials, or Docker/Traefik configuration in this sprint.

## Task 1: Canonical Sign Helpers And Context Contract

**Files:**
- Create: `tests/test_financial_signs.py`
- Modify: `src/agent/context.py`

- [ ] **Step 1: Write the failing financial-sign tests**

Create `tests/test_financial_signs.py` with this content:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.agent.context import build_financial_context, income_value, spending_value
from src.storage import Account, Transaction


def test_canonical_spending_and_income_values():
    assert spending_value(-80.0, "BANK", "Groceries") == 80.0
    assert spending_value(1000.0, "BANK", "Salary") == 0.0
    assert income_value(1000.0, "BANK", "Salary") == 1000.0
    assert income_value(300.0, "CREDIT", "Shopping") == 0.0

    assert spending_value(300.0, "CREDIT", "Shopping") == 300.0
    assert spending_value(-40.0, "CREDIT", "Shopping") == -40.0
    assert spending_value(-300.0, "CREDIT", "Credit card payment") == 0.0
    assert spending_value(-300.0, "BANK", "Credit card payment") == 0.0
    assert spending_value(-120.0, "BANK", "Transfers") == 0.0


def test_context_uses_bank_debits_and_card_purchases_without_duplicate_invoice(tmp_db):
    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    tmp_db.upsert_account(Account(id="card1", source="test", name="Card", type="CREDIT"))
    tmp_db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 5, 1),
            amount=Decimal("1000.00"),
            description="Salary",
            source="test",
            category="Salary",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 5, 2),
            amount=Decimal("-80.00"),
            description="Debit groceries",
            source="test",
            category="Groceries",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 5, 3),
            amount=Decimal("-300.00"),
            description="Invoice payment from bank",
            source="test",
            category="Credit card payment",
        ),
        Transaction(
            account_id="card1",
            posted_at=date(2026, 5, 4),
            amount=Decimal("300.00"),
            description="Card purchase",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=date(2026, 5, 5),
            amount=Decimal("-40.00"),
            description="Card refund",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=date(2026, 5, 6),
            amount=Decimal("-300.00"),
            description="Invoice settlement on card",
            source="test",
            category="Credit card payment",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 5, 7),
            amount=Decimal("-120.00"),
            description="Internal transfer",
            source="test",
            category="Transfers",
        ),
    ])

    ctx = build_financial_context(tmp_db, today=date(2026, 6, 19)).to_dict()

    assert ctx["fluxo_mensal"]["2026-05"]["renda"] == 1000.0
    assert ctx["fluxo_mensal"]["2026-05"]["gasto"] == 340.0
    assert ctx["pagamentos_cartao_total"] == 300.0

    categories = {row["categoria"]: row["total"] for row in ctx["gasto_por_categoria"]}
    assert categories == {"Shopping": 260.0, "Groceries": 80.0}
```

- [ ] **Step 2: Run the new tests and verify they fail for the right reason**

Run:

```bash
cd /opt/projetos/financas-agent
pytest tests/test_financial_signs.py -q
```

Expected result before implementation:

```text
ImportError: cannot import name 'income_value' from 'src.agent.context'
```

- [ ] **Step 3: Add canonical helper functions to `src/agent/context.py`**

Add these functions after `_month_key`:

```python
def _category_name(category: str | None) -> str:
    return category or "(sem categoria)"


def spending_value(amount: float, account_type: str | None, category: str | None) -> float:
    """Return positive spending impact for expenses and negative impact for refunds."""
    category_name = _category_name(category)
    if category_name in NON_SPENDING_CATEGORIES:
        return 0.0

    value = float(amount)
    if (account_type or "").upper() in CREDIT_TYPES:
        return value
    return -value if value < 0 else 0.0


def income_value(amount: float, account_type: str | None, category: str | None) -> float:
    """Return income from bank accounts only, excluding internal movements."""
    category_name = _category_name(category)
    if category_name in NON_SPENDING_CATEGORIES:
        return 0.0
    if (account_type or "").upper() in CREDIT_TYPES:
        return 0.0

    value = float(amount)
    return value if value > 0 else 0.0
```

In `build_financial_context`, replace the current spending calculation block:

```python
        is_credit = acct_type.get(r["account_id"], "") in CREDIT_TYPES

        # Valor de consumo (positivo = gastou); 0 se n?o for consumo.
        if is_credit:
            spend_val = amount          # compra positiva, estorno negativo
        else:
            spend_val = -amount if amount < 0 else 0.0
        is_spending = category not in NON_SPENDING_CATEGORIES and spend_val != 0.0
```

with this block:

```python
        account_type = acct_type.get(r["account_id"], "")
        is_credit = account_type in CREDIT_TYPES

        # Valor de consumo (positivo = gastou; negativo = estorno).
        spend_val = spending_value(amount, account_type, category)
        is_spending = spend_val != 0.0
```

Replace the current income block:

```python
        if not is_credit and amount > 0 and category not in NON_SPENDING_CATEGORIES:
            realized_months[mk]["renda"] += amount
```

with this block:

```python
        income_val = income_value(amount, account_type, category)
        if income_val:
            realized_months[mk]["renda"] += income_val
```

- [ ] **Step 4: Run focused context tests**

Run:

```bash
cd /opt/projetos/financas-agent
pytest tests/test_financial_signs.py tests/test_analyst.py tests/test_cards.py -q
```

Expected result:

```text
passed
```

- [ ] **Step 5: Commit Task 1**

Run:

```bash
cd /opt/projetos/financas-agent
git add src/agent/context.py tests/test_financial_signs.py
git commit -m "test: document canonical financial signs"
```

## Task 2: Nubank Credit Importer Uses Canonical Signs

**Files:**
- Modify: `tests/test_importers.py`
- Modify: `src/importers/csv_nubank.py`

- [ ] **Step 1: Replace the old Nubank credit sign test and add adjustment coverage**

In `tests/test_importers.py`, replace `test_import_nubank_credit_flips_signs` with these two tests:

```python
def test_import_nubank_credit_preserves_purchase_signs(tmp_db):
    r = import_nubank_csv(FIXTURES / "nubank_credit.csv", tmp_db, kind="credit")
    assert r.total_read == 5

    rows = tmp_db.list_transactions(account_id="nubank:credit-card")
    assert len(rows) == 5
    amounts = sorted(round(float(row["amount"]), 2) for row in rows)
    assert amounts == [18.3, 42.5, 55.9, 89.9, 150.0]

    accounts = {row["id"]: row for row in tmp_db.list_accounts()}
    assert accounts["nubank:credit-card"]["type"] == "CREDIT"


def test_import_nubank_credit_preserves_negative_adjustments(tmp_path, tmp_db):
    csv_path = tmp_path / "nubank_credit_adjustment.csv"
    csv_path.write_text(
        "date,title,amount\n"
        "2026-05-01,Compra farmacia,25.00\n"
        "2026-05-02,Estorno farmacia,-10.00\n",
        encoding="utf-8",
    )

    r = import_nubank_csv(csv_path, tmp_db, kind="credit", account_id="nubank:test-card")
    assert r.total_read == 2

    rows = tmp_db.list_transactions(account_id="nubank:test-card")
    amounts = sorted(round(float(row["amount"]), 2) for row in rows)
    assert amounts == [-10.0, 25.0]
```

- [ ] **Step 2: Run importer tests and verify they fail on the old sign flip**

Run:

```bash
cd /opt/projetos/financas-agent
pytest tests/test_importers.py::test_import_nubank_credit_preserves_purchase_signs tests/test_importers.py::test_import_nubank_credit_preserves_negative_adjustments -q
```

Expected result before implementation:

```text
FAILED tests/test_importers.py::test_import_nubank_credit_preserves_purchase_signs
FAILED tests/test_importers.py::test_import_nubank_credit_preserves_negative_adjustments
```

- [ ] **Step 3: Remove the Nubank credit card sign flip**

In `src/importers/csv_nubank.py`, change the credit branch to this:

```python
    if kind == "credit":
        acc_id = account_id or "nubank:credit-card"
        mapping = CSVMapping(
            date_col="date",
            amount_col="amount",
            description_col="title",
            date_format="%Y-%m-%d",
        )
        return import_csv(
            path, db, mapping=mapping, account_id=acc_id,
            institution="Nubank", account_type="CREDIT",
        )
```

Delete the `_flip_credit_card_signs` function from the bottom of `src/importers/csv_nubank.py`.

The credit-card docstring at the top of `import_nubank_csv` already says the CSV amounts are positive spending, so no extra behavior comment is needed.

- [ ] **Step 4: Run focused importer tests**

Run:

```bash
cd /opt/projetos/financas-agent
pytest tests/test_importers.py -q
```

Expected result:

```text
passed
```

- [ ] **Step 5: Commit Task 2**

Run:

```bash
cd /opt/projetos/financas-agent
git add src/importers/csv_nubank.py tests/test_importers.py
git commit -m "fix: preserve Nubank credit purchase signs"
```

## Task 3: Summary Endpoint And CLI Report Use Canonical Signs

**Files:**
- Modify: `tests/test_web_app.py`
- Modify: `src/web/app.py`
- Modify: `src/cli.py`

- [ ] **Step 1: Add a failing `/api/summary` regression test**

In `tests/test_web_app.py`, add these imports near the top:

```python
from datetime import date, timedelta
from decimal import Decimal

from src.storage import Account, Transaction
```

Add this helper and test after `test_summary_empty`:

```python
def _seed_summary_sign_transactions(db):
    posted = date.today() - timedelta(days=3)
    db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    db.upsert_account(Account(id="card1", source="test", name="Card", type="CREDIT"))
    db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=posted,
            amount=Decimal("1000.00"),
            description="Salary",
            source="test",
            category="Salary",
        ),
        Transaction(
            account_id="bank1",
            posted_at=posted,
            amount=Decimal("-100.00"),
            description="Debit groceries",
            source="test",
            category="Groceries",
        ),
        Transaction(
            account_id="bank1",
            posted_at=posted,
            amount=Decimal("-300.00"),
            description="Invoice payment from bank",
            source="test",
            category="Credit card payment",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("300.00"),
            description="Card purchase",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("-50.00"),
            description="Card refund",
            source="test",
            category="Shopping",
        ),
        Transaction(
            account_id="card1",
            posted_at=posted,
            amount=Decimal("-300.00"),
            description="Invoice settlement on card",
            source="test",
            category="Credit card payment",
        ),
    ])


def test_summary_uses_canonical_financial_signs(client, tmp_db):
    _seed_summary_sign_transactions(tmp_db)

    s = client.get("/api/summary?days=30").json()

    assert s["transactions"] == 6
    assert s["inflow"] == 1000.0
    assert s["outflow"] == -350.0
    assert s["net"] == 650.0

    by_category = {row["category"]: row["amount"] for row in s["by_category"]}
    assert by_category == {"Shopping": -250.0, "Groceries": -100.0}
```

- [ ] **Step 2: Run the summary test and verify it fails on raw-sign logic**

Run:

```bash
cd /opt/projetos/financas-agent
pytest tests/test_web_app.py::test_summary_uses_canonical_financial_signs -q
```

Expected result before implementation:

```text
FAILED tests/test_web_app.py::test_summary_uses_canonical_financial_signs
```

The old code counts the card purchase as inflow and counts card payments as outflow, so the failure should show values different from `1000.0`, `-350.0`, and `650.0`.

- [ ] **Step 3: Update `/api/summary` to use canonical helpers**

In `src/web/app.py`, add this import with the other agent imports:

```python
from ..agent.context import income_value, spending_value
```

Replace the body of the `summary` route with this implementation:

```python
    @app.get("/api/summary")
    def summary(days: int = 30, db: Database = Depends(get_db)) -> dict[str, Any]:
        since = date.today() - timedelta(days=days)
        rows = db.list_transactions(since=since, limit=10_000)
        account_types = {row["id"]: row["type"] for row in db.list_accounts()}

        by_cat: dict[str, float] = {}
        inflow = 0.0
        outflow = 0.0
        for r in rows:
            amount = float(r["amount"])
            account_type = account_types.get(r["account_id"])
            category = r["category"] or "(sem categoria)"

            inflow += income_value(amount, account_type, category)

            spent = spending_value(amount, account_type, category)
            if spent:
                outflow -= spent
                by_cat[category] = by_cat.get(category, 0.0) - spent

        return {
            "days": days,
            "transactions": len(rows),
            "inflow": round(inflow, 2),
            "outflow": round(outflow, 2),
            "net": round(inflow + outflow, 2),
            "by_category": [
                {"category": k, "amount": round(v, 2)}
                for k, v in sorted(by_cat.items(), key=lambda kv: kv[1])
                if round(v, 2) != 0
            ],
        }
```

This preserves the existing legacy response shape: `outflow` and `by_category.amount` are negative for spending, but they are calculated from canonical positive spending values internally.

- [ ] **Step 4: Update the CLI report to use the same helpers**

In `src/cli.py`, add this import with the other agent imports:

```python
from .agent.context import spending_value
```

Replace the body inside the `try` block of `report` with this implementation:

```python
        since = date.today() - timedelta(days=days)
        rows = db.list_transactions(since=since, limit=10_000)
        account_types = {row["id"]: row["type"] for row in db.list_accounts()}

        by_cat: dict[str, float] = {}
        for r in rows:
            category = r["category"] or "(sem categoria)"
            spent = spending_value(
                float(r["amount"]),
                account_types.get(r["account_id"]),
                category,
            )
            if spent:
                by_cat[category] = by_cat.get(category, 0.0) - spent

        table = Table("Categoria", "Total (R$)")
        for cat, total in sorted(by_cat.items(), key=lambda kv: kv[1]):
            if round(total, 2) == 0:
                continue
            table.add_row(cat, f"{total:,.2f}")
        console.print(table)
        console.print(f"[bold]Sa?da total:[/bold] R$ {sum(by_cat.values()):,.2f}")
```

- [ ] **Step 5: Run focused web and CLI-adjacent tests**

Run:

```bash
cd /opt/projetos/financas-agent
pytest tests/test_web_app.py tests/test_financial_signs.py -q
python -m src.cli report --days 30 >/tmp/deon-fin-cli-report.txt
tail -n 20 /tmp/deon-fin-cli-report.txt
```

Expected result:

```text
passed
```

The CLI command should exit with status `0` and print a category table. Do not assert specific production values because the VPS database contains real personal data.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
cd /opt/projetos/financas-agent
git add src/web/app.py src/cli.py tests/test_web_app.py
git commit -m "fix: summarize spending with canonical signs"
```

## Task 4: Full Verification And VPS Deploy

**Files:**
- No new source files beyond Tasks 1-3.
- Uses: `scripts/vps_deploy.sh`

- [ ] **Step 1: Run the full test suite**

Run:

```bash
cd /opt/projetos/financas-agent
pytest
```

Expected result:

```text
passed, skipped allowed only for Pluggy integration tests when credentials are not provided by the shell
```

- [ ] **Step 2: Inspect the final diff**

Run:

```bash
cd /opt/projetos/financas-agent
git status --short
git diff --stat HEAD~3..HEAD
```

Expected result:

```text
Only .cursor/ may remain untracked. Source and test changes must be committed.
```

- [ ] **Step 3: Deploy through the existing VPS script**

Run:

```bash
cd /opt/projetos/financas-agent
./scripts/vps_deploy.sh
```

Expected result:

```text
SQLite backup created under data/backups/
pytest passes
docker compose build succeeds
docker compose up -d succeeds
https://fin.deonlab.tech/api/health returns 200 with {"status":"ok"}
```

- [ ] **Step 4: Push the branch**

Run:

```bash
cd /opt/projetos/financas-agent
git push deon codex/financas-vps-foundation
```

Expected result:

```text
codex/financas-vps-foundation updated on deon7769/deon-fin
```

## Self-Review

- Spec coverage: Task 1 covers the canonical rule and no-duplicate invoice invariant. Task 2 covers Nubank credit imports and negative adjustments. Task 3 covers `/api/summary` and CLI calculations. Task 4 covers full tests, deploy, health check, and push. Production SQLite migration, budget tables, UI, and environment splitting are explicitly excluded.
- Placeholder scan: no unresolved markers, placeholder functions, or unspecified test commands remain.
- Type consistency: helper signatures use `amount: float`, `account_type: str | None`, and `category: str | None`; all planned callers pass `float(r["amount"])`, account type from `db.list_accounts()`, and a normalized category string.
