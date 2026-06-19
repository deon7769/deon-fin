"""Analista financeiro pessoal por IA (multi-provedor).

Recebe o resumo agregado de context.build_financial_context e gera análises em
português: orçamento 50/30/20, auditoria de desperdícios e plano de metas.
Só agregados anonimizados são enviados ao provedor.

Suporta dois back-ends:
- "anthropic": SDK nativo da Claude (adaptive thinking, effort).
- compatíveis com OpenAI ("openrouter", "ollama", "gemini", "zai", "openai"):
  usa o SDK `openai` apontando para o base_url do provedor.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from ..config import Settings

SYSTEM_PROMPT = """\
Você é um analista financeiro pessoal brasileiro: didático, direto e prático.
Regras:
- Trabalhe sempre em reais (R$), formato brasileiro (R$ 1.234,56).
- Baseie-se SOMENTE nos dados fornecidos. Nunca invente números; se faltar um
  dado, declare a suposição que está fazendo.
- A renda a usar é `renda_mensal_informada`. A renda detectada no extrato é ruído
  (PIX/transferências mal classificados) — não a use como renda.
- Explique de forma simples; ao tocar em tema técnico (juros, investimento),
  resuma "como se a pessoa tivesse 15 anos".
- Os valores de gasto estão em regime de competência (compras de cartão +
  débitos), já excluindo transferências internas, aportes e pagamento de fatura.
- CRÍTICO sobre mensal vs. total: em comparações mensais (como a regra 50/30/20),
  use SEMPRE os valores MÉDIOS MENSAIS — `media_mensal` de cada categoria e
  `media_gasto_mensal` no agregado. NUNCA use o campo `total` (que soma vários
  meses) para comparar com a renda mensal, senão o resultado fica inflado.
- Perfil Familiar: Se fornecido em `perfil_familiar`, utilize as informações detalhadas de receitas individuais, provisões mensais (como veículo, pneus, SESI), metas (ex.: quitação de financiamento) e patrimônio consolidado (ex.: fluxo líquido de aluguel e saldo devedor do imóvel) para enriquecer o diagnóstico e guiar as recomendações de poupança, amortização e alocação de caixa.
- Formate em Markdown com seções curtas e tabelas quando ajudar. Seja específico:
  cite categorias e valores reais dos dados.
"""

_PROMPTS = {
    "budget": """\
Monte um **orçamento pela regra 50/30/20** (50% essenciais, 30% desejos, 20%
poupança/investimento e quitação de dívidas) com base na renda informada.
1. Classifique as categorias de gasto em Essenciais / Desejos / Poupança-Dívida.
2. Mostre quanto cada bloco deveria custar (R$ e %) vs. quanto está custando hoje.
3. Aponte onde a pessoa está estourando e o tamanho do desvio.
4. Dê 3 a 5 ações concretas para encaixar no 50/30/20.""",
    "waste": """\
Faça uma **auditoria de desperdícios** dos últimos meses.
1. Liste assinaturas/recorrências prováveis (use `recorrencias_provaveis`),
   destacando as estáveis (valor fixo todo mês) — candidatas a cancelar/renegociar.
2. Aponte tarifas, juros e custo financeiro (use `custo_financeiro`) e como zerá-los.
3. Identifique padrões de consumo onde dá para cortar ~20% sem perder qualidade
   de vida, com o valor estimado de economia mensal de cada corte.
4. Some o total que poderia ser economizado por mês.""",
    "goals": """\
Monte um **plano de metas** para os objetivos informados (`objetivos`).
1. Considerando renda menos gastos, estime a sobra mensal realista.
2. Defina a ordem de ataque dos objetivos (priorize quitar dívida cara e custo
   financeiro antes de investir; depois reserva de emergência de 3–6 meses de
   gastos; depois investir/viagem).
3. Para cada meta, diga quanto guardar por mês e em quanto tempo chega lá
   (pode simular juros simples de ~10% a.a. quando fizer sentido, explicando).
4. Entregue um plano de ação mês a mês para os próximos 3 meses.""",
    "all": """\
Gere um **relatório financeiro completo** com TRÊS seções, nesta ordem:

## 1. Orçamento 50/30/20
Classifique os gastos em Essenciais / Desejos / Poupança-Dívida; compare o ideal
(R$ e %) com o real; aponte os estouros e 3–5 ações.

## 2. Auditoria de desperdícios
Assinaturas/recorrências (destaque as estáveis), tarifas e juros, e onde cortar
~20% sem perder qualidade de vida — com economia mensal estimada e o total.

## 3. Plano de metas
Para os objetivos informados: sobra mensal realista, ordem de ataque (quitar
dívida cara → reserva de 3–6 meses → investir/viagem), quanto guardar por mês e
prazo de cada meta, e um plano de ação para os próximos 3 meses.

Comece com um parágrafo curto de diagnóstico geral (a foto da situação).""",
}

VALID_KINDS = tuple(_PROMPTS.keys())
DEFAULT_MAX_TOKENS = 16000


class AnalystError(RuntimeError):
    pass


def _user_prompt(kind: str, context: dict) -> str:
    if kind not in _PROMPTS:
        raise AnalystError(f"Tipo de análise inválido: {kind!r}. Use {VALID_KINDS}.")
    payload = json.dumps(context, ensure_ascii=False, indent=2)
    return (
        f"{_PROMPTS[kind]}\n\n"
        "Dados financeiros (agregados, em JSON):\n"
        f"```json\n{payload}\n```"
    )


class FinancialAnalyst:
    """Gera os relatórios via Anthropic ou um provedor compatível com OpenAI."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        api_key: str | None,
        base_url: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.max_tokens = max_tokens
        # Ollama é local e não exige chave; os demais sim.
        if not api_key and provider != "ollama":
            raise AnalystError(
                f"Chave de API não configurada para o provedor '{provider}'. "
                "Defina ANALYST_API_KEY (ou a chave específica do provedor) no .env.local."
            )
        if not model:
            raise AnalystError("ANALYST_MODEL não definido.")
        self._client = self._make_client(api_key)

    @classmethod
    def from_settings(cls, settings: "Settings") -> "FinancialAnalyst":
        return cls(
            provider=settings.analyst_provider,
            model=settings.analyst_model,
            api_key=settings.analyst_api_key,
            base_url=settings.analyst_base_url,
            max_tokens=settings.analyst_max_tokens,
        )

    # ------------------------------------------------------------------ client
    def _make_client(self, api_key: str | None):
        if self.provider == "anthropic":
            try:
                import anthropic
            except ImportError as e:  # pragma: no cover
                raise AnalystError("Pacote 'anthropic' não instalado.") from e
            return anthropic.Anthropic(api_key=api_key)
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover
            raise AnalystError(
                "Pacote 'openai' não instalado (necessário para provedores "
                "compatíveis com OpenAI). Rode: pip install openai"
            ) from e
        # OpenRouter recomenda headers de identificação (opcionais).
        headers = {}
        if self.provider == "openrouter":
            headers = {"HTTP-Referer": "http://localhost:8000", "X-Title": "Financas MVP"}
        return OpenAI(api_key=api_key or "ollama", base_url=self.base_url,
                      default_headers=headers or None)

    # ------------------------------------------------------------------ public
    def stream(self, kind: str, context: dict) -> Iterator[str]:
        """Gera o relatório em pedaços de texto (para a UI web e a CLI)."""
        prompt = _user_prompt(kind, context)
        if self.provider == "anthropic":
            yield from self._stream_anthropic(prompt)
        else:
            yield from self._stream_openai(prompt)

    def run(self, kind: str, context: dict) -> str:
        """Retorna o relatório completo como string."""
        return "".join(self.stream(kind, context))

    # ----------------------------------------------------------- backends
    def _stream_anthropic(self, prompt: str) -> Iterator[str]:
        import anthropic

        try:
            with self._client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                output_config={"effort": "high"},
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except anthropic.APIError as e:
            raise AnalystError(f"Falha na API da Claude: {e}") from e

    def _stream_openai(self, prompt: str) -> Iterator[str]:
        from openai import OpenAIError

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except OpenAIError as e:
            raise AnalystError(f"Falha na API ({self.provider}): {e}") from e
