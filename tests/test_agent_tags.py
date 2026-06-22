from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.agent.buckets import match_key_for
from src.agent.tags import apply_tags_to_database
from src.storage import Account, Transaction
from src.web.repositories import tags_repo


def _seed_account(db) -> None:
    db.upsert_account(Account(id="agent-tags-account", source="test", type="CHECKING"))


def _insert(
    db,
    *,
    external_id: str,
    description: str,
    amount: str = "-20.00",
    category: str | None = None,
) -> Transaction:
    tx = Transaction(
        account_id="agent-tags-account",
        posted_at=date(2026, 6, 20),
        amount=Decimal(amount),
        description=description,
        raw_description=description.upper(),
        category=category,
        source="test",
        external_id=external_id,
    )
    db.insert_transactions([tx])
    return tx


def _tag_by_name(db, name: str) -> dict:
    return next(tag for tag in tags_repo.list_tags(db) if tag["name"] == name)


def test_apply_tags_uses_rules_before_category_heuristics(tmp_db):
    _seed_account(tmp_db)
    tags_repo.seed_tags(tmp_db)
    software = tags_repo.create_tag(tmp_db, name="Software", color="#38BDF8")
    tx = _insert(
        tmp_db,
        external_id="agent-tags-rule-1",
        description="IFOOD CURSO",
        category="Food Delivery",
    )
    match_key = match_key_for("IFOOD CURSO", -20.0)
    tmp_db._conn.execute(
        "INSERT INTO tag_rules (match_key, tag_id) VALUES (?, ?)",
        (match_key, software["id"]),
    )
    tmp_db._conn.commit()

    stats = apply_tags_to_database(tmp_db)

    row = tmp_db._conn.execute(
        "SELECT tag_id, tag_source FROM transactions WHERE id=?",
        (tx.id,),
    ).fetchone()
    assert (row["tag_id"], row["tag_source"]) == (software["id"], "rule")
    assert stats["by_rule"] == 1
    assert stats["by_map"] == 0


def test_apply_tags_maps_known_category_and_merchant_without_overwriting_manual(tmp_db):
    _seed_account(tmp_db)
    tags_repo.seed_tags(tmp_db)
    mapped = _insert(
        tmp_db,
        external_id="agent-tags-map-1",
        description="IFOOD RESTAURANTE",
        category="Food Delivery",
    )
    manual = _insert(
        tmp_db,
        external_id="agent-tags-map-2",
        description="IFOOD RESTAURANTE",
        category="Food Delivery",
    )
    lazer = _tag_by_name(tmp_db, "Lazer")
    tmp_db._conn.execute(
        "UPDATE transactions SET tag_id=?, tag_source='manual' WHERE id=?",
        (lazer["id"], manual.id),
    )
    tmp_db._conn.commit()

    stats = apply_tags_to_database(tmp_db)

    alimentacao = _tag_by_name(tmp_db, "Alimentação")
    rows = {
        row["id"]: (row["tag_id"], row["tag_source"])
        for row in tmp_db._conn.execute("SELECT id, tag_id, tag_source FROM transactions")
    }
    assert rows[mapped.id] == (alimentacao["id"], "auto")
    assert rows[manual.id] == (lazer["id"], "manual")
    assert stats["by_map"] == 1
    assert stats["skipped_manual"] == 1


def test_apply_tags_keeps_credit_card_payments_untagged(tmp_db):
    _seed_account(tmp_db)
    payment = _insert(
        tmp_db,
        external_id="agent-tags-payment-1",
        description="Pagamento fatura",
        amount="-900.00",
        category="Credit card payment",
    )

    stats = apply_tags_to_database(tmp_db)

    row = tmp_db._conn.execute(
        "SELECT tag_id, tag_source FROM transactions WHERE id=?",
        (payment.id,),
    ).fetchone()
    assert (row["tag_id"], row["tag_source"]) == (None, None)
    assert stats["unmatched"] == 1
