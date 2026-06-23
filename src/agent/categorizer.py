from __future__ import annotations

import re
from dataclasses import dataclass

from ..storage import Database


@dataclass(frozen=True)
class Rule:
    category: str
    pattern: re.Pattern[str]


def _rule(category: str, pattern: str) -> Rule:
    return Rule(category=category, pattern=re.compile(pattern, re.IGNORECASE))


# Regras iniciais baseadas em comerciantes/keywords comuns no BR.
# A ordem importa: primeira regra que casar vence.
DEFAULT_RULES: list[Rule] = [
    _rule(
        "Pagamento de fatura",
        r"\b(pagamento\s+(?:de\s+)?fatura|pagamento\s+(?:do\s+)?cart[aã]o|"
        r"pagamento\s+on\s*line|pagamento\s+online|pgto\s+fatura)\b",
    ),
    _rule("Alimentação - Restaurante", r"\b(ifood|rappi|uber\s*eats|restaurante|burger|pizza|sushi|hambur)\b"),
    _rule("Alimentação - Mercado",     r"\b(carrefour|p[aã]o de a[cç][uú]car|extra|assa[ií]|atacad[aã]o|mercado|hortifruti|sams\s*club|big\b|tenda)\b"),
    _rule("Transporte - App",          r"\b(uber|99\s*app|99pay|99\s*pop|cabify|in\s*drive)\b"),
    _rule("Transporte - Combustível",  r"\b(posto|shell|ipiranga|petrobr[aá]s|ale\s*combust)\b"),
    _rule("Transporte - Estacionamento", r"\b(estacion|zona\s*azul|estapar|multipark)\b"),
    _rule("Assinaturas - Streaming",   r"\b(netflix|spotify|youtube\s*premium|amazon\s*prime|disney|hbo|globoplay|deezer|apple\s*(music|tv))\b"),
    _rule("Assinaturas - Software",    r"\b(adobe|github|openai|anthropic|claude|cursor|figma|notion|jetbrains|microsoft\s*365|google\s*one|icloud)\b"),
    _rule("Moradia - Aluguel",         r"\b(aluguel|locacao|imobili[aá]ria)\b"),
    _rule("Moradia - Contas",          r"\b(enel|cpfl|cemig|copel|sabesp|cedae|comgas|net\b|claro|vivo\b|tim\b|oi\b|sky)\b"),
    _rule("Saúde - Farmácia",          r"\b(drog(a|aria)|farm[aá]cia|raia|pacheco|panvel|onofre|venancio)\b"),
    _rule("Saúde - Plano/Consulta",    r"\b(unimed|amil|hapvida|bradesco\s*sa[uú]de|sulamerica\s*sa[uú]de|consulta|cl[ií]nica|hospital)\b"),
    _rule("Lazer - Cinema/Show",       r"\b(cinemark|kinoplex|ingresso|sympla|eventim|cinepolis)\b"),
    _rule("Compras - E-commerce",      r"\b(amazon|americanas|magaz(ine|inel)|mercado\s*livre|shopee|aliexpress|shein)\b"),
    _rule("Educação",                  r"\b(udemy|alura|coursera|edx|fgv|escola|faculdade|universidade|colegio)\b"),
    _rule("Transferências - PIX",      r"\bpix\b"),
    _rule("Transferências - TED/DOC",  r"\bted\b|\bdoc\b"),
    _rule("Tarifas Bancárias",         r"\b(tarifa|anuidade|iof|juros|encargos|manutencao)\b"),
    _rule("Renda - Salário",           r"\bsal[aá]rio|pagamento\s*funcionario|folha\b"),
    _rule("Investimentos",             r"\b(tesouro|cdb|lci|lca|aplicacao|resgate|xp\b|rico\b|nuinvest|btg)\b"),
]


class Categorizer:
    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules = rules if rules is not None else DEFAULT_RULES

    def classify(self, description: str) -> str | None:
        for rule in self.rules:
            if rule.pattern.search(description):
                return rule.category
        return None

    def apply_to_database(self, db: Database, *, overwrite_pluggy: bool = False) -> dict[str, int]:
        """Aplica regras a todas as transações sem categoria.

        overwrite_pluggy: se True, sobrescreve categorias vindas do Pluggy também.
        """
        stats = {"updated": 0, "unmatched": 0, "skipped": 0}
        with db._cursor() as cur:  # type: ignore[attr-defined]
            if overwrite_pluggy:
                cur.execute("SELECT id, description, raw_description, category_source FROM transactions")
            else:
                cur.execute(
                    """SELECT id, description, raw_description, category_source FROM transactions
                       WHERE category IS NULL OR category = ''"""
                )
            rows = cur.fetchall()

            for row in rows:
                text = (row["raw_description"] or row["description"] or "").strip()
                category = self.classify(text)
                if category is None:
                    stats["unmatched"] += 1
                    continue
                if not overwrite_pluggy and row["category_source"] == "pluggy":
                    stats["skipped"] += 1
                    continue
                cur.execute(
                    "UPDATE transactions SET category=?, category_source='rule' WHERE id=?",
                    (category, row["id"]),
                )
                stats["updated"] += 1
        return stats
