from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.agent.budget import summarize_wishlist
from src.storage import Account, Transaction
from src.web.app import create_app, get_db, get_pluggy
from src.web.repositories import budget_repo, profile_repo


@pytest.fixture
def client(tmp_db, monkeypatch):
    monkeypatch.setattr("src.web.app._background_sync", lambda *a, **kw: None)
    monkeypatch.setattr(
        "src.web.repositories.profile_repo.settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        budget_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        "src.agent.maintenance.load_family_profile",
        lambda: {
            "metas": [
                {
                    "nome": "Reserva",
                    "valor_alvo": 6000,
                    "prazo_meses": 12,
                    "guardado": 1200,
                    "prioridade": 1,
                }
            ],
            "wishlist": [
                {
                    "nome": "Viagem",
                    "valor_alvo": 3000,
                    "prazo_meses": 6,
                    "guardado": 0,
                    "prioridade": 2,
                }
            ],
        },
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


def _set_income(db, value: float = 1000.0) -> None:
    profile_repo.update_profile(
        db,
        name="",
        email="",
        monthly_income=value,
        financial_month_start_day=1,
        goals_text="",
    )


def _seed_account(db) -> None:
    db.upsert_account(
        Account(id="savings-api-bank", source="test", name="Conta", type="CHECKING")
    )


def _insert_tx(
    db,
    external_id: str,
    *,
    amount: str = "-100.00",
    description: str = "Aporte meta",
    hidden: bool = False,
) -> Transaction:
    tx = Transaction(
        account_id="savings-api-bank",
        posted_at=date(2026, 6, 12),
        amount=Decimal(amount),
        description=description,
        raw_description=description,
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    db._conn.execute(
        "UPDATE transactions SET reference_month='2026-06', hidden=? WHERE id=?",
        (1 if hidden else 0, tx.id),
    )
    db._conn.commit()
    return tx


def test_savings_goals_seed_from_family_profile_and_return_summary(client, tmp_db):
    _set_income(tmp_db, 1000.0)

    response = client.get("/api/savings-goals?month=2026-06")

    assert response.status_code == 200
    body = response.json()
    assert [goal["name"] for goal in body["goals"]] == ["Reserva", "Viagem"]
    assert body["goals"][0]["target_amount"] == 6000.0
    assert body["goals"][0]["monthly_required"] == 400.0
    assert body["goals"][0]["progress_pct"] == 20.0
    assert body["goals"][0]["fits_surplus"] is True
    assert body["goals"][1]["monthly_required"] == 500.0
    assert body["total_monthly_required"] == 900.0
    assert body["monthly_surplus"] == 1000.0
    assert body["surplus_after_goals"] == 100.0

    assert client.get("/api/savings-goals?month=2026-06").json()["goals"] == body["goals"]


def test_savings_goal_crud_recalculates_summary(client, tmp_db):
    _set_income(tmp_db, 900.0)

    created = client.post(
        "/api/savings-goals",
        json={
            "name": "Notebook",
            "target_amount": 4800,
            "term_months": 12,
            "saved_amount": 1200,
            "priority": 3,
        },
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    updated = client.patch(
        f"/api/savings-goals/{goal_id}",
        json={"saved_amount": 2400, "priority": 1},
    )
    assert updated.status_code == 200
    assert updated.json()["saved_amount"] == 2400.0
    assert updated.json()["priority"] == 1

    body = client.get("/api/savings-goals?month=2026-06").json()
    direct = summarize_wishlist(
        [
            {
                "nome": "Notebook",
                "valor_alvo": 4800,
                "prazo_meses": 12,
                "guardado": 2400,
                "prioridade": 1,
            }
        ],
        sobra_mensal=900,
    )
    assert body["goals"][0]["name"] == "Notebook"
    assert body["goals"][0]["monthly_required"] == direct["itens"][0]["guardar_mes"]
    assert body["total_monthly_required"] == direct["total_guardar_mes"]

    deleted = client.delete(f"/api/savings-goals/{goal_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_id": goal_id, "unlinked": 0}
    assert client.get("/api/savings-goals?month=2026-06").json()["goals"] == []


def test_savings_goal_link_unlink_transactions_and_candidates(client, tmp_db):
    _set_income(tmp_db, 1000.0)
    _seed_account(tmp_db)
    goal_id = client.post(
        "/api/savings-goals",
        json={
            "name": "Viagem",
            "target_amount": 1000,
            "term_months": 4,
            "saved_amount": 100,
            "priority": 1,
        },
    ).json()["id"]
    linked = _insert_tx(tmp_db, "savings-api-link-1", amount="-250.00")
    hidden = _insert_tx(tmp_db, "savings-api-link-2", amount="-999.00", hidden=True)
    candidate = _insert_tx(
        tmp_db,
        "savings-api-candidate-1",
        amount="-150.00",
        description="Aporte candidato",
    )

    link_response = client.post(
        f"/api/savings-goals/{goal_id}/link",
        json={"transaction_ids": [linked.id, hidden.id]},
    )

    assert link_response.status_code == 200
    assert link_response.json() == {
        "goal_id": goal_id,
        "linked": 2,
        "transaction_ids": [linked.id, hidden.id],
    }
    refreshed = client.get("/api/savings-goals?month=2026-06").json()["goals"][0]
    assert refreshed["saved_manual"] == 100.0
    assert refreshed["saved_from_tx"] == 250.0
    assert refreshed["saved_total"] == 350.0
    assert refreshed["linked_count"] == 2

    linked_response = client.get(f"/api/savings-goals/{goal_id}/transactions")
    assert linked_response.status_code == 200
    assert linked_response.json()["saved_from_tx"] == 250.0
    assert {item["id"] for item in linked_response.json()["items"]} == {linked.id, hidden.id}

    candidates = client.get(f"/api/savings-goals/{goal_id}/candidates?month=2026-06")
    assert candidates.status_code == 200
    assert [item["id"] for item in candidates.json()["items"]] == [candidate.id]

    unlink_response = client.post(
        f"/api/savings-goals/{goal_id}/unlink",
        json={"transaction_ids": [hidden.id]},
    )

    assert unlink_response.status_code == 200
    assert unlink_response.json() == {
        "goal_id": goal_id,
        "unlinked": 1,
        "transaction_ids": [hidden.id],
    }
    assert client.get("/api/savings-goals?month=2026-06").json()["goals"][0][
        "linked_count"
    ] == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "target_amount": 100, "term_months": 12},
        {"name": "Inválida", "target_amount": 0, "term_months": 12},
        {"name": "Inválida", "target_amount": 100, "term_months": 0},
        {"name": "Inválida", "target_amount": 100, "term_months": 12, "saved_amount": -1},
    ],
)
def test_savings_goal_rejects_invalid_payload(client, payload):
    response = client.post("/api/savings-goals", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_savings_goal_returns_not_found_for_unknown_id(client):
    response = client.patch("/api/savings-goals/9999", json={"saved_amount": 10})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
