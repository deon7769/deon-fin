from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.agent import Categorizer
from src.storage import Account, Transaction


@pytest.mark.parametrize(
    "description,expected",
    [
        ("IFOOD *RESTAURANTE TAL", "Alimentação - Restaurante"),
        ("UBER TRIP HELP.UBER.COM", "Transporte - App"),
        ("NETFLIX.COM", "Assinaturas - Streaming"),
        ("PIX ENVIADO MARIA", "Transferências - PIX"),
        ("POSTO SHELL CENTRO", "Transporte - Combustível"),
        ("DROGARIA PACHECO", "Saúde - Farmácia"),
        ("ENEL DISTRIBUICAO SP", "Moradia - Contas"),
        ("MEGA SUSHI", "Alimentação - Restaurante"),
        ("AMAZON BR SERVICOS", "Compras - E-commerce"),
        ("Coisa aleatoria sem match", None),
    ],
)
def test_classify(description, expected):
    assert Categorizer().classify(description) == expected


def test_apply_to_database(tmp_db):
    tmp_db.upsert_account(Account(id="acc:1", source="csv"))
    txs = [
        Transaction(account_id="acc:1", posted_at=date(2026, 5, 1), amount=Decimal("-30"),
                    description="iFood pedido", source="csv"),
        Transaction(account_id="acc:1", posted_at=date(2026, 5, 2), amount=Decimal("-50"),
                    description="Netflix.com", source="csv"),
        Transaction(account_id="acc:1", posted_at=date(2026, 5, 3), amount=Decimal("-99"),
                    description="loja desconhecida xyz", source="csv"),
    ]
    tmp_db.insert_transactions(txs)
    stats = Categorizer().apply_to_database(tmp_db)
    assert stats["updated"] == 2
    assert stats["unmatched"] == 1
