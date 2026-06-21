from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.storage import Account, Transaction
from src.web.repositories import tags_repo


def _seed_account(db) -> None:
    db.upsert_account(Account(id="acc-tags", source="test", type="CHECKING"))


def _insert_tx(db, external_id: str, *, description: str = "Compra teste") -> Transaction:
    tx = Transaction(
        account_id="acc-tags",
        posted_at=date(2026, 6, 20),
        amount=Decimal("-10.00"),
        description=description,
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    return tx


def test_seed_tags_idempotent_and_non_destructive(tmp_db):
    assert tags_repo.seed_tags(tmp_db) == 7
    assert tags_repo.seed_tags(tmp_db) == 0

    items = tags_repo.list_tags(tmp_db)
    assert [item["name"] for item in items] == [
        "Alimentação",
        "Conforto",
        "Educação",
        "Lazer",
        "Saúde",
        "Transporte",
        "Vestuário",
    ]
    assert {item["name"]: item["color"] for item in items} == {
        "Alimentação": "#F5B301",
        "Conforto": "#EF4444",
        "Educação": "#38BDF8",
        "Lazer": "#9F1239",
        "Saúde": "#3B82F6",
        "Transporte": "#F97316",
        "Vestuário": "#A855F7",
    }

    saude_id = next(item["id"] for item in items if item["name"] == "Saúde")
    tmp_db._conn.execute("UPDATE tags SET color='#111111' WHERE id=?", (saude_id,))
    tmp_db._conn.commit()

    assert tags_repo.seed_tags(tmp_db) == 0
    assert tags_repo.get_tag(tmp_db, saude_id)["color"] == "#111111"


def test_normalize_color_accepts_hex_and_rejects_other_formats():
    assert tags_repo.normalize_color("#fff") == "#fff"
    assert tags_repo.normalize_color("#FFFFFF") == "#ffffff"
    assert tags_repo.normalize_color("  #F5B301  ") == "#f5b301"
    assert tags_repo.normalize_color(None) is None
    assert tags_repo.normalize_color("") is None

    for value in ["red", "#12", "ff0000", "#1234", "rgb(1,2,3)"]:
        with pytest.raises(ValueError):
            tags_repo.normalize_color(value)


def test_normalize_name_trims_collapses_spaces_and_enforces_limit():
    assert tags_repo.normalize_name("  Saúde   e   Bem-estar  ") == "Saúde e Bem-estar"

    for value in ["", "   "]:
        with pytest.raises(ValueError):
            tags_repo.normalize_name(value)

    with pytest.raises(ValueError):
        tags_repo.normalize_name("x" * 41)


def test_name_taken_is_case_insensitive_and_can_ignore_current_id(tmp_db):
    tag = tags_repo.create_tag(tmp_db, name="Saúde", color="#3B82F6")

    assert tags_repo.name_taken(tmp_db, "saúde")
    assert tags_repo.name_taken(tmp_db, "SAÚDE")
    assert not tags_repo.name_taken(tmp_db, "saúde", exclude_id=tag["id"])


def test_create_tag_normalizes_values_and_rejects_duplicate_names(tmp_db):
    tag = tags_repo.create_tag(tmp_db, name="  Pets  ", color="#10B981")

    assert tag["name"] == "Pets"
    assert tag["color"] == "#10b981"
    assert tag["tx_count"] == 0

    with pytest.raises(ValueError, match="duplicate"):
        tags_repo.create_tag(tmp_db, name="pets", color=None)


def test_update_tag_partial_and_conflict_rules(tmp_db):
    first = tags_repo.create_tag(tmp_db, name="Saúde", color="#3B82F6")
    tags_repo.create_tag(tmp_db, name="Lazer", color="#9F1239")

    renamed = tags_repo.update_tag(tmp_db, first["id"], name=" Saúde e Bem-estar ")
    assert renamed["name"] == "Saúde e Bem-estar"
    assert renamed["color"] == "#3b82f6"

    recolored = tags_repo.update_tag(tmp_db, first["id"], color="#22C55E")
    assert recolored["name"] == "Saúde e Bem-estar"
    assert recolored["color"] == "#22c55e"

    cleared = tags_repo.update_tag(tmp_db, first["id"], color=None)
    assert cleared["color"] is None

    same_name = tags_repo.update_tag(tmp_db, first["id"], name="saúde e bem-estar")
    assert same_name["name"] == "saúde e bem-estar"

    with pytest.raises(ValueError, match="duplicate"):
        tags_repo.update_tag(tmp_db, first["id"], name="lazer")

    assert tags_repo.update_tag(tmp_db, 9999, name="Nada") is None


def test_delete_tag_unlinks_transactions_without_deleting_them(tmp_db):
    _seed_account(tmp_db)
    tag = tags_repo.create_tag(tmp_db, name="Pets", color="#10B981")
    tagged_a = _insert_tx(tmp_db, "tags-delete-1")
    tagged_b = _insert_tx(tmp_db, "tags-delete-2")
    untouched = _insert_tx(tmp_db, "tags-delete-3")
    tmp_db._conn.execute("UPDATE transactions SET tag_id=? WHERE id=?", (tag["id"], tagged_a.id))
    tmp_db._conn.execute("UPDATE transactions SET tag_id=? WHERE id=?", (tag["id"], tagged_b.id))
    tmp_db._conn.commit()

    result = tags_repo.delete_tag(tmp_db, tag["id"])

    assert result == {"deleted_id": tag["id"], "untagged": 2}
    assert tmp_db.count_transactions() == 3
    rows = tmp_db._conn.execute(
        "SELECT id, tag_id FROM transactions ORDER BY external_id"
    ).fetchall()
    assert [(row["id"], row["tag_id"]) for row in rows] == [
        (tagged_a.id, None),
        (tagged_b.id, None),
        (untouched.id, None),
    ]
    assert tags_repo.get_tag(tmp_db, tag["id"]) is None


def test_delete_tag_not_found_returns_none(tmp_db):
    assert tags_repo.delete_tag(tmp_db, 9999) is None


def test_list_tags_reports_tx_count_and_sorts_case_insensitive(tmp_db):
    _seed_account(tmp_db)
    viagem = tags_repo.create_tag(tmp_db, name="Viagem", color="#38BDF8")
    pets = tags_repo.create_tag(tmp_db, name="pets", color=None)
    tx = _insert_tx(tmp_db, "tags-count-1")
    tmp_db._conn.execute("UPDATE transactions SET tag_id=? WHERE id=?", (viagem["id"], tx.id))
    tmp_db._conn.commit()

    rows = tags_repo.list_tags(tmp_db)

    assert [row["name"] for row in rows] == ["pets", "Viagem"]
    assert {row["id"]: row["tx_count"] for row in rows} == {
        pets["id"]: 0,
        viagem["id"]: 1,
    }
