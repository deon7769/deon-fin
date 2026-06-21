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
    monkeypatch.setattr("src.agent.maintenance.load_family_profile", lambda: None)
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
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


def _seed_account(db) -> None:
    db.upsert_account(
        Account(
            id="plan-bank",
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
    amount: str,
    bucket_id: int | None,
    category: str = "Mercado",
) -> Transaction:
    tx = Transaction(
        account_id="plan-bank",
        posted_at=date(2026, 6, 15),
        amount=Decimal(amount),
        description=external_id,
        raw_description=external_id.upper(),
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
               bucket_source=?
         WHERE id=?
        """,
        (
            reference_month(tx.posted_at, 1),
            bucket_id,
            "manual" if bucket_id is not None else None,
            tx.id,
        ),
    )
    db._conn.commit()
    return tx


def _bucket_by_key(db, key: str) -> dict[str, Any]:
    buckets_repo.seed_buckets(db)
    return next(bucket for bucket in buckets_repo.list_buckets(db) if bucket["key"] == key)


def test_bucket_plan_reuses_budget_math_and_reports_percent_warning(client, tmp_db):
    _seed_account(tmp_db)
    profile_repo.update_profile(
        tmp_db,
        name="",
        email="",
        monthly_income=1000.0,
        financial_month_start_day=1,
        goals_text="",
    )
    fixed = _bucket_by_key(tmp_db, "custos_fixos")
    pleasures = _bucket_by_key(tmp_db, "prazeres")
    tmp_db._conn.execute(
        "UPDATE budget_buckets SET planned_kind='amount', planned_value=300 WHERE id=?",
        (pleasures["id"],),
    )
    tmp_db._conn.commit()
    _insert_tx(tmp_db, external_id="plan-rent", amount="-125.50", bucket_id=fixed["id"])

    response = client.get("/api/buckets/plan?month=2026-06")

    assert response.status_code == 200
    body = response.json()
    assert body["income"] == 1000.0
    assert body["income_source"] == "profile"
    assert body["sum_percent"] == 90.0
    assert body["sum_amount"] == 1200.0
    assert body["warning"]["code"] == "percent_total_mismatch"
    assert len(body["buckets"]) == 6

    categories = {
        item["id"]: item
        for item in budget_repo.budget_for_month(tmp_db, "2026-06")["categories"]
    }
    planned = {item["id"]: item for item in body["buckets"]}
    assert planned[fixed["id"]]["planned_amount"] == categories[fixed["id"]]["planned"]
    assert planned[fixed["id"]]["spent_month"] == 125.5
    assert planned[pleasures["id"]]["planned_kind"] == "amount"
    assert planned[pleasures["id"]]["planned_amount"] == 300.0


def test_patch_bucket_plan_fields_and_sort_order(client, tmp_db):
    bucket = _bucket_by_key(tmp_db, "conforto")

    update = client.patch(
        f"/api/buckets/{bucket['id']}",
        json={
            "name": "Conforto ajustado",
            "color": "#123ABC",
            "planned_kind": "amount",
            "planned_value": 250.45,
        },
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Conforto ajustado"
    assert update.json()["color"] == "#123ABC"
    assert update.json()["planned_kind"] == "amount"
    assert update.json()["planned_value"] == 250.45

    current = client.get("/api/buckets").json()["items"]
    order = [item["id"] for item in reversed(current)]
    sort = client.patch("/api/buckets/sort", json={"order": order})

    assert sort.status_code == 200
    assert sort.json()["updated"] == len(order)
    assert [item["id"] for item in client.get("/api/buckets").json()["items"]] == order


@pytest.mark.parametrize(
    "payload",
    [
        {"planned_kind": "weekly"},
        {"planned_kind": "percent", "planned_value": 120},
        {"planned_kind": "amount", "planned_value": -1},
        {"color": "red"},
    ],
)
def test_patch_bucket_rejects_invalid_plan_payload(client, tmp_db, payload):
    bucket = _bucket_by_key(tmp_db, "metas")

    response = client.patch(f"/api/buckets/{bucket['id']}", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_patch_bucket_returns_not_found_for_unknown_bucket(client):
    response = client.patch("/api/buckets/9999", json={"planned_value": 10})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

