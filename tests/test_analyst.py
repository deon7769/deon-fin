from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.agent.anonymize import anonymize
from src.agent.context import build_financial_context
from src.storage import Account, Transaction


# --------------------------------------------------------------- anonymize
def test_anonymize_remove_cpf_e_conta():
    out = anonymize("Pagamento CPF 068.116.539-14 conta 341/0292/00012354-4")
    assert "068.116.539-14" not in out
    assert "00012354" not in out
    assert "<cpf>" in out and "<conta>" in out


def test_anonymize_mascara_nome_em_pix():
    out = anonymize("Pix recebido FELIPE DE SOUZA GRANADO")
    assert "FELIPE" not in out.upper()
    assert "<pessoa>" in out


def test_anonymize_preserva_comerciante():
    # Nome de loja não é PII e deve permanecer.
    out = anonymize("IFD*IFOOD CLUB")
    assert "ifood" in out.lower()


def test_anonymize_vazio():
    assert anonymize(None) == ""
    assert anonymize("") == ""


# --------------------------------------------------------------- context
def _seed(db):
    db.upsert_account(Account(id="bank1", source="pluggy", name="itau", type="BANK"))
    db.upsert_account(Account(id="card1", source="pluggy", name="Black", type="CREDIT"))
    txs = [
        # Conta bancária
        Transaction(account_id="bank1", posted_at=date(2026, 5, 5), amount=Decimal("5000"),
                    description="Salario", source="pluggy", category="Salary"),
        Transaction(account_id="bank1", posted_at=date(2026, 5, 6), amount=Decimal("-200"),
                    description="Compra debito BISTEK", source="pluggy", category="Groceries"),
        Transaction(account_id="bank1", posted_at=date(2026, 5, 10), amount=Decimal("-1000"),
                    description="Pagamento fatura", source="pluggy", category="Credit card payment"),
        Transaction(account_id="bank1", posted_at=date(2026, 5, 12), amount=Decimal("-300"),
                    description="Aplicacao RDB", source="pluggy", category="Investments"),
        # Cartão de crédito (compra positiva, estorno negativo)
        Transaction(account_id="card1", posted_at=date(2026, 5, 8), amount=Decimal("300"),
                    description="Loja X", source="pluggy", category="Shopping"),
        Transaction(account_id="card1", posted_at=date(2026, 5, 9), amount=Decimal("-50"),
                    description="Estorno loja X", source="pluggy", category="Shopping"),
        # Compromisso futuro (parcela a vencer)
        Transaction(account_id="card1", posted_at=date(2026, 8, 1), amount=Decimal("400"),
                    description="Parcela futura", source="pluggy", category="Clothing"),
    ]
    db.insert_transactions(txs)


def test_context_separa_gasto_renda_e_futuro(tmp_db):
    _seed(tmp_db)
    ctx = build_financial_context(
        tmp_db, monthly_income=10000, goals=["reserva"], today=date(2026, 6, 9)
    ).to_dict()

    cats = {c["categoria"]: c["total"] for c in ctx["gasto_por_categoria"]}
    assert cats["Groceries"] == 200.0
    assert cats["Shopping"] == 250.0           # 300 compra - 50 estorno
    assert "Credit card payment" not in cats   # liquidação não é gasto
    assert "Investments" not in cats           # aporte não é gasto

    mes = ctx["fluxo_mensal"]["2026-05"]
    assert mes["renda"] == 5000.0
    assert mes["investido"] == 300.0
    assert ctx["pagamentos_cartao_total"] == 1000.0
    assert ctx["investido_total"] == 300.0
    assert ctx["compromissos_futuros"]["total"] == 400.0
    assert ctx["renda_mensal_informada"] == 10000


def test_context_db_vazio_nao_quebra(tmp_db):
    ctx = build_financial_context(tmp_db, today=date(2026, 6, 9)).to_dict()
    assert ctx["meses_cobertos"] == 1
    assert ctx["gasto_por_categoria"] == []
    assert ctx["media_gasto_mensal"] == 0.0


def test_context_futuros_por_mes(tmp_db):
    _seed(tmp_db)
    ctx = build_financial_context(tmp_db, today=date(2026, 6, 9)).to_dict()
    assert ctx["compromissos_futuros"]["por_mes"].get("2026-08") == 400.0


def test_context_filtro_de_periodo(tmp_db):
    _seed(tmp_db)  # gastos realizados só em 2026-05
    ctx = build_financial_context(
        tmp_db, today=date(2026, 6, 9), period_months=1
    ).to_dict()
    # janela de 1 mês = junho/2026; maio fica de fora → sem gasto realizado
    assert ctx["gasto_por_categoria"] == []


def test_transfer_noise_helper():
    from src.agent.context import _is_transfer_noise
    assert _is_transfer_noise("transferencia enviada")
    assert _is_transfer_noise("pix recebido fulano")
    assert not _is_transfer_noise("netflix br")
