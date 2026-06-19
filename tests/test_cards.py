from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.agent.cards import card_monthly_breakdown
from src.storage import Account, Transaction


def _seed(db):
    db.upsert_account(Account(id="card1", source="pluggy", name="Itaú Black", type="CREDIT"))
    db.upsert_account(Account(id="bank1", source="pluggy", name="Itaú", type="BANK"))
    txs = [
        # cartão — mês passado (realizado)
        Transaction(account_id="card1", posted_at=date(2026, 5, 10), amount=Decimal("300"),
                    description="Loja", source="pluggy", category="Shopping"),
        # cartão — mês atual
        Transaction(account_id="card1", posted_at=date(2026, 6, 5), amount=Decimal("200"),
                    description="Mercado", source="pluggy", category="Groceries"),
        # cartão — futuro (parcela a vencer)
        Transaction(account_id="card1", posted_at=date(2026, 8, 1), amount=Decimal("150"),
                    description="Parcela", source="pluggy", category="Electronics"),
        # conta bancária — NÃO deve entrar
        Transaction(account_id="bank1", posted_at=date(2026, 6, 7), amount=Decimal("-50"),
                    description="Débito", source="pluggy", category="Groceries"),
    ]
    db.insert_transactions(txs)


def test_card_breakdown_separa_realizado_e_futuro(tmp_db):
    _seed(tmp_db)
    cat_map = {"shopping": "Compras", "groceries": "Mercado", "electronics": "Eletrônicos"}
    out = card_monthly_breakdown(tmp_db, today=date(2026, 6, 11), cat_map=cat_map)

    meses = {m["mes"]: m for m in out["meses"]}
    assert set(meses) == {"2026-05", "2026-06", "2026-08"}
    assert meses["2026-05"]["tipo"] == "realizado"
    assert meses["2026-06"]["tipo"] == "atual"
    assert meses["2026-08"]["tipo"] == "futuro"
    # categoria traduzida
    assert meses["2026-05"]["por_categoria"][0]["categoria"] == "Compras"

    r = out["resumo"]
    assert r["fatura_mes_atual"] == 200.0
    assert r["gasto_realizado"] == 500.0   # 300 (maio) + 200 (junho)
    assert r["futuro_parcelado"] == 150.0  # agosto
    assert out["meses"][out["indice_atual"]]["mes"] == "2026-06"


def test_card_breakdown_ignora_conta_bancaria(tmp_db):
    _seed(tmp_db)
    out = card_monthly_breakdown(tmp_db, today=date(2026, 6, 11))
    # nenhuma categoria de débito bancário deve aparecer no total dos cartões
    total = sum(m["total"] for m in out["meses"])
    assert total == 650.0  # 300 + 200 + 150 (sem o -50 do banco)
