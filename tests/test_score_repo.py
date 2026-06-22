from __future__ import annotations

import pytest

from src.web.repositories import portfolio_repo


def _score_repo():
    try:
        from src.web.repositories import score_repo
    except ImportError as exc:
        pytest.fail(f"score_repo repository is missing: {exc}")
    return score_repo


def _create_asset(tmp_db, asset_class: str = "acoes_nac") -> dict:
    return portfolio_repo.create_manual_asset(
        tmp_db,
        asset_class=asset_class,
        ticker="WEGE3" if asset_class != "rf" else None,
        name="WEG" if asset_class != "rf" else "Tesouro Selic",
        quantity=10 if asset_class != "rf" else 0,
        manual_value=400,
    )


def test_compute_nota_counts_unanswered_questions_as_negative(tmp_db):
    score_repo = _score_repo()
    asset = _create_asset(tmp_db)

    score = score_repo.compute_nota(tmp_db, asset["id"])

    assert score == {
        "asset_id": asset["id"],
        "diagram_type": "acoes",
        "pontos_positivos": 0.0,
        "pontos_negativos": 5.0,
        "peso_total": 5.0,
        "nota": -10.0,
    }


def test_compute_nota_normalizes_yes_and_no_answers_to_minus_10_plus_10(tmp_db):
    score_repo = _score_repo()
    asset = _create_asset(tmp_db)
    question_ids = [
        row["id"]
        for row in tmp_db._conn.execute(
            """
            SELECT id
              FROM asset_questions
             WHERE diagram_type='acoes'
             ORDER BY sort_order, id
            """
        ).fetchall()
    ]
    assert len(question_ids) == 5

    score_repo.save_asset_answers(
        tmp_db,
        asset["id"],
        {question_ids[0]: 1, question_ids[1]: 1, question_ids[2]: 1},
    )

    score = score_repo.compute_nota(tmp_db, asset["id"])

    assert score["pontos_positivos"] == 3.0
    assert score["pontos_negativos"] == 2.0
    assert score["peso_total"] == 5.0
    assert score["nota"] == 2.0


def test_compute_nota_returns_na_for_unscored_asset_class(tmp_db):
    score_repo = _score_repo()
    asset = _create_asset(tmp_db, "rf")

    score = score_repo.compute_nota(tmp_db, asset["id"])

    assert score == {
        "asset_id": asset["id"],
        "diagram_type": None,
        "pontos_positivos": 0.0,
        "pontos_negativos": 0.0,
        "peso_total": 0.0,
        "nota": None,
    }


def test_compute_nota_rejects_missing_asset(tmp_db):
    score_repo = _score_repo()
    with pytest.raises(ValueError, match="ativo não encontrado"):
        score_repo.compute_nota(tmp_db, 999999)
