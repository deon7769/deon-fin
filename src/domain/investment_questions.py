from __future__ import annotations

from typing import TypedDict


class AssetQuestionDefault(TypedDict):
    criterio: str
    pergunta: str
    peso: float
    sort_order: int


DIAGRAM_BY_ASSET_CLASS = {
    "acoes_nac": "acoes",
    "acoes_int": "acoes",
    "fii": "imobiliario",
    "reit": "imobiliario",
}

DEFAULT_ASSET_QUESTIONS: dict[str, list[AssetQuestionDefault]] = {
    "acoes": [
        {
            "criterio": "Rentabilidade",
            "pergunta": "ROE historico maior que 8%?",
            "peso": 1.0,
            "sort_order": 10,
        },
        {
            "criterio": "Crescimento",
            "pergunta": "CAGR de receita ou lucro maior que 5% em 5 anos?",
            "peso": 1.0,
            "sort_order": 20,
        },
        {
            "criterio": "Dividendos",
            "pergunta": "Possui historico consistente de dividendos?",
            "peso": 1.0,
            "sort_order": 30,
        },
        {
            "criterio": "Inovacao",
            "pergunta": "Investe de forma recorrente em pesquisa e desenvolvimento?",
            "peso": 1.0,
            "sort_order": 40,
        },
        {
            "criterio": "Longevidade",
            "pergunta": "Tem mais de 30 anos de mercado?",
            "peso": 1.0,
            "sort_order": 50,
        },
    ],
    "imobiliario": [
        {
            "criterio": "Lideranca",
            "pergunta": "E lider do setor?",
            "peso": 1.0,
            "sort_order": 10,
        },
        {
            "criterio": "Longevidade",
            "pergunta": "Atua em um setor com mais de 100 anos?",
            "peso": 1.0,
            "sort_order": 20,
        },
        {
            "criterio": "Governanca",
            "pergunta": "Possui boa governanca?",
            "peso": 1.0,
            "sort_order": 30,
        },
        {
            "criterio": "Concentracao",
            "pergunta": "E livre de controle estatal ou dependencia de cliente unico?",
            "peso": 1.0,
            "sort_order": 40,
        },
        {
            "criterio": "Endividamento",
            "pergunta": "Manteve Divida Liquida/EBITDA menor que 3 em 5 anos?",
            "peso": 1.0,
            "sort_order": 50,
        },
    ],
}
