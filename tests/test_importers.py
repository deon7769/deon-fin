from __future__ import annotations

from pathlib import Path

import pytest

from src.importers import import_nubank_csv, import_ofx

FIXTURES = Path(__file__).parent / "fixtures"


def test_import_ofx_inserts_and_dedups(tmp_db):
    r1 = import_ofx(FIXTURES / "sample.ofx", tmp_db)
    assert r1.total_read == 3
    assert r1.inserted == 3
    assert r1.skipped_duplicates == 0

    r2 = import_ofx(FIXTURES / "sample.ofx", tmp_db)
    assert r2.inserted == 0
    assert r2.skipped_duplicates == 3


def test_import_nubank_credit_preserves_purchase_signs(tmp_db):
    r = import_nubank_csv(FIXTURES / "nubank_credit.csv", tmp_db, kind="credit")
    assert r.total_read == 5

    rows = tmp_db.list_transactions(account_id="nubank:credit-card")
    assert len(rows) == 5
    amounts = sorted(round(float(row["amount"]), 2) for row in rows)
    assert amounts == [18.3, 42.5, 55.9, 89.9, 150.0]

    accounts = {row["id"]: row for row in tmp_db.list_accounts()}
    assert accounts["nubank:credit-card"]["type"] == "CREDIT"


def test_import_nubank_credit_preserves_negative_adjustments(tmp_path, tmp_db):
    csv_path = tmp_path / "nubank_credit_adjustment.csv"
    csv_path.write_text(
        "date,title,amount\n"
        "2026-05-01,Compra farmacia,25.00\n"
        "2026-05-02,Estorno farmacia,-10.00\n",
        encoding="utf-8",
    )

    r = import_nubank_csv(csv_path, tmp_db, kind="credit", account_id="nubank:test-card")
    assert r.total_read == 2

    rows = tmp_db.list_transactions(account_id="nubank:test-card")
    amounts = sorted(round(float(row["amount"]), 2) for row in rows)
    assert amounts == [-10.0, 25.0]


def test_import_nubank_debit_keeps_signs(tmp_db):
    r = import_nubank_csv(FIXTURES / "nubank_debit.csv", tmp_db, kind="debit")
    assert r.total_read == 4
    rows = tmp_db.list_transactions(account_id="nubank:checking")
    amounts = sorted(row["amount"] for row in rows)
    assert amounts == [-250.0, -100.5, -42.9, 1500.0]


def test_import_nubank_invalid_kind(tmp_db):
    with pytest.raises(ValueError):
        import_nubank_csv(FIXTURES / "nubank_credit.csv", tmp_db, kind="invalid")
