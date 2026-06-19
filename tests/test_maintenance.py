from __future__ import annotations

from src.agent import maintenance as mnt


def test_translate_category_default_e_fallback():
    cat = mnt.load_overrides()["categorias_pt"]
    assert mnt.translate_category("Groceries", cat) == "Mercado"
    assert mnt.translate_category("gas stations", cat) == "Combustível"
    # categoria sem tradução volta como veio
    assert mnt.translate_category("Xyzland", cat) == "Xyzland"


def test_income_from_profile():
    assert mnt.income_from_profile(None) is None
    assert mnt.income_from_profile({"receitas": []}) is None
    prof = {"receitas": [{"membro": "A", "valor": 8867.0}, {"membro": "B", "valor": 6937.0}]}
    assert mnt.income_from_profile(prof) == 15804.0


def test_apply_recurrence_overrides_marca_e_ignora():
    recs = [
        {"comerciante": "netflix br", "estavel": True, "valor_medio": 39.9},
        {"comerciante": "transferencia enviada", "estavel": False, "valor_medio": 100.0},
        {"comerciante": "posto apolo", "estavel": False, "valor_medio": 200.0},
    ]
    rec_map = [
        {"match": "netflix", "tipo": "assinatura", "rotulo": "Netflix"},
        {"match": "transferencia", "tipo": "ignorar"},
        # posto apolo sem regra -> mantém, tipo derivado de estavel
    ]
    out = mnt.apply_recurrence_overrides(recs, rec_map)
    nomes = {r["comerciante"]: r for r in out}
    assert "transferencia enviada" not in nomes           # ignorado
    assert nomes["Netflix"]["tipo"] == "assinatura"        # rótulo aplicado
    assert nomes["posto apolo"]["tipo"] == "recorrencia"   # default p/ não-estável


def test_load_overrides_tem_defaults():
    ov = mnt.load_overrides()
    assert "categorias_pt" in ov and "recorrencias" in ov
    assert len(ov["categorias_pt"]) >= 40
