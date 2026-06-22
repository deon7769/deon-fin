from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.storage import Account, Transaction
from src.web.repositories import buckets_repo, tags_repo, transactions_repo


def _seed_accounts(db) -> None:
    db.upsert_account(
        Account(
            id="repo-checking",
            source="test",
            institution="Banco Teste",
            name="Conta Corrente",
            type="CHECKING",
        )
    )
    db.upsert_account(
        Account(
            id="repo-credit",
            source="test",
            institution="Banco Teste",
            name="Cartao Teste",
            type="CREDIT",
        )
    )


def _insert(
    db,
    *,
    account_id: str = "repo-checking",
    posted_at: date = date(2026, 6, 20),
    amount: str = "-10.00",
    description: str = "Compra Teste",
    category: str | None = "Alimentação - Restaurante",
    external_id: str,
) -> Transaction:
    tx = Transaction(
        account_id=account_id,
        posted_at=posted_at,
        amount=Decimal(amount),
        description=description,
        raw_description=description.upper(),
        category=category,
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    db._conn.execute(
        "UPDATE transactions SET reference_month=? WHERE id=?",
        (posted_at.strftime("%Y-%m"), tx.id),
    )
    db._conn.commit()
    return tx


def test_list_transactions_filters_common_fields_and_paginates(tmp_db):
    _seed_accounts(tmp_db)
    june_expense = _insert(
        tmp_db,
        amount="-120.00",
        description="IFOOD Restaurante",
        external_id="repo-common-1",
    )
    salary = _insert(
        tmp_db,
        posted_at=date(2026, 6, 21),
        amount="3500.00",
        description="Salario Empresa",
        external_id="repo-common-2",
    )
    _insert(
        tmp_db,
        posted_at=date(2026, 7, 2),
        amount="-75.00",
        description="Uber Viagem",
        external_id="repo-common-3",
    )
    hidden = _insert(
        tmp_db,
        amount="-40.00",
        description="Farmacia Oculta",
        external_id="repo-common-4",
    )
    tmp_db._conn.execute("UPDATE transactions SET hidden=1 WHERE id=?", (hidden.id,))
    tmp_db._conn.commit()

    month_page = transactions_repo.list_transactions(tmp_db, month="2026-06", page=1, page_size=2)
    assert month_page["total"] == 2
    assert [item["id"] for item in month_page["items"]] == [salary.id, june_expense.id]
    assert month_page["page"] == 1
    assert month_page["page_size"] == 2

    assert transactions_repo.list_transactions(tmp_db, month="2026-06", q="ifood")["items"][0][
        "id"
    ] == june_expense.id
    assert transactions_repo.list_transactions(tmp_db, date_from=date(2026, 7, 1))["total"] == 1
    assert transactions_repo.list_transactions(tmp_db, type="income")["total"] == 1
    assert transactions_repo.list_transactions(tmp_db, type="expense")["total"] == 2
    assert transactions_repo.list_transactions(tmp_db, amount_min=100, amount_max=200)["total"] == 1
    assert transactions_repo.list_transactions(tmp_db, account_id="repo-checking")["total"] == 3
    assert transactions_repo.list_transactions(tmp_db, hidden="include")["total"] == 4
    assert transactions_repo.list_transactions(tmp_db, hidden="only")["items"][0]["id"] == hidden.id


def test_filter_income_includes_credit_refunds(tmp_db):
    _seed_accounts(tmp_db)
    refund = _insert(
        tmp_db,
        account_id="repo-credit",
        amount="-35.00",
        description="Estorno Cartao",
        category="Lazer",
        external_id="repo-credit-refund-1",
    )
    purchase = _insert(
        tmp_db,
        account_id="repo-credit",
        amount="90.00",
        description="Compra Cartao",
        category="Lazer",
        external_id="repo-credit-refund-2",
    )

    income_page = transactions_repo.list_transactions(tmp_db, type="income")
    expense_page = transactions_repo.list_transactions(tmp_db, type="expense")

    assert [item["id"] for item in income_page["items"]] == [refund.id]
    assert income_page["items"][0]["type"] == "income"
    assert [item["id"] for item in expense_page["items"]] == [purchase.id]


def test_filter_expense_excludes_neutral_transfers_and_card_payments(tmp_db):
    _seed_accounts(tmp_db)
    grocery = _insert(
        tmp_db,
        amount="-120.00",
        description="Mercado",
        category="Groceries",
        external_id="repo-type-expense-1",
    )
    _insert(
        tmp_db,
        amount="-700.00",
        description="Pix entre contas",
        category="Transfer - PIX",
        external_id="repo-type-expense-2",
    )
    _insert(
        tmp_db,
        amount="-900.00",
        description="Pagamento fatura",
        category="Credit card payment",
        external_id="repo-type-expense-3",
    )

    page = transactions_repo.list_transactions(tmp_db, month="2026-06", type="expense")

    assert [item["id"] for item in page["items"]] == [grocery.id]
    assert page["total"] == 1
    assert page["summary"] == {"income": 0.0, "expense": 120.0, "balance": -120.0}


def test_list_transactions_filters_bucket_and_tag_with_none(tmp_db):
    _seed_accounts(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    tags_repo.seed_tags(tmp_db)
    bucket = buckets_repo.list_buckets(tmp_db)[0]
    tag = tags_repo.list_tags(tmp_db)[0]
    bucketed = _insert(tmp_db, external_id="repo-bucket-tag-1")
    tagged = _insert(tmp_db, description="Tagged", external_id="repo-bucket-tag-2")
    plain = _insert(tmp_db, description="Plain", external_id="repo-bucket-tag-3")
    tmp_db._conn.execute(
        "UPDATE transactions SET bucket_id=?, tag_id=? WHERE id=?",
        (bucket["id"], tag["id"], bucketed.id),
    )
    tmp_db._conn.execute("UPDATE transactions SET tag_id=? WHERE id=?", (tag["id"], tagged.id))
    tmp_db._conn.commit()

    by_bucket = transactions_repo.list_transactions(
        tmp_db,
        bucket_ids=[bucket["id"], None],
        hidden="include",
    )
    assert {item["id"] for item in by_bucket["items"]} == {bucketed.id, tagged.id, plain.id}

    by_tag = transactions_repo.list_transactions(tmp_db, tag_ids=[tag["id"]], hidden="include")
    assert {item["id"] for item in by_tag["items"]} == {bucketed.id, tagged.id}

    no_tag = transactions_repo.list_transactions(tmp_db, tag_ids=[None], hidden="include")
    assert [item["id"] for item in no_tag["items"]] == [plain.id]


def test_list_transactions_summary_respects_hidden_filter_and_uses_sign_helpers(tmp_db):
    _seed_accounts(tmp_db)
    _insert(
        tmp_db,
        amount="5000.00",
        description="Salario",
        external_id="repo-summary-1",
    )
    _insert(
        tmp_db,
        amount="-100.00",
        description="Mercado",
        category="Alimentação - Mercado",
        external_id="repo-summary-2",
    )
    _insert(
        tmp_db,
        account_id="repo-credit",
        amount="250.00",
        description="Compra Cartao",
        category="Lazer",
        external_id="repo-summary-3",
    )
    _insert(
        tmp_db,
        amount="-700.00",
        description="Transferencia",
        category="Transferência - PIX",
        external_id="repo-summary-4",
    )
    hidden = _insert(
        tmp_db,
        amount="-999.00",
        description="Oculta",
        external_id="repo-summary-5",
    )
    tmp_db._conn.execute("UPDATE transactions SET hidden=1 WHERE id=?", (hidden.id,))
    tmp_db._conn.commit()

    visible = transactions_repo.list_transactions(tmp_db, month="2026-06")
    page = transactions_repo.list_transactions(tmp_db, month="2026-06", hidden="include")

    assert visible["summary"] == {"income": 5000.0, "expense": 350.0, "balance": 4650.0}
    assert page["summary"] == {"income": 5000.0, "expense": 1349.0, "balance": 3651.0}
    hidden_only = transactions_repo.list_transactions(tmp_db, month="2026-06", hidden="only")
    assert hidden_only["total"] == 1
    assert hidden_only["summary"] == {"income": 0.0, "expense": 999.0, "balance": -999.0}
    visible_transfer = next(item for item in page["items"] if item["description"] == "Transferencia")
    assert visible_transfer["type"] == "expense"
    assert visible_transfer["signed_value"] == 0.0
    assert visible_transfer["display_value"] == -700.0


def test_list_transactions_display_value_preserves_credit_card_expense_sign(tmp_db):
    _seed_accounts(tmp_db)
    _insert(
        tmp_db,
        account_id="repo-credit",
        amount="250.00",
        description="Compra Cartao",
        category="Lazer",
        external_id="repo-display-credit",
    )

    page = transactions_repo.list_transactions(tmp_db, month="2026-06")

    item = page["items"][0]
    assert item["type"] == "expense"
    assert item["amount"] == 250.0
    assert item["signed_value"] == -250.0
    assert item["display_value"] == -250.0


def test_list_transactions_includes_translated_category_label(tmp_db):
    _seed_accounts(tmp_db)
    _insert(
        tmp_db,
        amount="-89.90",
        description="Restaurante",
        category="Eating out",
        external_id="repo-category-label",
    )

    page = transactions_repo.list_transactions(tmp_db, month="2026-06")

    item = page["items"][0]
    assert item["category"] == "Eating out"
    assert item["category_label"] == "Restaurantes"


def test_update_transaction_bucket_marks_manual_without_rule_side_effects(tmp_db):
    _seed_accounts(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    tx = _insert(tmp_db, description="Padaria Alfa", external_id="repo-bucket-rule-1")
    bucket = buckets_repo.list_buckets(tmp_db)[0]

    updated = transactions_repo.update_transaction(tmp_db, tx.id, bucket_id=bucket["id"])

    assert updated["bucket_id"] == bucket["id"]
    assert buckets_repo.list_rules(tmp_db) == []

    cleared = transactions_repo.update_transaction(tmp_db, tx.id, bucket_id=None)

    assert cleared["bucket_id"] is None
    assert buckets_repo.list_rules(tmp_db) == []
