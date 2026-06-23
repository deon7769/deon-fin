from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

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


def test_credit_card_online_payment_description_does_not_count_as_refund():
    assert (
        spending_value(
            -5384.5,
            "CREDIT",
            "Shopping",
            description="PAGAMENTO ON LINE",
        )
        == 0.0
    )
    assert (
        spending_value(
            -40.0,
            "CREDIT",
            "Shopping",
            description="ESTORNO LOJA X",
        )
        == -40.0
    )


def test_own_account_transfer_description_does_not_count_as_spending_when_category_is_wrong():
    assert (
        spending_value(
            -3380.0,
            "BANK",
            "Education",
            description="Transferência enviada|DAVI DE OLIVEIRA NETO 05398277111",
            owner_names=["DAVI OLIVEIRA NETO"],
        )
        == 0.0
    )
    assert (
        spending_value(
            -200.0,
            "BANK",
            "Education",
            description="Transferência enviada|LEANDRO LEMES",
            owner_names=["DAVI OLIVEIRA NETO"],
        )
        == 200.0
    )


@pytest.mark.parametrize("category", [
    "Investimentos",
    "Pagamento de fatura",
    "Payment",
    "Transferência - PIX",
    "Transferências",
    "Transferência entre contas",
    "Transferência interna",
    "Transfer - Internal",
    "Transferências - PIX",
    "Transferências - TED/DOC",
    "Transferência - TED/DOC",
])
def test_non_spending_aliases_do_not_count_as_spending_or_income(category):
    assert spending_value(-100.0, "BANK", category) == 0.0
    assert spending_value(100.0, "BANK", category) == 0.0
    assert spending_value(100.0, "CREDIT", category) == 0.0
    assert spending_value(-100.0, "CREDIT", category) == 0.0
    assert income_value(100.0, "BANK", category) == 0.0


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


def test_context_tracks_portuguese_non_spending_aliases(tmp_db):
    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank", type="BANK"))
    tmp_db.upsert_account(Account(id="card1", source="test", name="Card", type="CREDIT"))
    tmp_db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 5, 1),
            amount=Decimal("-300.00"),
            description="Pagamento fatura",
            source="test",
            category="Pagamento de fatura",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 5, 2),
            amount=Decimal("-200.00"),
            description="Aplicacao",
            source="test",
            category="Investimentos",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 5, 3),
            amount=Decimal("-50.00"),
            description="Transferencia interna",
            source="test",
            category="Transferência entre contas",
        ),
        Transaction(
            account_id="card1",
            posted_at=date(2026, 5, 4),
            amount=Decimal("100.00"),
            description="Compra cartão",
            source="test",
            category="Shopping",
        ),
    ])

    ctx = build_financial_context(tmp_db, today=date(2026, 6, 19)).to_dict()

    assert ctx["fluxo_mensal"]["2026-05"]["gasto"] == 100.0
    assert ctx["fluxo_mensal"]["2026-05"]["investido"] == 200.0
    assert ctx["pagamentos_cartao_total"] == 300.0
    assert ctx["investido_total"] == 200.0
    assert ctx["gasto_por_categoria"] == [
        {"categoria": "Shopping", "total": 100.0, "qtd": 1, "media_mensal": 100.0}
    ]


def test_context_counts_external_pix_income_without_counting_mirrored_own_pix(tmp_db):
    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank 1", type="BANK"))
    tmp_db.upsert_account(Account(id="bank2", source="test", name="Bank 2", type="BANK"))
    tmp_db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 6, 12),
            amount=Decimal("7845.40"),
            description="Pix recebido cliente externo",
            source="test",
            category="Transfer - PIX",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 6, 12),
            amount=Decimal("-5400.00"),
            description="Pix enviado conta propria",
            source="test",
            category="Same person transfer",
        ),
        Transaction(
            account_id="bank2",
            posted_at=date(2026, 6, 12),
            amount=Decimal("5400.00"),
            description="Pix recebido conta propria",
            source="test",
            category="Transfer - PIX",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 6, 13),
            amount=Decimal("-100.00"),
            description="Mercado",
            source="test",
            category="Groceries",
        ),
    ])

    ctx = build_financial_context(tmp_db, today=date(2026, 6, 21)).to_dict()

    assert ctx["fluxo_mensal"]["2026-06"]["renda"] == 7845.4
    assert ctx["fluxo_mensal"]["2026-06"]["gasto"] == 100.0
