from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.storage import Account, Transaction
from src.storage.reference_month import reference_month
from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import buckets_repo, budget_repo, profile_repo


@pytest.fixture
def client(tmp_db, monkeypatch):
    monkeypatch.setattr("src.web.app._background_sync", lambda *a, **kw: None)
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.mnt.load_family_profile",
        lambda: None,
    )
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)

    app = create_app()

    def _override_db():
        yield tmp_db

    class FakePluggy:
        def create_connect_token(self, *, client_user_id=None, item_id=None):
            return "fake.connect.token"

        def delete_item(self, item_id):
            return None

        def close(self):
            return None

    fake = FakePluggy()

    def _override_pluggy():
        yield fake

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_pluggy] = _override_pluggy
    return TestClient(app)


def _seed_accounts(db) -> None:
    db.upsert_account(
        Account(
            id="budget-bank",
            source="test",
            institution="Banco Teste",
            name="Conta Corrente",
            type="CHECKING",
        )
    )
    db.upsert_account(
        Account(
            id="budget-card",
            source="test",
            institution="Banco Teste",
            name="Cartao Teste",
            type="CREDIT",
        )
    )


def _insert_tx(
    db,
    *,
    external_id: str,
    account_id: str = "budget-bank",
    posted_at: date = date(2026, 6, 15),
    amount: str = "-10.00",
    description: str = "Compra teste",
    category: str | None = "Mercado",
    reference_month_value: str = "2026-06",
    bucket_id: int | None = None,
    hidden: bool = False,
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
        """
        UPDATE transactions
           SET reference_month=?,
               bucket_id=?,
               bucket_source=?,
               hidden=?
         WHERE id=?
        """,
        (
            reference_month_value,
            bucket_id,
            "manual" if bucket_id is not None else None,
            1 if hidden else 0,
            tx.id,
        ),
    )
    db._conn.commit()
    return tx


def _bucket_by_key(db, key: str) -> dict[str, Any]:
    buckets_repo.seed_buckets(db)
    return next(bucket for bucket in buckets_repo.list_buckets(db) if bucket["key"] == key)


def test_budget_for_month_aggregates_buckets_and_uncategorized(tmp_db, monkeypatch):
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    _seed_accounts(tmp_db)

    fixed = _bucket_by_key(tmp_db, "custos_fixos")
    pleasures = _bucket_by_key(tmp_db, "prazeres")
    tmp_db._conn.execute(
        "UPDATE budget_buckets SET planned_kind='amount', planned_value=300 WHERE id=?",
        (pleasures["id"],),
    )
    tmp_db._conn.commit()

    _insert_tx(
        tmp_db,
        external_id="budget-salary",
        amount="1000.00",
        description="Salario",
        category="Salario",
    )
    _insert_tx(
        tmp_db,
        external_id="budget-fixed",
        amount="-600.00",
        description="Aluguel",
        category="Moradia",
        bucket_id=fixed["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="budget-card-pleasure",
        account_id="budget-card",
        amount="250.00",
        description="Cinema",
        category="Lazer",
        bucket_id=pleasures["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="budget-card-refund",
        account_id="budget-card",
        amount="-50.00",
        description="Estorno cinema",
        category="Lazer",
        bucket_id=pleasures["id"],
    )
    uncategorized = _insert_tx(
        tmp_db,
        external_id="budget-uncategorized",
        amount="-80.00",
        description="Mercado sem pote",
        category="Mercado",
    )
    _insert_tx(
        tmp_db,
        external_id="budget-hidden",
        account_id="budget-card",
        amount="999.00",
        description="Compra oculta",
        category="Lazer",
        bucket_id=pleasures["id"],
        hidden=True,
    )
    _insert_tx(
        tmp_db,
        external_id="budget-card-payment",
        amount="-250.00",
        description="Pagamento fatura",
        category="Pagamento de fatura",
        bucket_id=fixed["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="budget-transfer",
        amount="-100.00",
        description="Pix entre contas",
        category="Transferência - PIX",
        bucket_id=fixed["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="budget-other-month",
        amount="-500.00",
        description="Outro mes",
        category="Moradia",
        reference_month_value="2026-05",
        bucket_id=fixed["id"],
    )

    result = budget_repo.budget_for_month(tmp_db, "2026-06")
    categories = {item["key"]: item for item in result["categories"]}

    assert result["month"] == "2026-06"
    assert result["income"] == 1000.0
    assert result["income_source"] == "transactions"
    assert result["spent"] == 880.0
    assert result["remaining"] == 120.0
    assert result["used_pct"] == 88.0
    assert len(result["categories"]) == 6

    assert categories["custos_fixos"]["planned"] == 550.0
    assert categories["custos_fixos"]["spent"] == 600.0
    assert categories["custos_fixos"]["remaining"] == -50.0
    assert categories["custos_fixos"]["used_pct"] == 109.09
    assert categories["custos_fixos"]["exceeded"] is True
    assert categories["custos_fixos"]["tx_count"] == 1

    assert categories["prazeres"]["planned_kind"] == "amount"
    assert categories["prazeres"]["planned"] == 300.0
    assert categories["prazeres"]["spent"] == 200.0
    assert categories["prazeres"]["remaining"] == 100.0
    assert categories["prazeres"]["used_pct"] == 66.67
    assert categories["prazeres"]["exceeded"] is False
    assert categories["prazeres"]["tx_count"] == 1

    assert result["uncategorized"] == [
        {
            "id": uncategorized.id,
            "description": "Mercado sem pote",
            "date": "2026-06-15",
            "amount": 80.0,
        }
    ]


def test_budget_ignores_credit_card_invoice_payment_with_wrong_provider_category(tmp_db, monkeypatch):
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    _seed_accounts(tmp_db)

    pleasures = _bucket_by_key(tmp_db, "prazeres")
    tmp_db._conn.execute(
        "UPDATE budget_buckets SET planned_kind='amount', planned_value=300 WHERE id=?",
        (pleasures["id"],),
    )
    tmp_db._conn.commit()

    _insert_tx(
        tmp_db,
        external_id="budget-payment-misclassified-salary",
        amount="1000.00",
        description="Salario",
        category="Salario",
    )
    _insert_tx(
        tmp_db,
        external_id="budget-payment-misclassified-purchase",
        account_id="budget-card",
        amount="200.00",
        description="Cinema",
        category="Shopping",
        bucket_id=pleasures["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="budget-payment-misclassified-card-payment",
        account_id="budget-card",
        amount="-5384.50",
        description="PAGAMENTO ON LINE",
        category="Shopping",
        bucket_id=pleasures["id"],
    )

    result = budget_repo.budget_for_month(tmp_db, "2026-06")
    category = next(item for item in result["categories"] if item["key"] == "prazeres")

    assert result["spent"] == 200.0
    assert category["spent"] == 200.0
    assert category["remaining"] == 100.0
    assert category["used_pct"] == 66.67
    assert category["tx_count"] == 1


def test_budget_ignores_own_account_transfer_with_wrong_provider_category(tmp_db, monkeypatch):
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    _seed_accounts(tmp_db)
    tmp_db._conn.execute(
        "UPDATE accounts SET name='DAVI OLIVEIRA NETO', institution='DAVI OLIVEIRA NETO' WHERE id='budget-card'",
    )

    pleasures = _bucket_by_key(tmp_db, "prazeres")
    tmp_db._conn.execute(
        "UPDATE budget_buckets SET planned_kind='amount', planned_value=300 WHERE id=?",
        (pleasures["id"],),
    )
    tmp_db._conn.commit()

    _insert_tx(
        tmp_db,
        external_id="budget-own-transfer-salary",
        amount="1000.00",
        description="Salario",
        category="Salario",
    )
    _insert_tx(
        tmp_db,
        external_id="budget-own-transfer-purchase",
        account_id="budget-card",
        amount="200.00",
        description="Cinema",
        category="Shopping",
        bucket_id=pleasures["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="budget-own-transfer-misclassified",
        amount="-3380.00",
        description="Transferência enviada|DAVI DE OLIVEIRA NETO 05398277111",
        category="Education",
        bucket_id=pleasures["id"],
    )

    result = budget_repo.budget_for_month(tmp_db, "2026-06")
    category = next(item for item in result["categories"] if item["key"] == "prazeres")

    assert result["spent"] == 200.0
    assert category["spent"] == 200.0
    assert category["remaining"] == 100.0
    assert category["used_pct"] == 66.67
    assert category["tx_count"] == 1


def test_budget_respects_account_total_policy(tmp_db, monkeypatch):
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    _seed_accounts(tmp_db)
    pleasures = _bucket_by_key(tmp_db, "prazeres")
    tmp_db._conn.execute(
        """
        INSERT INTO account_total_settings (
            account_id, include_balance, include_transactions
        )
        VALUES ('budget-bank', 1, 0)
        """
    )
    tmp_db._conn.commit()
    _insert_tx(
        tmp_db,
        external_id="budget-policy-income",
        amount="1000.00",
        description="Salario excluido",
        category="Salario",
    )
    _insert_tx(
        tmp_db,
        external_id="budget-policy-bank-expense",
        amount="-300.00",
        description="Mercado excluido",
        category="Mercado",
        bucket_id=pleasures["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="budget-policy-card-expense",
        account_id="budget-card",
        amount="200.00",
        description="Cinema",
        category="Lazer",
        bucket_id=pleasures["id"],
    )

    result = budget_repo.budget_for_month(tmp_db, "2026-06")
    category = next(item for item in result["categories"] if item["key"] == "prazeres")

    assert result["income"] == 0.0
    assert result["income_source"] == "none"
    assert result["spent"] == 200.0
    assert category["spent"] == 200.0
    assert category["tx_count"] == 1


def test_budget_income_falls_back_to_profile_settings_family_profile_and_none(tmp_db, monkeypatch):
    _seed_accounts(tmp_db)
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )

    profile_repo.update_profile(
        tmp_db,
        name="",
        email="",
        monthly_income=4200.0,
        financial_month_start_day=1,
        goals_text="",
    )

    profile_budget = budget_repo.budget_for_month(tmp_db, "2026-06")
    assert profile_budget["income"] == 4200.0
    assert profile_budget["income_source"] == "profile"

    profile_repo.update_profile(
        tmp_db,
        name="",
        email="",
        monthly_income=0.0,
        financial_month_start_day=1,
        goals_text="",
    )
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=3300.0, financial_goals=[]),
    )

    settings_budget = budget_repo.budget_for_month(tmp_db, "2026-07")
    assert settings_budget["income"] == 3300.0
    assert settings_budget["income_source"] == "settings"

    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        budget_repo.mnt,
        "load_family_profile",
        lambda: {"receitas": [{"valor": 1200.0}, {"valor": 800.0}]},
    )

    family_budget = budget_repo.budget_for_month(tmp_db, "2026-08")
    assert family_budget["income"] == 2000.0
    assert family_budget["income_source"] == "family_profile"

    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    none_budget = budget_repo.budget_for_month(tmp_db, "2026-09")
    assert none_budget["income"] == 0.0
    assert none_budget["income_source"] == "none"
    assert none_budget["used_pct"] is None


def test_budget_settings_source_does_not_require_existing_profile(tmp_db, monkeypatch):
    _seed_accounts(tmp_db)
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=3300.0, financial_goals=[]),
    )

    result = budget_repo.budget_for_month(tmp_db, "2026-06")

    assert result["income"] == 3300.0
    assert result["income_source"] == "settings"


def test_budget_income_transactions_have_priority(tmp_db, monkeypatch):
    _seed_accounts(tmp_db)
    profile_repo.update_profile(
        tmp_db,
        name="",
        email="",
        monthly_income=4200.0,
        financial_month_start_day=1,
        goals_text="",
    )
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=3300.0, financial_goals=[]),
    )
    monkeypatch.setattr(
        budget_repo.mnt,
        "load_family_profile",
        lambda: {"receitas": [{"valor": 9999.0}]},
    )
    _insert_tx(
        tmp_db,
        external_id="budget-income-priority",
        amount="5100.00",
        description="Renda do mes",
        category="Salario",
    )

    result = budget_repo.budget_for_month(tmp_db, "2026-06")

    assert result["income"] == 5100.0
    assert result["income_source"] == "transactions"


def test_budget_income_counts_external_pix_without_counting_mirrored_own_pix(
    tmp_db, monkeypatch
):
    _seed_accounts(tmp_db)
    tmp_db.upsert_account(
        Account(
            id="budget-bank-2",
            source="test",
            institution="Banco Teste 2",
            name="Conta Secundaria",
            type="CHECKING",
        )
    )
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)
    _insert_tx(
        tmp_db,
        external_id="budget-external-pix-income",
        amount="7845.40",
        description="Pix recebido cliente externo",
        category="Transfer - PIX",
    )
    _insert_tx(
        tmp_db,
        external_id="budget-own-pix-out",
        amount="-5400.00",
        description="Pix enviado conta propria",
        category="Same person transfer",
    )
    _insert_tx(
        tmp_db,
        external_id="budget-own-pix-in",
        account_id="budget-bank-2",
        amount="5400.00",
        description="Pix recebido conta propria",
        category="Transfer - PIX",
    )

    result = budget_repo.budget_for_month(tmp_db, "2026-06")

    assert result["income"] == 7845.4
    assert result["income_source"] == "transactions"


def test_resolve_month_uses_profile_start_day(tmp_db, monkeypatch):
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(budget_repo.mnt, "load_family_profile", lambda: None)

    assert budget_repo.resolve_month(tmp_db, "2026-06") == "2026-06"
    assert budget_repo.resolve_month(tmp_db, "2026") is None
    assert budget_repo.resolve_month(tmp_db, "2026-13") is None
    assert budget_repo.resolve_month(tmp_db, None) == reference_month(date.today(), 1)

    profile_repo.update_profile(
        tmp_db,
        name="",
        email="",
        monthly_income=0.0,
        financial_month_start_day=10,
        goals_text="",
    )
    assert budget_repo.resolve_month(tmp_db, None) == reference_month(date.today(), 10)


def test_budget_endpoint_shape_and_legacy_smoke(client, tmp_db):
    _seed_accounts(tmp_db)
    _insert_tx(
        tmp_db,
        external_id="budget-endpoint-income",
        amount="100.00",
        description="Renda endpoint",
        category="Salario",
    )

    response = client.get("/api/budget?month=2026-06")
    summary = client.get("/api/summary?days=30")
    dashboard = client.get("/api/dashboard?meses=6")
    card = client.get("/api/cartao")

    assert response.status_code == 200
    assert set(response.json()) == {
        "month",
        "income",
        "spent",
        "remaining",
        "used_pct",
        "income_source",
        "categories",
        "uncategorized",
    }
    assert response.json()["income"] == 100.0
    assert len(response.json()["categories"]) == 6
    assert summary.status_code == 200
    assert dashboard.status_code == 200
    assert card.status_code == 200


def test_budget_endpoint_invalid_month(client):
    response = client.get("/api/budget?month=2026")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
