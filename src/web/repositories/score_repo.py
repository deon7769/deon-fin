from __future__ import annotations

from typing import Any

from src.domain.investment_questions import DEFAULT_ASSET_QUESTIONS, DIAGRAM_BY_ASSET_CLASS

from ...storage import Database

VALID_DIAGRAM_TYPES = set(DEFAULT_ASSET_QUESTIONS)


def _round_score(value: float) -> float:
    return round(float(value), 2)


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _validate_diagram_type(diagram_type: str) -> str:
    value = str(diagram_type or "").strip()
    if value not in VALID_DIAGRAM_TYPES:
        raise ValueError("tipo de diagrama inválido")
    return value


def _validate_peso(value: Any) -> float:
    try:
        peso = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("peso inválido") from exc
    if peso <= 0:
        raise ValueError("peso inválido")
    return peso


def _row_to_question(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "diagram_type": row["diagram_type"],
        "criterio": row["criterio"],
        "pergunta": row["pergunta"],
        "peso": _round_score(row["peso"]),
        "sort_order": int(row["sort_order"] or 0),
        "ativo": bool(row["ativo"]),
    }


def diagram_for_asset_class(asset_class: str | None) -> str | None:
    return DIAGRAM_BY_ASSET_CLASS.get(str(asset_class or "").strip())


def _empty_score(asset_id: int, diagram_type: str | None) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "diagram_type": diagram_type,
        "pontos_positivos": 0.0,
        "pontos_negativos": 0.0,
        "peso_total": 0.0,
        "nota": None,
    }


def compute_nota(db: Database, asset_id: int) -> dict[str, Any]:
    asset = db._conn.execute(
        "SELECT id, asset_class FROM portfolio_assets WHERE id=?",
        (asset_id,),
    ).fetchone()
    if asset is None:
        raise ValueError("ativo não encontrado")

    diagram_type = diagram_for_asset_class(asset["asset_class"])
    if diagram_type is None:
        return _empty_score(asset_id, None)

    questions = db._conn.execute(
        """
        SELECT id, peso
          FROM asset_questions
         WHERE diagram_type=?
           AND ativo=1
         ORDER BY sort_order, id
        """,
        (diagram_type,),
    ).fetchall()
    if not questions:
        return _empty_score(asset_id, diagram_type)

    answers = {
        row["question_id"]: int(row["resposta"] or 0)
        for row in db._conn.execute(
            "SELECT question_id, resposta FROM asset_answers WHERE asset_id=?",
            (asset_id,),
        ).fetchall()
    }
    peso_total = sum(float(question["peso"] or 0.0) for question in questions)
    pontos_positivos = sum(
        float(question["peso"] or 0.0)
        for question in questions
        if answers.get(int(question["id"]), 0) == 1
    )
    pontos_negativos = peso_total - pontos_positivos
    nota = ((pontos_positivos - pontos_negativos) / peso_total) * 10 if peso_total else None
    return {
        "asset_id": asset_id,
        "diagram_type": diagram_type,
        "pontos_positivos": _round_score(pontos_positivos),
        "pontos_negativos": _round_score(pontos_negativos),
        "peso_total": _round_score(peso_total),
        "nota": _round_score(nota) if nota is not None else None,
    }


def list_questions(db: Database, diagram_type: str, *, include_inactive: bool = False) -> list[dict[str, Any]]:
    normalized = _validate_diagram_type(diagram_type)
    where_active = "" if include_inactive else "AND ativo=1"
    rows = db._conn.execute(
        f"""
        SELECT *
          FROM asset_questions
         WHERE diagram_type=?
           {where_active}
         ORDER BY sort_order, id
        """,
        (normalized,),
    ).fetchall()
    return [_row_to_question(row) for row in rows]


def create_question(
    db: Database,
    *,
    diagram_type: str,
    pergunta: str,
    criterio: str | None = None,
    peso: float = 1.0,
    sort_order: int = 0,
    ativo: bool = True,
) -> dict[str, Any]:
    normalized = _validate_diagram_type(diagram_type)
    normalized_pergunta = _text(pergunta)
    if not normalized_pergunta:
        raise ValueError("pergunta obrigatória")
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO asset_questions (
                diagram_type, criterio, pergunta, peso, sort_order, ativo
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                normalized,
                _text(criterio),
                normalized_pergunta,
                _validate_peso(peso),
                int(sort_order or 0),
                1 if ativo else 0,
            ),
        )
        question_id = int(cur.lastrowid)
    question = get_question(db, question_id)
    if question is None:
        raise RuntimeError("pergunta não foi criada")
    return question


def get_question(db: Database, question_id: int) -> dict[str, Any] | None:
    row = db._conn.execute(
        "SELECT * FROM asset_questions WHERE id=?",
        (question_id,),
    ).fetchone()
    return _row_to_question(row) if row else None


def update_question(db: Database, question_id: int, **updates: Any) -> dict[str, Any] | None:
    current = db._conn.execute(
        "SELECT * FROM asset_questions WHERE id=?",
        (question_id,),
    ).fetchone()
    if current is None:
        return None

    diagram_type = current["diagram_type"]
    if "diagram_type" in updates and updates["diagram_type"] is not None:
        diagram_type = _validate_diagram_type(updates["diagram_type"])
    criterio = current["criterio"]
    if "criterio" in updates:
        criterio = _text(updates["criterio"])
    pergunta = current["pergunta"]
    if "pergunta" in updates:
        pergunta = _text(updates["pergunta"])
        if not pergunta:
            raise ValueError("pergunta obrigatória")
    peso = float(current["peso"] or 1.0)
    if "peso" in updates and updates["peso"] is not None:
        peso = _validate_peso(updates["peso"])
    sort_order = int(current["sort_order"] or 0)
    if "sort_order" in updates and updates["sort_order"] is not None:
        sort_order = int(updates["sort_order"])
    ativo = bool(current["ativo"])
    if "ativo" in updates and updates["ativo"] is not None:
        ativo = bool(updates["ativo"])

    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            UPDATE asset_questions
               SET diagram_type=?,
                   criterio=?,
                   pergunta=?,
                   peso=?,
                   sort_order=?,
                   ativo=?
             WHERE id=?
            """,
            (diagram_type, criterio, pergunta, peso, sort_order, 1 if ativo else 0, question_id),
        )
    return get_question(db, question_id)


def delete_question(db: Database, question_id: int) -> dict[str, int] | None:
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute("DELETE FROM asset_answers WHERE question_id=?", (question_id,))
        cur.execute("DELETE FROM asset_questions WHERE id=?", (question_id,))
        if cur.rowcount == 0:
            return None
    return {"deleted_id": question_id}


def restore_default_questions(db: Database, diagram_type: str) -> dict[str, Any]:
    normalized = _validate_diagram_type(diagram_type)
    defaults = DEFAULT_ASSET_QUESTIONS[normalized]
    with db._cursor() as cur:  # type: ignore[attr-defined]
        question_ids = [
            row["id"]
            for row in cur.execute(
                "SELECT id FROM asset_questions WHERE diagram_type=?",
                (normalized,),
            ).fetchall()
        ]
        for question_id in question_ids:
            cur.execute("DELETE FROM asset_answers WHERE question_id=?", (question_id,))
        cur.execute("DELETE FROM asset_questions WHERE diagram_type=?", (normalized,))
        for question in defaults:
            cur.execute(
                """
                INSERT INTO asset_questions (
                    diagram_type, criterio, pergunta, peso, sort_order, ativo
                )
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (
                    normalized,
                    question["criterio"],
                    question["pergunta"],
                    question["peso"],
                    question["sort_order"],
                ),
            )
    return {"diagram_type": normalized, "questions": list_questions(db, normalized)}


def get_asset_answers(db: Database, asset_id: int) -> dict[str, Any]:
    score = compute_nota(db, asset_id)
    diagram_type = score["diagram_type"]
    if diagram_type is None:
        return {"asset_id": asset_id, "diagram_type": None, "questions": [], "answers": [], "score": score}

    questions = list_questions(db, diagram_type)
    persisted = {
        row["question_id"]: bool(row["resposta"])
        for row in db._conn.execute(
            "SELECT question_id, resposta FROM asset_answers WHERE asset_id=?",
            (asset_id,),
        ).fetchall()
    }
    answers = [
        {
            "asset_id": asset_id,
            "question_id": question["id"],
            "resposta": bool(persisted.get(question["id"], False)),
        }
        for question in questions
    ]
    return {
        "asset_id": asset_id,
        "diagram_type": diagram_type,
        "questions": questions,
        "answers": answers,
        "score": score,
    }


def save_asset_answers(
    db: Database,
    asset_id: int,
    answers: dict[int | str, int | bool],
) -> dict[str, Any]:
    current = get_asset_answers(db, asset_id)
    valid_question_ids = {question["id"] for question in current["questions"]}
    with db._cursor() as cur:  # type: ignore[attr-defined]
        for question_id, resposta in answers.items():
            normalized_question_id = int(question_id)
            if normalized_question_id not in valid_question_ids:
                raise ValueError("pergunta inválida")
            cur.execute(
                """
                INSERT INTO asset_answers (asset_id, question_id, resposta)
                VALUES (?, ?, ?)
                ON CONFLICT(asset_id, question_id) DO UPDATE SET
                    resposta=excluded.resposta
                """,
                (asset_id, normalized_question_id, 1 if bool(resposta) else 0),
            )
    return compute_nota(db, asset_id)


def save_asset_answers_response(
    db: Database,
    asset_id: int,
    answers: dict[int | str, int | bool],
) -> dict[str, Any]:
    save_asset_answers(db, asset_id, answers)
    return get_asset_answers(db, asset_id)
