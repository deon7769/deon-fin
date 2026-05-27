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


def test_import_nubank_credit_flips_signs(tmp_db):
    r = import_nubank_csv(FIXTURES / "nubank_credit.csv", tmp_db, kind="credit")
    assert r.total_read == 5
    rows = tmp_db.list_transactions(account_id="nubank:credit-card")
    assert len(rows) == 5
    assert all(row["amount"] < 0 for row in rows), "todas devem ser saídas (negativas)"


def test_import_nubank_debit_keeps_signs(tmp_db):
    r = import_nubank_csv(FIXTURES / "nubank_debit.csv", tmp_db, kind="debit")
    assert r.total_read == 4
    rows = tmp_db.list_transactions(account_id="nubank:checking")
    amounts = sorted(row["amount"] for row in rows)
    assert amounts == [-250.0, -100.5, -42.9, 1500.0]


def test_import_nubank_invalid_kind(tmp_db):
    with pytest.raises(ValueError):
        import_nubank_csv(FIXTURES / "nubank_credit.csv", tmp_db, kind="invalid")
