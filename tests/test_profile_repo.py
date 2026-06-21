from __future__ import annotations

from types import SimpleNamespace

from src.web.repositories import profile_repo


def test_get_or_create_profile_seeds_from_legacy_settings(tmp_db, monkeypatch):
    monkeypatch.setattr(
        profile_repo,
        "settings",
        SimpleNamespace(monthly_income=4321.5, financial_goals=["Reserva", "Casa"]),
    )
    monkeypatch.setattr(profile_repo.mnt, "load_family_profile", lambda: None)

    profile = profile_repo.get_or_create_profile(tmp_db)

    assert profile["id"] == 1
    assert profile["name"] == ""
    assert profile["email"] == ""
    assert profile["monthly_income"] == 4321.5
    assert profile["financial_month_start_day"] == 1
    assert profile["goals_text"] == "Reserva, Casa"
    assert profile["initials"] == "?"


def test_get_or_create_profile_uses_family_income_when_settings_empty(tmp_db, monkeypatch):
    monkeypatch.setattr(
        profile_repo,
        "settings",
        SimpleNamespace(monthly_income=None, financial_goals=[]),
    )
    monkeypatch.setattr(
        profile_repo.mnt,
        "load_family_profile",
        lambda: {"receitas": [{"valor": 1000}, {"valor": 250.75}]},
    )

    profile = profile_repo.get_or_create_profile(tmp_db)

    assert profile["monthly_income"] == 1250.75
    assert profile["goals_text"] == ""


def test_get_or_create_profile_is_idempotent(tmp_db, monkeypatch):
    monkeypatch.setattr(
        profile_repo,
        "settings",
        SimpleNamespace(monthly_income=1000.0, financial_goals=["Primeiro"]),
    )
    monkeypatch.setattr(profile_repo.mnt, "load_family_profile", lambda: None)

    first = profile_repo.get_or_create_profile(tmp_db)
    monkeypatch.setattr(
        profile_repo,
        "settings",
        SimpleNamespace(monthly_income=9999.0, financial_goals=["Segundo"]),
    )
    second = profile_repo.get_or_create_profile(tmp_db)

    assert first == second
    assert second["monthly_income"] == 1000.0
    assert second["goals_text"] == "Primeiro"
    assert tmp_db._conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0] == 1


def test_update_profile_upserts_singleton_and_updates_initials(tmp_db):
    profile = profile_repo.update_profile(
        tmp_db,
        name="Davi Alves",
        email="davi@example.com",
        monthly_income=10490.41,
        financial_month_start_day=15,
        goals_text="Quitar financiamento",
    )

    assert profile["id"] == 1
    assert profile["name"] == "Davi Alves"
    assert profile["email"] == "davi@example.com"
    assert profile["monthly_income"] == 10490.41
    assert profile["financial_month_start_day"] == 15
    assert profile["goals_text"] == "Quitar financiamento"
    assert profile["initials"] == "DA"
    assert profile["updated_at"] is not None


def test_initials_for_handles_blank_single_and_multi_word_names():
    assert profile_repo.initials_for("") == "?"
    assert profile_repo.initials_for(None) == "?"
    assert profile_repo.initials_for("Davi") == "D"
    assert profile_repo.initials_for("Davi Alves") == "DA"
    assert profile_repo.initials_for("  maria   da silva ") == "MD"
