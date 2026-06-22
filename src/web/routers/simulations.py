from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...agent.simulators import (
    aluguel_vs_financiamento,
    amortizacao_completa,
    cdb,
    juros_compostos,
    marcacao_mercado,
    pix_parcelado,
    renda_retiradas,
)
from ...config import settings

router = APIRouter(prefix="/api/sim", tags=["simulations"])


class JurosCompostosRequest(BaseModel):
    valor_inicial: float
    valor_mensal: float
    taxa: float
    taxa_periodo: Literal["anual", "mensal"]
    periodo: int
    periodo_unidade: Literal["anos", "meses"]


class RendaRequest(BaseModel):
    valor_inicial: float
    retirada_mensal: float
    taxa: float
    taxa_periodo: Literal["anual", "mensal"]
    periodo: int
    periodo_unidade: Literal["anos", "meses"]


class PixParceladoRequest(BaseModel):
    valor_pix: float
    n_parcelas: int
    juros_mensal_pct: float = 0.0
    incluir_valor_parcela: bool = False
    valor_parcela: float | None = None


class CdbRequest(BaseModel):
    investimento_inicial: float
    investimento_mensal: float = 0.0
    cdi_pct: float
    tempo: int
    tempo_unidade: Literal["anos", "meses"]
    cdi_aa: float | None = None


class MarcacaoMercadoRequest(BaseModel):
    tipo: Literal["prefixado", "ipca"]
    data_aplicacao: str
    data_vencimento: str
    valor_investido: float
    valor_atual_bruto: float
    rentabilidade_contratada_aa: float
    isento_ir: bool
    ipca_projetado_aa: float | None = None
    rentabilidade_nova_oferta_aa: float | None = None
    nova_oferta_isenta_ir: bool = False
    data_hoje: str | None = None


class ExtraPaymentRequest(BaseModel):
    mes: int
    valor: float


class AmortizacaoCompletaRequest(BaseModel):
    modalidade: Literal["imobiliario", "veiculos", "consignado", "pessoal"] | None = None
    valor_emprestimo: float
    data_inicio: str
    sistema: Literal["sac", "price"]
    taxa: float
    taxa_periodo: Literal["anual", "mensal"]
    n_parcelas: int
    correcao: Literal["nenhuma", "tr", "ipca"] = "nenhuma"
    indice_correcao_aa: float | None = None
    aportes_extra: list[ExtraPaymentRequest] = Field(default_factory=list)
    modo_aporte: Literal["reduzir_prazo", "reduzir_parcela"] = "reduzir_prazo"
    seguros_taxas_mensal: float = 0.0


class ImovelRequest(BaseModel):
    valor_imovel: float
    entrada: float
    custos_financiamento: float = 0.0
    prazo_meses: int
    taxa_aa: float
    sistema: Literal["sac", "price"]
    aluguel_mensal: float
    reajuste_aluguel_aa: float
    rendimento_investimento_aa: float
    valorizacao_imovel_aa: float


def _simulate(fn, **payload: Any) -> dict[str, Any]:
    try:
        return fn(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/juros-compostos")
def simulate_juros_compostos(body: JurosCompostosRequest) -> dict[str, Any]:
    return _simulate(juros_compostos, **body.model_dump())


@router.post("/renda")
def simulate_renda(body: RendaRequest) -> dict[str, Any]:
    return _simulate(renda_retiradas, **body.model_dump())


@router.post("/pix-parcelado")
def simulate_pix_parcelado(body: PixParceladoRequest) -> dict[str, Any]:
    return _simulate(pix_parcelado, **body.model_dump())


@router.post("/cdb")
def simulate_cdb(body: CdbRequest) -> dict[str, Any]:
    payload = body.model_dump()
    used_default = payload["cdi_aa"] is None
    payload["cdi_aa"] = settings.cdi_aa if used_default else payload["cdi_aa"]
    result = _simulate(cdb, **payload)
    if used_default:
        result["avisos"] = [
            {
                "code": "default_cdi_aa",
                "message": f"CDI anual padrão usado: {payload['cdi_aa']}%.",
            }
        ]
    return result


@router.post("/marcacao-mercado")
def simulate_marcacao_mercado(body: MarcacaoMercadoRequest) -> dict[str, Any]:
    payload = body.model_dump()
    used_default = payload["tipo"] == "ipca" and payload["ipca_projetado_aa"] is None
    payload["ipca_projetado_aa"] = (
        settings.ipca_aa if used_default else payload["ipca_projetado_aa"]
    )
    result = _simulate(marcacao_mercado, **payload)
    if used_default:
        result["avisos"] = [
            {
                "code": "default_ipca_aa",
                "message": f"IPCA projetado padrão usado: {payload['ipca_projetado_aa']}%.",
            }
        ]
    return result


@router.post("/amortizacao")
def simulate_amortizacao_completa(body: AmortizacaoCompletaRequest) -> dict[str, Any]:
    return _simulate(amortizacao_completa, **body.model_dump())


@router.post("/imovel")
def simulate_imovel(body: ImovelRequest) -> dict[str, Any]:
    return _simulate(aluguel_vs_financiamento, **body.model_dump())
