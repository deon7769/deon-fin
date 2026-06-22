from __future__ import annotations

from src.storage import Account, Database
from src.web.repositories import system_totals_repo


def _seed_account(db: Database, *, account_id: str = "acc-1") -> None:
    db.upsert_account(
        Account(
            id=account_id,
            source="test",
            institution="Banco Teste",
            name="Conta Principal",
            type="CHECKING",
        )
    )


def test_list_system_totals_defaults_accounts_and_movements_included(tmp_db: Database):
    _seed_account(tmp_db)

    settings = system_totals_repo.list_settings(tmp_db)

    account = next(item for item in settings["accounts"] if item["id"] == "acc-1")
    assert account["include_balance"] is True
    assert account["include_transactions"] is True
    assert {item["key"] for item in settings["movements"]} >= {
        "income",
        "expense",
        "card_payment",
        "investment",
    }
    assert all(item["include_in_totals"] is True for item in settings["movements"])


def test_update_account_system_total_settings_persists(tmp_db: Database):
    _seed_account(tmp_db)

    system_totals_repo.update_account_settings(
        tmp_db,
        [
            {
                "account_id": "acc-1",
                "include_balance": False,
                "include_transactions": True,
            }
        ],
    )

    settings = system_totals_repo.list_settings(tmp_db)
    account = next(item for item in settings["accounts"] if item["id"] == "acc-1")
    assert account["include_balance"] is False
    assert account["include_transactions"] is True


def test_update_movement_system_total_settings_persists(tmp_db: Database):
    system_totals_repo.update_movement_settings(
        tmp_db,
        [{"movement_type": "investment", "include_in_totals": False}],
    )

    settings = system_totals_repo.list_settings(tmp_db)
    movement = next(item for item in settings["movements"] if item["key"] == "investment")
    assert movement["include_in_totals"] is False
