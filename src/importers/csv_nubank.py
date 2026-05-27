from __future__ import annotations

from pathlib import Path

from ..storage import Database
from .base import ImportResult
from .csv_generic import CSVMapping, import_csv


def import_nubank_csv(
    path: Path | str,
    db: Database,
    *,
    kind: str = "credit",
    account_id: str | None = None,
) -> ImportResult:
    """Importa CSV exportado do app Nubank.

    kind='credit'  -> fatura do cartão Nubank
        Colunas: date, title, amount (todos positivos, são gastos)
    kind='debit'   -> extrato da conta Nubank
        Colunas: Data, Valor, Identificador, Descrição
    """
    if kind == "credit":
        acc_id = account_id or "nubank:credit-card"
        mapping = CSVMapping(
            date_col="date",
            amount_col="amount",
            description_col="title",
            date_format="%Y-%m-%d",
        )
        result = import_csv(
            path, db, mapping=mapping, account_id=acc_id,
            institution="Nubank", account_type="CREDIT",
        )
        # Despesas em cartão são positivas no CSV; convertendo p/ negativo (saída de caixa)
        _flip_credit_card_signs(db, acc_id)
        return result

    if kind == "debit":
        acc_id = account_id or "nubank:checking"
        mapping = CSVMapping(
            date_col="Data",
            amount_col="Valor",
            description_col="Descrição",
            date_format="%d/%m/%Y",
        )
        return import_csv(
            path, db, mapping=mapping, account_id=acc_id,
            institution="Nubank", account_type="CHECKING",
        )

    raise ValueError(f"kind inválido: {kind!r} (use 'credit' ou 'debit')")


def _flip_credit_card_signs(db: Database, account_id: str) -> None:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            "UPDATE transactions SET amount = -ABS(amount) WHERE account_id=? AND amount > 0",
            (account_id,),
        )
