from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.agent.cards import card_monthly_breakdown
from src.storage import Account, Transaction
from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import buckets_repo, invoices_repo, profile_repo, tags_repo


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
    monkeypatch.setattr("src.web.app.mnt.load_family_profile", lambda: None)
    monkeypatch.setattr("src.web.app.mnt.load_overrides", lambda: {"categorias_pt": {}, "recorrencias": {}})

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
            id="invoice-card",
            source="test",
            institution="Banco Teste",
            name="Cartao Black",
            type="CREDIT",
            metadata={"brand": "Visa", "number": "**** **** **** 1234"},
        )
    )
    db.upsert_account(
        Account(
            id="invoice-card-2",
            source="test",
            institution="Banco Teste",
            name="Cartao Platinum",
            type="CREDIT_CARD",
        )
    )
    db.upsert_account(
        Account(
            id="invoice-bank",
            source="test",
            institution="Banco Teste",
            name="Conta Corrente",
            type="CHECKING",
        )
    )


def _insert_tx(
    db,
    *,
    external_id: str,
    account_id: str = "invoice-card",
    posted_at: date = date(2026, 6, 15),
    amount: str = "10.00",
    description: str = "Compra teste",
    category: str | None = "Mercado",
    reference_month_value: str = "2026-06",
    bucket_id: int | None = None,
    tag_id: int | None = None,
    metadata: dict[str, Any] | None = None,
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
        metadata=metadata or {},
    )
    db.insert_transactions([tx])
    db._conn.execute(
        """
        UPDATE transactions
           SET reference_month=?,
               bucket_id=?,
               bucket_source=?,
               tag_id=?
         WHERE id=?
        """,
        (
            reference_month_value,
            bucket_id,
            "manual" if bucket_id is not None else None,
            tag_id,
            tx.id,
        ),
    )
    db._conn.commit()
    return tx


def _bucket_by_key(db, key: str) -> dict[str, Any]:
    buckets_repo.seed_buckets(db)
    return next(bucket for bucket in buckets_repo.list_buckets(db) if bucket["key"] == key)


def _tag_by_name(db, name: str) -> dict[str, Any]:
    tags_repo.seed_tags(db)
    return next(tag for tag in tags_repo.list_tags(db) if tag["name"] == name)


def test_is_purchase_matches_cards_predicate():
    assert invoices_repo._is_purchase(50, "Restaurante") is True
    assert invoices_repo._is_purchase(-30, "Restaurante") is False
    assert invoices_repo._is_purchase(200, "Pagamento de fatura") is False
    assert invoices_repo._is_purchase(200, "Transferência - PIX") is False


def test_parse_installment_prefers_structured_metadata_and_safe_text_patterns():
    assert invoices_repo._parse_installment("MAGAZINELUIZA PARC 03/10") == {"n": 3, "of": 10}
    assert invoices_repo._parse_installment("LOJA PARCELA 3 DE 10") == {"n": 3, "of": 10}
    assert invoices_repo._parse_installment("COMPRA 50/49") is None
    assert invoices_repo._parse_installment("03/10") is None
    assert invoices_repo._parse_installment("IFOOD") is None
    assert invoices_repo._parse_installment(
        "QUALQUER TEXTO",
        {"installmentNumber": 4, "totalInstallments": 12},
    ) == {"n": 4, "of": 12}


def test_invoice_dates_are_derived_from_reference_month(monkeypatch):
    monkeypatch.setattr(invoices_repo, "_today", lambda: date(2026, 7, 2))

    assert invoices_repo._invoice_dates_and_status("2026-06", 1) == {
        "closing_date": "2026-06-30",
        "due_date": "2026-07-07",
        "paid": True,
        "approximate_dates": True,
    }
    assert invoices_repo._invoice_dates_and_status("2026-07", 15) == {
        "closing_date": "2026-08-14",
        "due_date": "2026-08-21",
        "paid": False,
        "approximate_dates": True,
    }


def test_cards_list_only_credit_cards_and_degrade(tmp_db):
    _seed_accounts(tmp_db)

    cards = invoices_repo.list_cards(tmp_db)
    by_id = {card["id"]: card for card in cards}

    assert set(by_id) == {"invoice-card", "invoice-card-2"}
    assert by_id["invoice-card"]["name"] == "Cartao Black"
    assert by_id["invoice-card"]["brand"] == "Visa"
    assert by_id["invoice-card"]["last4"] == "1234"
    assert by_id["invoice-card"]["credit_limit"] is None
    assert by_id["invoice-card"]["available"] is None
    assert by_id["invoice-card-2"]["brand"] is None
    assert by_id["invoice-card-2"]["last4"] is None


def test_cards_enrich_from_balances(tmp_db):
    _seed_accounts(tmp_db)
    tmp_db._conn.execute(
        """
        INSERT INTO account_balances (account_id, credit_limit, available)
        VALUES ('invoice-card', 10000.0, 7250.25)
        """
    )
    tmp_db._conn.commit()

    card = next(item for item in invoices_repo.list_cards(tmp_db) if item["id"] == "invoice-card")

    assert card["credit_limit"] == 10000.0
    assert card["available"] == 7250.25


def test_invoice_items_are_purchases_only_and_include_bucket_tag_category(tmp_db):
    _seed_accounts(tmp_db)
    fixed = _bucket_by_key(tmp_db, "custos_fixos")
    tag = _tag_by_name(tmp_db, "Alimentação")
    first = _insert_tx(
        tmp_db,
        external_id="invoice-market",
        posted_at=date(2026, 6, 14),
        amount="120.00",
        description="Mercado",
        category="Mercado",
        bucket_id=fixed["id"],
        tag_id=tag["id"],
    )
    second = _insert_tx(
        tmp_db,
        external_id="invoice-parc",
        posted_at=date(2026, 6, 15),
        amount="300.00",
        description="MAGAZINELUIZA PARC 03/10",
        category="Eletronicos",
        bucket_id=fixed["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="invoice-payment",
        amount="-300.00",
        description="Pagamento fatura",
        category="Pagamento de fatura",
    )
    _insert_tx(
        tmp_db,
        external_id="invoice-refund",
        amount="-50.00",
        description="Estorno",
        category="Mercado",
    )
    _insert_tx(
        tmp_db,
        external_id="invoice-bank",
        account_id="invoice-bank",
        amount="-500.00",
        description="Debito banco",
        category="Mercado",
    )
    _insert_tx(
        tmp_db,
        external_id="invoice-other-month",
        posted_at=date(2026, 5, 15),
        amount="999.00",
        description="Outro mes",
        category="Mercado",
        reference_month_value="2026-05",
    )

    result = invoices_repo.get_invoice(tmp_db, account_id="invoice-card", month="2026-06")
    assert result is not None

    assert result["invoice"]["account_id"] == "invoice-card"
    assert result["invoice"]["reference_month"] == "2026-06"
    assert result["invoice"]["total"] == 420.0
    assert result["invoice"]["count"] == 2
    assert [item["id"] for item in result["items"]] == [second.id, first.id]
    assert result["items"][0]["installment"] == {"n": 3, "of": 10}
    assert result["items"][1]["bucket"] == {
        "id": fixed["id"],
        "name": fixed["name"],
        "color": fixed["color"],
    }
    assert result["items"][1]["tag"] == {
        "id": tag["id"],
        "name": tag["name"],
        "color": tag["color"],
    }
    assert result["by_category"] == [
        {"name": "Eletronicos", "color": fixed["color"], "total": 300.0},
        {"name": "Mercado", "color": fixed["color"], "total": 120.0},
    ]


def test_invoice_total_matches_legacy_card_breakdown(tmp_db):
    _seed_accounts(tmp_db)
    _insert_tx(
        tmp_db,
        external_id="invoice-match-a",
        amount="100.00",
        description="Compra A",
        category="Mercado",
    )
    _insert_tx(
        tmp_db,
        external_id="invoice-match-b",
        amount="25.50",
        description="Compra B",
        category="Lazer",
    )
    _insert_tx(
        tmp_db,
        external_id="invoice-match-other-card",
        account_id="invoice-card-2",
        amount="999.00",
        description="Outro cartao",
        category="Lazer",
    )

    invoice = invoices_repo.get_invoice(tmp_db, account_id="invoice-card", month="2026-06")
    legacy = card_monthly_breakdown(tmp_db, today=date(2026, 6, 20))
    month = next(item for item in legacy["meses"] if item["mes"] == "2026-06")
    card_slice = next(item for item in month["por_cartao"] if item["cartao"] == "Cartao Black")

    assert invoice is not None
    assert invoice["invoice"]["total"] == card_slice["total"] == 125.5


def test_invoice_validation_empty_and_legacy_shape(client, tmp_db):
    _seed_accounts(tmp_db)

    missing = client.get("/api/invoices")
    invalid_month = client.get("/api/invoices?account_id=invoice-card&month=2026-13")
    not_card = client.get("/api/invoices?account_id=invoice-bank&month=2026-06")
    empty = client.get("/api/invoices?account_id=invoice-card&month=2027-01")
    cards = client.get("/api/cards")
    legacy = client.get("/api/cartao")

    assert missing.status_code == 422
    assert invalid_month.status_code == 422
    assert not_card.status_code == 404
    assert empty.status_code == 200
    assert empty.json()["invoice"]["total"] == 0.0
    assert empty.json()["items"] == []
    assert empty.json()["by_category"] == []
    assert cards.status_code == 200
    assert {item["id"] for item in cards.json()["items"]} == {"invoice-card", "invoice-card-2"}
    assert legacy.status_code == 200
    assert {"meses", "indice_atual", "resumo", "top_comerciantes", "alertas"} == set(legacy.json())
