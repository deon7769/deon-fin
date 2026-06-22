from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "country_ratings.json"

TIER_COLORS = {
    "top": "#2563EB",
    "high": "#22C55E",
    "medium": "#F59E0B",
    "speculative": "#EF4444",
    "nodata": "#3A3A3E",
}

_COUNTRY_RATINGS_CACHE: dict[str, dict[str, Any]] | None = None


def derive_tier_from_sp(rating: str | None) -> str:
    normal = str(rating or "").strip().upper()
    if not normal or normal in {"-", "NA", "N/A", "NR"}:
        return "nodata"
    if normal == "AAA":
        return "top"

    base = normal.rstrip("+-")
    if base in {"AA", "A"}:
        return "high"
    if base in {"BBB", "BB"}:
        return "medium"
    if base in {"B", "CCC", "CC", "C", "D", "SD", "RD"}:
        return "speculative"
    return "nodata"


def color_for_tier(tier: str) -> str:
    return TIER_COLORS.get(str(tier or "").strip().lower(), TIER_COLORS["nodata"])


def load_country_ratings() -> dict[str, dict[str, Any]]:
    global _COUNTRY_RATINGS_CACHE

    if _COUNTRY_RATINGS_CACHE is None:
        with DATA_PATH.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        _COUNTRY_RATINGS_CACHE = {str(code).upper(): data for code, data in raw.items()}
    return _COUNTRY_RATINGS_CACHE


def _computed_tier(country: dict[str, Any]) -> str:
    ratings = country.get("ratings") or {}
    if not isinstance(ratings, dict):
        return "nodata"
    return derive_tier_from_sp(ratings.get("sp"))


def list_country_ratings() -> list[dict[str, str]]:
    countries = load_country_ratings()
    payload = []
    for code, country in countries.items():
        tier = _computed_tier(country)
        payload.append(
            {
                "code": code,
                "name": str(country.get("name") or code),
                "tier": tier,
                "color": color_for_tier(tier),
            }
        )
    return sorted(payload, key=lambda item: item["code"])


def get_country_rating(code: str) -> dict[str, Any]:
    normal = str(code or "").strip().upper()
    countries = load_country_ratings()
    country = countries.get(normal)
    if country is None:
        raise ValueError("país não encontrado")

    tier = _computed_tier(country)
    detail = copy.deepcopy(country)
    detail["code"] = normal
    detail["tier"] = tier
    detail["color"] = color_for_tier(tier)
    return detail
