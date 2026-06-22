from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...agent.portfolio import quotes
from ...storage import Database
from ..dependencies import get_db
from ..errors import error_response
from ..repositories import portfolio_repo, score_repo

router = APIRouter(prefix="/api", tags=["portfolio"])


class AssetCreateRequest(BaseModel):
    asset_class: str
    ticker: str | None = None
    name: str | None = None
    quantity: float | None = None
    manual_value: float | None = None


class AssetPatchRequest(BaseModel):
    asset_class: str | None = None
    ticker: str | None = None
    name: str | None = None
    quantity: float | None = None
    manual_value: float | None = None


class TargetsSaveRequest(BaseModel):
    targets: dict[str, float]
    perfil: str | None = None


class AporteCalculateRequest(BaseModel):
    aporte: float


class AporteCompraRequest(BaseModel):
    asset_id: int
    quantidade: float


class AporteConfirmRequest(BaseModel):
    compras: list[AporteCompraRequest]
    aporte: float | None = None


class QuestionCreateRequest(BaseModel):
    diagram_type: str
    criterio: str | None = None
    pergunta: str
    peso: float = 1.0
    sort_order: int = 0
    ativo: bool = True


class QuestionPatchRequest(BaseModel):
    diagram_type: str | None = None
    criterio: str | None = None
    pergunta: str | None = None
    peso: float | None = None
    sort_order: int | None = None
    ativo: bool | None = None


class AssetAnswerRequest(BaseModel):
    question_id: int
    resposta: bool


class AssetAnswersSaveRequest(BaseModel):
    answers: list[AssetAnswerRequest]


def _fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is None:
        fields = getattr(model, "__fields_set__", set())
    return set(fields)


def _repo_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/investments")
def investments_summary(
    include_inactive: bool = Query(default=False),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    return portfolio_repo.portfolio_summary(db, include_inactive=include_inactive)


@router.get("/investments/profiles")
def investment_profiles() -> dict[str, Any]:
    return portfolio_repo.get_investment_profiles()


@router.get("/investments/targets")
def investment_targets(db: Database = Depends(get_db)) -> dict[str, Any]:
    return portfolio_repo.get_allocation_targets(db)


@router.post("/investments/aporte/calcular")
def calculate_investment_aporte(
    body: AporteCalculateRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return portfolio_repo.calculate_aporte(db, body.aporte)
    except ValueError as exc:
        if str(exc) == "targets_sum":
            return error_response(
                422,
                "targets_sum",
                "Ajuste as Metas da carteira para 100% antes de aportar.",
            )
        raise _repo_error(exc) from exc


@router.post("/investments/aporte/confirmar")
def confirm_investment_aporte(
    body: AporteConfirmRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return portfolio_repo.confirm_aporte(
            db,
            compras=[compra.model_dump() for compra in body.compras],
            aporte=body.aporte,
        )
    except ValueError as exc:
        if str(exc) == "ativo não encontrado":
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise _repo_error(exc) from exc


@router.get("/investments/questions")
def investment_questions(
    diagram_type: str = Query(...),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return {
            "diagram_type": diagram_type,
            "questions": score_repo.list_questions(db, diagram_type),
        }
    except ValueError as exc:
        raise _repo_error(exc) from exc


@router.post("/investments/questions", status_code=201)
def create_investment_question(
    body: QuestionCreateRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return score_repo.create_question(
            db,
            diagram_type=body.diagram_type,
            criterio=body.criterio,
            pergunta=body.pergunta,
            peso=body.peso,
            sort_order=body.sort_order,
            ativo=body.ativo,
        )
    except ValueError as exc:
        raise _repo_error(exc) from exc


@router.post("/investments/questions/restore-defaults")
def restore_investment_questions(
    diagram_type: str = Query(...),
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return score_repo.restore_default_questions(db, diagram_type)
    except ValueError as exc:
        raise _repo_error(exc) from exc


@router.patch("/investments/questions/{question_id}")
def update_investment_question(
    question_id: int,
    body: QuestionPatchRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    fields = _fields_set(body)
    if not fields:
        raise HTTPException(status_code=422, detail="corpo vazio")
    try:
        question = score_repo.update_question(
            db,
            question_id,
            **{field: getattr(body, field) for field in fields},
        )
    except ValueError as exc:
        raise _repo_error(exc) from exc
    if question is None:
        raise HTTPException(status_code=404, detail="pergunta não encontrada")
    return question


@router.delete("/investments/questions/{question_id}")
def delete_investment_question(
    question_id: int,
    db: Database = Depends(get_db),
) -> dict[str, int]:
    result = score_repo.delete_question(db, question_id)
    if result is None:
        raise HTTPException(status_code=404, detail="pergunta não encontrada")
    return result


@router.get("/investments/assets/{asset_id}/answers")
def get_investment_asset_answers(
    asset_id: int,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return score_repo.get_asset_answers(db, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/investments/assets/{asset_id}/answers")
def save_investment_asset_answers(
    asset_id: int,
    body: AssetAnswersSaveRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return score_repo.save_asset_answers_response(
            db,
            asset_id,
            {answer.question_id: answer.resposta for answer in body.answers},
        )
    except ValueError as exc:
        message = str(exc)
        if message == "ativo não encontrado":
            raise HTTPException(status_code=404, detail=message) from exc
        raise _repo_error(exc) from exc


@router.put("/investments/targets")
def save_investment_targets(
    body: TargetsSaveRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    try:
        return portfolio_repo.save_allocation_targets(
            db,
            body.targets,
            perfil=body.perfil,
        )
    except ValueError as exc:
        if str(exc) == "targets_sum":
            return error_response(
                422,
                "targets_sum",
                "A soma das metas deve ser 100%.",
            )
        raise _repo_error(exc) from exc


@router.get("/investments/ticker-search")
def ticker_search(
    q: str = Query(default=""),
    classe: str = Query(default="acoes_nac"),
) -> dict[str, Any]:
    try:
        return {"items": quotes.search_ticker(q, classe)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/investments/assets", status_code=201)
def create_asset(
    body: AssetCreateRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    unit_price = None
    price_updated_at = None
    price_source = None
    ticker = body.ticker.upper() if body.ticker else None
    if ticker and body.asset_class in quotes.QUOTEABLE_CLASSES:
        try:
            quote = quotes.get_quotes(db, [ticker], body.asset_class).get(ticker)
        except Exception:
            quote = None
        if quote:
            unit_price = float(quote["price"])
            price_updated_at = str(quote.get("ts") or "")
            price_source = "brapi"
    try:
        return portfolio_repo.create_manual_asset(
            db,
            asset_class=body.asset_class,
            ticker=ticker,
            name=body.name,
            quantity=body.quantity,
            manual_value=body.manual_value,
            unit_price=unit_price,
            price_source=price_source,
            price_updated_at=price_updated_at,
        )
    except ValueError as exc:
        raise _repo_error(exc) from exc


@router.patch("/investments/assets/{asset_id}")
def update_asset(
    asset_id: int,
    body: AssetPatchRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    fields = _fields_set(body)
    if not fields:
        raise HTTPException(status_code=422, detail="corpo vazio")
    updates = {field: getattr(body, field) for field in fields}
    try:
        asset = portfolio_repo.update_asset(db, asset_id, **updates)
    except ValueError as exc:
        raise _repo_error(exc) from exc
    if asset is None:
        raise HTTPException(status_code=404, detail="ativo não encontrado")
    return asset


@router.delete("/investments/assets/{asset_id}")
def delete_asset(asset_id: int, db: Database = Depends(get_db)) -> dict[str, int]:
    result = portfolio_repo.delete_asset(db, asset_id)
    if result is None:
        raise HTTPException(status_code=404, detail="ativo não encontrado")
    return result


@router.post("/investments/refresh-quotes")
def refresh_quotes(db: Database = Depends(get_db)) -> dict[str, int]:
    try:
        return quotes.refresh_prices(db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
