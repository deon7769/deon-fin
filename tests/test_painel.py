from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.agent.context import build_financial_context
from src.storage import Account, Transaction
from src.storage.reference_month import reference_month
from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import painel_repo, profile_repo, tags_repo


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


def _month_add(ym: str, delta: int) -> str:
    year, month = (int(part) for part in ym.split("-"))
    idx = year * 12 + (month - 1) + delta
    next_year, next_month = divmod(idx, 12)
    return f"{next_year:04d}-{next_month + 1:02d}"


def _date_for_month(ym: str, day: int = 15) -> date:
    year, month = (int(part) for part in ym.split("-"))
    return date(year, month, day)


def _seed_accounts(db) -> None:
    db.upsert_account(
        Account(
            id="painel-bank",
            source="test",
            institution="Banco Teste",
            name="Conta Corrente",
            type="CHECKING",
        )
    )
    db.upsert_account(
        Account(
            id="painel-card",
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
    account_id: str = "painel-bank",
    posted_at: date = date(2026, 6, 20),
    amount: str = "-10.00",
    description: str = "Compra Teste",
    category: str | None = "Mercado",
    reference_month_value: str = "2026-06",
    tag_id: int | None = None,
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
               tag_id=?,
               hidden=?
         WHERE id=?
        """,
        (reference_month_value, tag_id, 1 if hidden else 0, tx.id),
    )
    db._conn.commit()
    return tx


def _tag_by_name(db, name: str) -> dict[str, Any]:
    tags_repo.seed_tags(db)
    return next(tag for tag in tags_repo.list_tags(db) if tag["name"] == name)


def test_summary_signs(tmp_db):
    _seed_accounts(tmp_db)
    _insert_tx(
        tmp_db,
        external_id="summary-salary",
        amount="5400.00",
        description="Salario",
        category="Salario",
    )
    _insert_tx(
        tmp_db,
        external_id="summary-bank-expense",
        amount="-100.00",
        description="Mercado",
        category="Mercado",
    )
    _insert_tx(
        tmp_db,
        external_id="summary-card-purchase",
        account_id="painel-card",
        amount="200.00",
        description="Compra cartao",
        category="Lazer",
    )
    _insert_tx(
        tmp_db,
        external_id="summary-card-payment",
        amount="-300.00",
        description="Pagamento fatura",
        category="Pagamento de fatura",
    )
    _insert_tx(
        tmp_db,
        external_id="summary-transfer",
        amount="-1000.00",
        description="Transferencia",
        category="Transferência - PIX",
    )

    assert painel_repo.month_summary(tmp_db, "2026-06") == {
        "month": "2026-06",
        "result": 5100.0,
        "income": 5400.0,
        "expense": 300.0,
        "accounts_balance": 0.0,
        "accounts_balance_available": False,
    }


def test_summary_excludes_hidden(tmp_db):
    _seed_accounts(tmp_db)
    _insert_tx(
        tmp_db,
        external_id="hidden-bank-expense",
        amount="-100.00",
        description="Mercado",
        category="Mercado",
    )
    _insert_tx(
        tmp_db,
        external_id="hidden-card-purchase",
        account_id="painel-card",
        amount="200.00",
        description="Compra oculta",
        category="Lazer",
        hidden=True,
    )

    summary = painel_repo.month_summary(tmp_db, "2026-06")

    assert summary["expense"] == 100.0
    assert summary["result"] == -100.0


def test_summary_balance_unavailable_and_available(tmp_db):
    _seed_accounts(tmp_db)

    unavailable = painel_repo.month_summary(tmp_db, "2026-06")
    assert unavailable["accounts_balance"] == 0.0
    assert unavailable["accounts_balance_available"] is False

    tmp_db._conn.execute(
        """
        INSERT INTO account_balances (account_id, balance)
        VALUES ('painel-bank', 40.0), ('painel-card', 27.67)
        """
    )
    tmp_db._conn.commit()

    available = painel_repo.month_summary(tmp_db, "2026-06")
    assert available["accounts_balance"] == 67.67
    assert available["accounts_balance_available"] is True


def test_history_window_length(tmp_db):
    _seed_accounts(tmp_db)
    current_month = reference_month(date.today(), 1)
    previous_month = _month_add(current_month, -1)
    _insert_tx(
        tmp_db,
        external_id="history-current-income",
        posted_at=_date_for_month(current_month),
        amount="1000.00",
        description="Renda atual",
        category="Salario",
        reference_month_value=current_month,
    )
    _insert_tx(
        tmp_db,
        external_id="history-previous-expense",
        posted_at=_date_for_month(previous_month),
        amount="-50.00",
        description="Despesa anterior",
        category="Mercado",
        reference_month_value=previous_month,
    )

    rows = painel_repo.history(tmp_db, 6)

    assert len(rows) == 6
    assert [row["month"] for row in rows] == sorted(row["month"] for row in rows)
    assert rows[-1]["month"] == current_month
    assert {row["month"] for row in rows} == {
        _month_add(current_month, -delta) for delta in range(5, -1, -1)
    }
    assert next(row for row in rows if row["month"] == current_month)["income"] == 1000.0
    assert next(row for row in rows if row["month"] == previous_month)["expense"] == 50.0
    assert painel_repo.window_to_months("3m") == 3
    assert painel_repo.window_to_months("6M") == 6
    assert painel_repo.window_to_months("1a") == 12
    assert painel_repo.window_to_months("xx") == 6


def test_history_parity_with_fluxo_mensal(tmp_db):
    _seed_accounts(tmp_db)
    current_month = reference_month(date.today(), 1)
    previous_month = _month_add(current_month, -1)
    for idx, ym in enumerate([previous_month, current_month], start=1):
        _insert_tx(
            tmp_db,
            external_id=f"parity-income-{idx}",
            posted_at=_date_for_month(ym),
            amount="1200.00",
            description=f"Renda {ym}",
            category="Salario",
            reference_month_value=ym,
        )
        _insert_tx(
            tmp_db,
            external_id=f"parity-expense-{idx}",
            posted_at=_date_for_month(ym),
            amount="-80.00",
            description=f"Despesa {ym}",
            category="Mercado",
            reference_month_value=ym,
        )

    history_by_month = {row["month"]: row for row in painel_repo.history(tmp_db, 6)}
    fluxo_mensal = build_financial_context(
        tmp_db,
        today=date.today(),
        period_months=6,
        family_profile=None,
    ).to_dict()["fluxo_mensal"]

    for month, values in fluxo_mensal.items():
        assert history_by_month[month]["income"] == values["renda"]
        assert history_by_month[month]["expense"] == values["gasto"]


def test_by_tag_includes_sem_tags(tmp_db):
    _seed_accounts(tmp_db)
    tag = _tag_by_name(tmp_db, "Alimentação")
    _insert_tx(
        tmp_db,
        external_id="by-tag-tagged",
        amount="-100.00",
        description="Mercado tagged",
        category="Mercado",
        tag_id=tag["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="by-tag-untagged",
        amount="-50.00",
        description="Mercado sem tag",
        category="Mercado",
    )

    result = painel_repo.by_tag(tmp_db, "2026-06", "expense")
    items = {item["tag_id"]: item for item in result["items"]}

    assert result["month"] == "2026-06"
    assert result["type"] == "expense"
    assert result["total"] == 150.0
    assert items[tag["id"]]["tag_name"] == "Alimentação"
    assert items[tag["id"]]["color"] == tag["color"]
    assert items[tag["id"]]["total"] == 100.0
    assert items[None] == {
        "tag_id": None,
        "tag_name": "Sem Tags",
        "color": None,
        "total": 50.0,
    }


def test_by_tag_excludes_hidden_and_other_type(tmp_db):
    _seed_accounts(tmp_db)
    tag = _tag_by_name(tmp_db, "Conforto")
    _insert_tx(
        tmp_db,
        external_id="by-tag-hidden",
        amount="-999.00",
        description="Despesa oculta",
        category="Lazer",
        tag_id=tag["id"],
        hidden=True,
    )
    _insert_tx(
        tmp_db,
        external_id="by-tag-visible-expense",
        amount="-70.00",
        description="Despesa visivel",
        category="Lazer",
        tag_id=tag["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="by-tag-income",
        amount="500.00",
        description="Receita tagged",
        category="Salario",
        tag_id=tag["id"],
    )

    expense = painel_repo.by_tag(tmp_db, "2026-06", "expense")
    income = painel_repo.by_tag(tmp_db, "2026-06", "income")

    assert expense["total"] == 70.0
    assert expense["items"][0]["total"] == 70.0
    assert income["total"] == 500.0
    assert income["items"][0]["total"] == 500.0


def test_by_tag_applies_refunds_to_tag_total(tmp_db):
    _seed_accounts(tmp_db)
    tag = _tag_by_name(tmp_db, "Lazer")
    _insert_tx(
        tmp_db,
        external_id="by-tag-card-purchase",
        account_id="painel-card",
        amount="200.00",
        description="Compra cartao",
        category="Lazer",
        tag_id=tag["id"],
    )
    _insert_tx(
        tmp_db,
        external_id="by-tag-card-refund",
        account_id="painel-card",
        amount="-50.00",
        description="Estorno cartao",
        category="Lazer",
        tag_id=tag["id"],
    )

    summary = painel_repo.month_summary(tmp_db, "2026-06")
    result = painel_repo.by_tag(tmp_db, "2026-06", "expense")

    assert summary["expense"] == 150.0
    assert result["total"] == 150.0
    assert result["items"] == [
        {
            "tag_id": tag["id"],
            "tag_name": "Lazer",
            "color": tag["color"],
            "total": 150.0,
        }
    ]


def test_resolve_month(tmp_db):
    assert painel_repo.resolve_month(tmp_db, "2026-06") == "2026-06"
    assert painel_repo.resolve_month(tmp_db, "2026") is None
    assert painel_repo.resolve_month(tmp_db, "2026-13") is None
    assert painel_repo.resolve_month(tmp_db, None) == reference_month(date.today(), 1)

    profile_repo.update_profile(
        tmp_db,
        name="",
        email="",
        monthly_income=0.0,
        financial_month_start_day=10,
        goals_text="",
    )
    assert painel_repo.resolve_month(tmp_db, None) == reference_month(date.today(), 10)


def test_summary_endpoint_shape(client, tmp_db):
    _seed_accounts(tmp_db)
    _insert_tx(
        tmp_db,
        external_id="endpoint-summary",
        amount="100.00",
        description="Receita endpoint",
        category="Salario",
    )

    response = client.get("/api/painel/summary?month=2026-06")

    assert response.status_code == 200
    assert set(response.json()) == {
        "month",
        "result",
        "income",
        "expense",
        "accounts_balance",
        "accounts_balance_available",
    }
    assert response.json()["income"] == 100.0


def test_summary_endpoint_invalid_month(client):
    response = client.get("/api/painel/summary?month=2026")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_history_endpoint_default_6(client):
    response = client.get("/api/painel/history")

    assert response.status_code == 200
    assert len(response.json()) == 6


def test_history_endpoint_window_variants(client):
    assert len(client.get("/api/painel/history?window=3m").json()) == 3
    assert len(client.get("/api/painel/history?window=1a").json()) == 12
    assert len(client.get("/api/painel/history?window=banana").json()) == 6


def test_by_tag_endpoint_and_invalid_type(client, tmp_db):
    _seed_accounts(tmp_db)
    _insert_tx(
        tmp_db,
        external_id="endpoint-by-tag",
        amount="-25.00",
        description="Despesa sem tag endpoint",
        category="Mercado",
    )

    response = client.get("/api/painel/by-tag?month=2026-06&type=expense")
    invalid = client.get("/api/painel/by-tag?month=2026-06&type=banana")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"tag_id": None, "tag_name": "Sem Tags", "color": None, "total": 25.0}
    ]
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_legacy_dashboard_and_summary_untouched(client, tmp_db):
    _seed_accounts(tmp_db)
    _insert_tx(
        tmp_db,
        external_id="legacy-summary",
        posted_at=date.today(),
        amount="-30.00",
        description="Despesa legado",
        category="Mercado",
        reference_month_value=reference_month(date.today(), 1),
    )

    dashboard = client.get("/api/dashboard?meses=6")
    summary = client.get("/api/summary?days=30")

    assert dashboard.status_code == 200
    assert {"kpis", "fluxo_mensal", "gasto_por_categoria", "executivo"}.issubset(
        dashboard.json().keys()
    )
    assert summary.status_code == 200
    assert {"transactions", "inflow", "outflow", "net", "by_category"}.issubset(
        summary.json().keys()
    )
