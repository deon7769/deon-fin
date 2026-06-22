from __future__ import annotations

import pytest


def test_rating_tiers_and_colors_follow_spec():
    from src.agent.portfolio.country_ratings import color_for_tier, derive_tier_from_sp

    assert derive_tier_from_sp("AAA") == "top"
    assert derive_tier_from_sp("AA+") == "high"
    assert derive_tier_from_sp("A-") == "high"
    assert derive_tier_from_sp("BBB") == "medium"
    assert derive_tier_from_sp("BB-") == "medium"
    assert derive_tier_from_sp("B") == "speculative"
    assert derive_tier_from_sp("CCC+") == "speculative"
    assert derive_tier_from_sp("") == "nodata"

    assert color_for_tier("top") == "#2563EB"
    assert color_for_tier("high") == "#22C55E"
    assert color_for_tier("medium") == "#F59E0B"
    assert color_for_tier("speculative") == "#EF4444"
    assert color_for_tier("nodata") == "#3A3A3E"


def test_load_country_ratings_reads_seeded_dataset_once_per_process():
    from src.agent.portfolio.country_ratings import load_country_ratings

    first = load_country_ratings()
    second = load_country_ratings()

    assert first is second
    assert {"US", "BR", "DE", "IN", "RU", "JP", "CN", "GB", "CA", "AU", "MX"} <= set(first)
    assert first["US"]["ratings"]["sp"] == "AA+"
    assert first["BR"]["main_index"] == "Ibovespa"


def test_list_country_ratings_returns_light_map_payload():
    from src.agent.portfolio.country_ratings import list_country_ratings

    countries = list_country_ratings()
    by_code = {country["code"]: country for country in countries}

    assert by_code["DE"] == {
        "code": "DE",
        "name": "Alemanha",
        "tier": "top",
        "color": "#2563EB",
    }
    assert by_code["BR"] == {
        "code": "BR",
        "name": "Brasil",
        "tier": "medium",
        "color": "#F59E0B",
    }
    assert set(by_code["US"]) == {"code", "name", "tier", "color"}


def test_get_country_rating_is_case_insensitive_and_returns_detail():
    from src.agent.portfolio.country_ratings import get_country_rating

    brazil = get_country_rating("br")

    assert brazil["name"] == "Brasil"
    assert brazil["name_intl"] == "Brazil"
    assert brazil["ratings"] == {"sp": "BB", "moody": "Ba2", "fitch": "BB-"}
    assert brazil["tier"] == "medium"
    assert brazil["color"] == "#F59E0B"
    assert brazil["empresas"][0]["ticker"] == "VALE3"
    assert brazil["etfs"][0]["ticker"] == "BOVA11"


def test_get_country_rating_rejects_unknown_code():
    from src.agent.portfolio.country_ratings import get_country_rating

    with pytest.raises(ValueError, match="país não encontrado"):
        get_country_rating("ZZ")
