"""Dados editáveis pelo usuário (área de Manutenção), persistidos em data/*.json.

São informações que NÃO vêm da integração bancária e que o usuário define a
partir das conversas: receitas, reservas/provisões, metas, patrimônio
(`family_profile.json`) e os "de/para" de tradução de categorias e de
classificação de assinaturas/recorrências (`overrides.json`).

Lidos a cada request (sem precisar reiniciar o servidor após editar).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
FAMILY_PROFILE_PATH = DATA_DIR / "family_profile.json"
OVERRIDES_PATH = DATA_DIR / "overrides.json"

# Tradução padrão das categorias do Pluggy (inglês → português). Editável.
DEFAULT_CATEGORIAS_PT: dict[str, str] = {
    "services": "Serviços",
    "groceries": "Mercado",
    "gas stations": "Combustível",
    "income taxes": "Impostos",
    "electricity": "Energia",
    "water": "Água",
    "housing": "Moradia",
    "rent": "Aluguel",
    "telecommunications": "Telecom",
    "internet": "Internet",
    "healthcare": "Saúde",
    "hospital clinics and labs": "Hospital/Clínica",
    "pharmacy": "Farmácia",
    "optometry": "Óptica",
    "education": "Educação",
    "automotive": "Automotivo",
    "insurance": "Seguros",
    "vehicle insurance": "Seguro do veículo",
    "taxi and ride-hailing": "Táxi/App",
    "transport": "Transporte",
    "parking": "Estacionamento",
    "food and drinks": "Alimentação",
    "shopping": "Compras",
    "online shopping": "Compras online",
    "eating out": "Restaurantes",
    "food delivery": "Delivery",
    "clothing": "Vestuário",
    "wellness and fitness": "Bem-estar/Academia",
    "gyms and fitness centers": "Academia",
    "leisure": "Lazer",
    "tickets": "Ingressos",
    "digital services": "Serviços digitais",
    "video streaming": "Streaming de vídeo",
    "music streaming": "Streaming de música",
    "electronics": "Eletrônicos",
    "bookstore": "Livraria",
    "houseware": "Casa/Utilidades",
    "accomodation": "Hospedagem",
    "office supplies": "Material de escritório",
    "donations": "Doações",
    "travel": "Viagem",
    "entertainment": "Entretenimento",
    "investments": "Investimentos",
    "credit card fees": "Tarifas de cartão",
    "interests charged": "Juros",
    "loans and financing": "Empréstimos/Financiamento",
    "tax on financial operations": "IOF",
    "bank fees": "Tarifas bancárias",
    "transfer - pix": "Transferência - PIX",
    "transfers": "Transferências",
    "same person transfer": "Transferência entre contas",
    "transfer - internal": "Transferência interna",
    "credit card payment": "Pagamento de fatura",
    "(sem categoria)": "Sem categoria",
}

# tipos válidos para o de/para de recorrências
TIPOS_RECORRENCIA = ("assinatura", "recorrencia", "ignorar")


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- family profile
def load_family_profile() -> dict[str, Any] | None:
    return _read_json(FAMILY_PROFILE_PATH)


def save_family_profile(profile: dict[str, Any]) -> None:
    _write_json(FAMILY_PROFILE_PATH, profile)


def income_from_profile(profile: dict[str, Any] | None) -> float | None:
    """Soma das receitas do perfil — a renda 'informada' dinâmica."""
    if not profile:
        return None
    receitas = profile.get("receitas") or []
    total = sum(float(r.get("valor", 0) or 0) for r in receitas)
    return total or None


# ---------------------------------------------------------------- overrides
def load_overrides() -> dict[str, Any]:
    """Retorna {categorias_pt, recorrencias}, preenchendo os defaults faltantes."""
    data = _read_json(OVERRIDES_PATH) or {}
    cat = {**DEFAULT_CATEGORIAS_PT, **(data.get("categorias_pt") or {})}
    rec = data.get("recorrencias") or []
    return {"categorias_pt": cat, "recorrencias": rec}


def save_overrides(data: dict[str, Any]) -> None:
    # Guarda só o que diverge/define o usuário (categorias_pt completo é ok).
    payload = {
        "categorias_pt": data.get("categorias_pt") or {},
        "recorrencias": data.get("recorrencias") or [],
    }
    _write_json(OVERRIDES_PATH, payload)


def translate_category(name: str, cat_map: dict[str, str]) -> str:
    return cat_map.get((name or "").lower().strip(), name)


def apply_recurrence_overrides(
    recorrencias: list[dict[str, Any]], rec_map: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Aplica o de/para: remove 'ignorar', marca tipo/rótulo nas demais.

    rec_map: lista de {match, tipo, rotulo?}. 'match' casa por substring no
    comerciante (case-insensitive).
    """
    rules = [
        (str(r.get("match", "")).lower().strip(), r.get("tipo", "recorrencia"),
         r.get("rotulo") or None)
        for r in rec_map if r.get("match")
    ]
    out: list[dict[str, Any]] = []
    for item in recorrencias:
        comerciante = str(item.get("comerciante", "")).lower()
        tipo = "assinatura" if item.get("estavel") else "recorrencia"
        rotulo = None
        ignore = False
        for match, t, rot in rules:
            if match in comerciante:
                if t == "ignorar":
                    ignore = True
                    break
                tipo = t
                rotulo = rot
        if ignore:
            continue
        novo = dict(item)
        novo["tipo"] = tipo
        if rotulo:
            novo["comerciante"] = rotulo
        out.append(novo)
    return out
