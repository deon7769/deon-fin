"""Anonimização de descrições antes de enviar a uma LLM externa.

A análise por IA envia apenas agregados (ver context.py), mas descrições de
transferências costumam carregar nomes de pessoas (ex.: "Pix recebido FULANO DE
TAL"). Este módulo remove PII — CPF, número de conta/agência e nomes em PIX/TED —
substituindo por placeholders genéricos, seguindo a boa prática de nunca enviar
dados sigilosos a serviços externos.
"""

from __future__ import annotations

import re

# CPF: 000.000.000-00 ou 00000000000
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
# CNPJ: 00.000.000/0000-00
_CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
# Agência/conta tipo 341/0292/00012354-4 ou 0001/12345-0
_ACCOUNT = re.compile(r"\b\d{3,4}/\d{3,4}/?\d{2,9}-?\d?\b")
# Cartão mascarado ou número longo (>= 6 dígitos seguidos)
_LONG_DIGITS = re.compile(r"\b\d{6,}\b")

# Verbos de transferência seguidos de um nome próprio (sequência de palavras
# capitalizadas / em caixa alta). Cobre os formatos do Pluggy:
#   "Pix recebido FULANO DE TAL", "Pix enviado Maria Silva",
#   "Transferência Recebida|JOAO", "Transferência Pix - Beltrano"
_TRANSFER_NAME = re.compile(
    r"(?P<verbo>"
    r"pix\s+(?:recebido|enviado)"
    r"|transfer[êe]ncia\s+(?:recebida|enviada|pix)?"
    r"|ted\s+(?:recebid[ao]|enviad[ao])?"
    r"|doc\s+(?:recebid[ao]|enviad[ao])?"
    r"|pagamento\s+(?:de\s+)?pix"
    r")"
    r"[\s:|/-]*"
    r"(?P<nome>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.']*(?:\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.']*){0,5})",
    re.IGNORECASE,
)

_PLACEHOLDER = "<pessoa>"


def anonymize(text: str | None) -> str:
    """Remove PII de uma descrição de transação."""
    if not text:
        return ""
    out = text
    out = _CPF.sub("<cpf>", out)
    out = _CNPJ.sub("<cnpj>", out)
    out = _ACCOUNT.sub("<conta>", out)

    def _mask_name(m: re.Match[str]) -> str:
        return f"{m.group('verbo')} {_PLACEHOLDER}"

    out = _TRANSFER_NAME.sub(_mask_name, out)
    # Qualquer sequência numérica longa restante (cartões, ids) vira <num>
    out = _LONG_DIGITS.sub("<num>", out)
    return re.sub(r"\s{2,}", " ", out).strip()
