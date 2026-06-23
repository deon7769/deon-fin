from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.storage import Account, Transaction
from src.web.repositories import profile_repo, savings_repo


def _seed_account(db) -> None:
    db.upsert_account(
        Account(id="savings-link-bank", source="test", name="Conta", type="CHECKING")
    )


def _set_income(db, value: float = 1000.0) -> None:
    profile_repo.update_profile(
        db,
        name="",
        email="",
        monthly_income=value,
        financial_month_start_day=1,
        goals_text="",
    )


def _insert_tx(
    db,
    external_id: str,
    *,
    amount: str = "-250.00",
    description: str = "Aporte meta",
    hidden: bool = False,
) -> Transaction:
    tx = Transaction(
        account_id="savings-link-bank",
        posted_at=date(2026, 6, 10),
        amount=Decimal(amount),
        description=description,
        raw_description=description,
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    if hidden:
        db._conn.execute("UPDATE transactions SET hidden=1 WHERE id=?", (tx.id,))
        db._conn.commit()
    return tx


def test_goal_saved_total_uses_manual_baseline_plus_linked_transactions(tmp_db, monkeypatch):
    monkeypatch.setattr("src.agent.maintenance.load_family_profile", lambda: {})
    _seed_account(tmp_db)
    _set_income(tmp_db, 1000.0)
    goal = savings_repo.create_goal(
        tmp_db,
        name="Viagem",
        target_amount=3000,
        term_months=6,
        saved_amount=500,
        priority=1,
    )
    tx = _insert_tx(tmp_db, "savings-link-1", amount="-250.00")

    result = savings_repo.link_transactions(tmp_db, goal["id"], [tx.id])

    refreshed = savings_repo.get_goal(tmp_db, goal["id"])
    summary = savings_repo.list_with_summary(tmp_db, "2026-06")
    assert result == {"goal_id": goal["id"], "linked": 1, "transaction_ids": [tx.id]}
    assert refreshed["saved_manual"] == 500.0
    assert refreshed["saved_from_tx"] == 250.0
    assert refreshed["saved_total"] == 750.0
    assert refreshed["linked_count"] == 1
    assert refreshed["saved_amount"] == 500.0
    assert summary["goals"][0]["saved_total"] == 750.0
    assert summary["goals"][0]["monthly_required"] == 375.0
    assert summary["goals"][0]["progress_pct"] == 25.0


def test_goal_saved_total_ignores_hidden_linked_transactions(tmp_db, monkeypatch):
    monkeypatch.setattr("src.agent.maintenance.load_family_profile", lambda: {})
    _seed_account(tmp_db)
    goal = savings_repo.create_goal(
        tmp_db,
        name="Reserva",
        target_amount=2000,
        term_months=4,
        saved_amount=100,
    )
    visible = _insert_tx(tmp_db, "savings-hidden-1", amount="-300.00")
    hidden = _insert_tx(tmp_db, "savings-hidden-2", amount="-900.00", hidden=True)

    savings_repo.link_transactions(tmp_db, goal["id"], [visible.id, hidden.id])

    refreshed = savings_repo.get_goal(tmp_db, goal["id"])
    assert refreshed["saved_from_tx"] == 300.0
    assert refreshed["saved_total"] == 400.0
    assert refreshed["linked_count"] == 2


def test_linking_transaction_to_another_goal_moves_contribution(tmp_db, monkeypatch):
    monkeypatch.setattr("src.agent.maintenance.load_family_profile", lambda: {})
    _seed_account(tmp_db)
    first = savings_repo.create_goal(
        tmp_db,
        name="Viagem",
        target_amount=3000,
        term_months=6,
    )
    second = savings_repo.create_goal(
        tmp_db,
        name="Notebook",
        target_amount=4000,
        term_months=8,
    )
    tx = _insert_tx(tmp_db, "savings-move-1", amount="-700.00")

    savings_repo.link_transactions(tmp_db, first["id"], [tx.id])
    savings_repo.link_transactions(tmp_db, second["id"], [tx.id])

    assert savings_repo.get_goal(tmp_db, first["id"])["saved_from_tx"] == 0.0
    assert savings_repo.get_goal(tmp_db, second["id"])["saved_from_tx"] == 700.0
    row = tmp_db._conn.execute(
        "SELECT savings_goal_id FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()
    assert row["savings_goal_id"] == second["id"]


def test_unlink_and_delete_goal_clear_transaction_links(tmp_db, monkeypatch):
    monkeypatch.setattr("src.agent.maintenance.load_family_profile", lambda: {})
    _seed_account(tmp_db)
    goal = savings_repo.create_goal(
        tmp_db,
        name="Reserva",
        target_amount=2000,
        term_months=4,
    )
    keep = _insert_tx(tmp_db, "savings-clear-1", amount="-100.00")
    remove = _insert_tx(tmp_db, "savings-clear-2", amount="-200.00")
    savings_repo.link_transactions(tmp_db, goal["id"], [keep.id, remove.id])

    result = savings_repo.unlink_transactions(tmp_db, goal["id"], [remove.id])

    assert result == {"goal_id": goal["id"], "unlinked": 1, "transaction_ids": [remove.id]}
    assert savings_repo.get_goal(tmp_db, goal["id"])["saved_from_tx"] == 100.0

    deleted = savings_repo.delete_goal(tmp_db, goal["id"])

    assert deleted == {"deleted_id": goal["id"], "unlinked": 1}
    rows = tmp_db._conn.execute(
        "SELECT id, savings_goal_id FROM transactions ORDER BY external_id"
    ).fetchall()
    assert [(row["id"], row["savings_goal_id"]) for row in rows] == [
        (keep.id, None),
        (remove.id, None),
    ]
