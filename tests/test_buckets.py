from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.agent.buckets import apply_buckets_to_database, classify_bucket
from src.agent.categorizer import DEFAULT_RULES
from src.storage import Account, Transaction
from src.web.repositories import buckets_repo, transactions_repo


def _seed_account(db) -> None:
    db.upsert_account(Account(id="acc-1", source="test", type="CHECKING"))


def _insert_tx(
    db,
    *,
    amount: str = "-10.00",
    description: str = "IFOOD RESTAURANTE",
    raw_description: str | None = None,
    category: str | None = None,
) -> Transaction:
    tx = Transaction(
        account_id="acc-1",
        posted_at=date(2026, 6, 20),
        amount=Decimal(amount),
        description=description,
        raw_description=raw_description,
        category=category,
        source="test",
        external_id=f"tx-{db.count_transactions() + 1}",
    )
    db.insert_transactions([tx])
    return tx


def _bucket_by_key(db, key: str) -> dict:
    return next(bucket for bucket in buckets_repo.list_buckets(db) if bucket["key"] == key)


def _tx_bucket_state(db, tx_id: str) -> tuple[int | None, str | None]:
    row = db._conn.execute(
        "SELECT bucket_id, bucket_source FROM transactions WHERE id=?",
        (tx_id,),
    ).fetchone()
    return row["bucket_id"], row["bucket_source"]


def test_seed_buckets_idempotent_and_non_destructive(tmp_db):
    assert buckets_repo.seed_buckets(tmp_db) == 6
    assert buckets_repo.seed_buckets(tmp_db) == 0

    rows = buckets_repo.list_buckets(tmp_db)
    assert [row["key"] for row in rows] == [
        "liberdade_financeira",
        "custos_fixos",
        "conforto",
        "metas",
        "prazeres",
        "conhecimento",
    ]
    assert rows[0]["planned_kind"] == "percent"
    assert sum(float(row["planned_value"]) for row in rows) == 100.0

    tmp_db._conn.execute(
        "UPDATE budget_buckets SET planned_value=12.5 WHERE key='conforto'"
    )
    tmp_db._conn.commit()

    assert buckets_repo.seed_buckets(tmp_db) == 0
    assert _bucket_by_key(tmp_db, "conforto")["planned_value"] == 12.5


def test_classify_bucket_covers_default_rules():
    expected = {
        "Alimentação - Restaurante": "conforto",
        "Alimentação - Mercado": "conforto",
        "Transporte - App": "custos_fixos",
        "Transporte - Combustível": "custos_fixos",
        "Transporte - Estacionamento": "custos_fixos",
        "Assinaturas - Streaming": "prazeres",
        "Assinaturas - Software": "conhecimento",
        "Moradia - Aluguel": "custos_fixos",
        "Moradia - Contas": "custos_fixos",
        "Saúde - Farmácia": "conforto",
        "Saúde - Plano/Consulta": "custos_fixos",
        "Lazer - Cinema/Show": "prazeres",
        "Compras - E-commerce": "prazeres",
        "Educação": "conhecimento",
        "Transferências - PIX": None,
        "Transferências - TED/DOC": None,
        "Tarifas Bancárias": None,
        "Renda - Salário": None,
        "Investimentos": "liberdade_financeira",
    }

    categories = {rule.category for rule in DEFAULT_RULES}
    assert categories == set(expected)
    assert {category: classify_bucket(category) for category in categories} == expected


def test_apply_buckets_assigns_by_default_map(tmp_db):
    _seed_account(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    mercado = _insert_tx(tmp_db, category="Alimentação - Mercado")
    pix = _insert_tx(tmp_db, description="PIX recebido", category="Transferências - PIX")

    stats = apply_buckets_to_database(tmp_db)

    assert stats["by_map"] == 1
    assert stats["unmatched"] == 1
    assert _tx_bucket_state(tmp_db, mercado.id) == (
        _bucket_by_key(tmp_db, "conforto")["id"],
        "auto",
    )
    assert _tx_bucket_state(tmp_db, pix.id) == (None, None)


def test_apply_buckets_does_not_overwrite_manual(tmp_db):
    _seed_account(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    tx = _insert_tx(tmp_db, category="Alimentação - Mercado")
    prazer = _bucket_by_key(tmp_db, "prazeres")
    tmp_db._conn.execute(
        "UPDATE transactions SET bucket_id=?, bucket_source='manual' WHERE id=?",
        (prazer["id"], tx.id),
    )
    tmp_db._conn.commit()

    stats = apply_buckets_to_database(tmp_db)

    assert stats["skipped_manual"] == 1
    assert _tx_bucket_state(tmp_db, tx.id) == (prazer["id"], "manual")


def test_set_bucket_propagates_to_similar_transactions(tmp_db):
    _seed_account(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    conforto = _bucket_by_key(tmp_db, "conforto")
    target = _insert_tx(tmp_db, description="IFOOD RESTAURANTE")
    similar_a = _insert_tx(tmp_db, description="IFOOD RESTAURANTE")
    similar_b = _insert_tx(tmp_db, description="IFOOD RESTAURANTE")
    already_set = _insert_tx(tmp_db, description="IFOOD RESTAURANTE")
    tmp_db._conn.execute(
        "UPDATE transactions SET bucket_id=?, bucket_source='auto' WHERE id=?",
        (_bucket_by_key(tmp_db, "prazeres")["id"], already_set.id),
    )
    tmp_db._conn.commit()

    result = transactions_repo.set_bucket(
        tmp_db,
        target.id,
        bucket_id=conforto["id"],
        apply_to_similar=True,
    )

    assert result["bucket_source"] == "manual"
    assert result["rule_upserted"] is True
    assert result["similar_affected"] == 2
    assert set(result["similar_ids"]) == {similar_a.id, similar_b.id}
    assert _tx_bucket_state(tmp_db, target.id) == (conforto["id"], "manual")
    assert _tx_bucket_state(tmp_db, similar_a.id) == (conforto["id"], "rule")
    assert _tx_bucket_state(tmp_db, similar_b.id) == (conforto["id"], "rule")
    assert _tx_bucket_state(tmp_db, already_set.id) == (
        _bucket_by_key(tmp_db, "prazeres")["id"],
        "auto",
    )


def test_set_bucket_respects_amount_sign(tmp_db):
    _seed_account(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    conforto = _bucket_by_key(tmp_db, "conforto")
    target = _insert_tx(tmp_db, amount="-20.00", description="IFOOD RESTAURANTE")
    refund = _insert_tx(tmp_db, amount="20.00", description="IFOOD RESTAURANTE")

    result = transactions_repo.set_bucket(
        tmp_db,
        target.id,
        bucket_id=conforto["id"],
        apply_to_similar=True,
    )

    assert result["similar_affected"] == 0
    assert _tx_bucket_state(tmp_db, refund.id) == (None, None)


def test_setting_no_bucket_removes_rule(tmp_db):
    _seed_account(tmp_db)
    buckets_repo.seed_buckets(tmp_db)
    conforto = _bucket_by_key(tmp_db, "conforto")
    target = _insert_tx(tmp_db, description="IFOOD RESTAURANTE")

    created = transactions_repo.set_bucket(
        tmp_db,
        target.id,
        bucket_id=conforto["id"],
        apply_to_similar=True,
    )
    assert created["rule_upserted"] is True
    assert len(buckets_repo.list_rules(tmp_db)) == 1

    removed = transactions_repo.set_bucket(
        tmp_db,
        target.id,
        bucket_id=None,
        apply_to_similar=True,
    )

    assert removed["bucket_id"] is None
    assert removed["rule_deleted"] is True
    assert buckets_repo.list_rules(tmp_db) == []
    assert _tx_bucket_state(tmp_db, target.id) == (None, "manual")
