from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.agent.context import (
    account_owner_aliases,
    build_financial_context,
    income_value,
    internal_transfer_row_ids,
    spending_value,
)
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


def test_portuguese_external_pix_sent_counts_as_spending_when_not_internal():
    assert (
        spending_value(
            -100.0,
            "BANK",
            "Transfer\u00eancia - PIX",
            description="Pix enviado fornecedor externo",
            external_transfer_spending=True,
        )
        == 100.0
    )
    assert (
        spending_value(
            -150.0,
            "BANK",
            "Transfer\u00eancias - PIX",
            description="Pix enviado fornecedor externo",
            external_transfer_spending=True,
        )
        == 150.0
    )
    assert (
        spending_value(
            -100.0,
            "BANK",
            "Transfer\u00eancia - PIX",
            description="Transferencia",
            external_transfer_spending=True,
        )
        == 0.0
    )
    assert (
        spending_value(
            -150.0,
            "BANK",
            "Transfer\u00eancia - PIX",
            description="Pix entre contas",
            external_transfer_spending=True,
        )
        == 0.0
    )


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


def test_account_owner_aliases_ignore_numeric_account_names():
    aliases = account_owner_aliases([
        {"name": "077 0001 31238064 0", "institution": "Banco Teste"},
        {"name": "DAVI OLIVEIRA NETO", "institution": "DAVI OLIVEIRA NETO"},
    ])

    assert aliases == ("davi oliveira neto",)


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


def test_context_counts_external_pix_sent_as_spending_without_counting_own_pix_pair(tmp_db):
    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank 1", type="BANK"))
    tmp_db.upsert_account(Account(id="bank2", source="test", name="Bank 2", type="BANK"))
    tmp_db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 6, 12),
            amount=Decimal("-321.09"),
            description="Pix enviado fornecedor externo",
            source="test",
            category="Transfer - PIX",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 6, 13),
            amount=Decimal("-5400.00"),
            description="Pix enviado conta propria",
            source="test",
            category="Transfer - PIX",
        ),
        Transaction(
            account_id="bank2",
            posted_at=date(2026, 6, 13),
            amount=Decimal("5400.00"),
            description="Pix recebido conta propria",
            source="test",
            category="Transfer - PIX",
        ),
    ])

    ctx = build_financial_context(tmp_db, today=date(2026, 6, 21)).to_dict()

    assert ctx["fluxo_mensal"]["2026-06"]["renda"] == 0.0
    assert ctx["fluxo_mensal"]["2026-06"]["gasto"] == 321.09
    categories = {row["categoria"]: row["total"] for row in ctx["gasto_por_categoria"]}
    assert categories == {"Transfer - PIX": 321.09}


def test_internal_transfer_match_prefers_own_pix_debit_when_amounts_collide():
    rows = [
        {
            "id": "external-debit",
            "account_id": "bank-main",
            "posted_at": "2026-06-12",
            "amount": -500.0,
            "description": "Pix enviado fornecedor externo",
            "raw_description": "PIX ENVIADO FORNECEDOR EXTERNO",
            "category": "Transfer - PIX",
            "account_type": "BANK",
        },
        {
            "id": "own-debit",
            "account_id": "bank-main",
            "posted_at": "2026-06-12",
            "amount": -500.0,
            "description": "Pix enviado Davi Oliveira Neto reserva",
            "raw_description": "PIX ENVIADO DAVI OLIVEIRA NETO RESERVA",
            "category": "Transfer - PIX",
            "account_type": "BANK",
        },
        {
            "id": "own-credit",
            "account_id": "bank-reserve",
            "posted_at": "2026-06-12",
            "amount": 500.0,
            "description": "Pix recebido Davi Oliveira Neto reserva",
            "raw_description": "PIX RECEBIDO DAVI OLIVEIRA NETO RESERVA",
            "category": "Transfer - PIX",
            "account_type": "BANK",
        },
    ]

    assert internal_transfer_row_ids(rows, owner_names=["Davi Oliveira Neto"]) == {
        "own-debit",
        "own-credit",
    }


def test_automatic_investment_is_neutral_and_counts_as_period_invested(tmp_db):
    assert spending_value(-100.0, "BANK", "Automatic investment") == 0.0
    assert spending_value(-150.0, "BANK", "Investment application") == 0.0
    assert income_value(100.0, "BANK", "Automatic investment") == 0.0
    assert income_value(150.0, "BANK", "Investment application") == 0.0

    tmp_db.upsert_account(Account(id="bank1", source="test", name="Bank 1", type="BANK"))
    tmp_db.insert_transactions([
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 6, 14),
            amount=Decimal("-100.00"),
            description="Automatic investment",
            source="test",
            category="Automatic investment",
        ),
        Transaction(
            account_id="bank1",
            posted_at=date(2026, 6, 15),
            amount=Decimal("-150.00"),
            description="Investment application",
            source="test",
            category="Investment application",
        ),
    ])

    ctx = build_financial_context(tmp_db, today=date(2026, 6, 21)).to_dict()

    assert ctx["fluxo_mensal"]["2026-06"]["renda"] == 0.0
    assert ctx["fluxo_mensal"]["2026-06"]["gasto"] == 0.0
    assert ctx["fluxo_mensal"]["2026-06"]["investido"] == 250.0
    assert ctx["aportes_periodo_total"] == 250.0
    assert ctx["investido_total"] == 250.0
    assert ctx["gasto_por_categoria"] == []
