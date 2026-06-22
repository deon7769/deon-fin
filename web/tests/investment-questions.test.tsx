import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { InvestmentQuestionsPanel } from "@/components/investimentos/InvestmentQuestionsPanel";
import { buildQuestionPayload, diagramLabel } from "@/lib/investments";
import type { InvestmentQuestionsResponse } from "@/lib/types";

const questions: InvestmentQuestionsResponse = {
  diagram_type: "acoes",
  questions: [
    {
      id: 1,
      diagram_type: "acoes",
      criterio: "Rentabilidade",
      pergunta: "ROE historico maior que 8%?",
      peso: 1,
      sort_order: 10,
      ativo: true,
    },
    {
      id: 2,
      diagram_type: "acoes",
      criterio: "Crescimento",
      pergunta: "CAGR de receita ou lucro maior que 5% em 5 anos?",
      peso: 2,
      sort_order: 20,
      ativo: false,
    },
  ],
};

describe("investment questions helpers", () => {
  it("normalizes question payload and labels diagrams", () => {
    expect(diagramLabel("acoes")).toBe("Acoes");
    expect(diagramLabel("imobiliario")).toBe("Imobiliario");
    expect(
      buildQuestionPayload({
        diagramType: "acoes",
        criterio: " Rentabilidade ",
        pergunta: "  ROE acima da meta?  ",
        peso: "1,5",
        sortOrder: "30",
        ativo: true,
      }),
    ).toEqual({
      diagram_type: "acoes",
      criterio: "Rentabilidade",
      pergunta: "ROE acima da meta?",
      peso: 1.5,
      sort_order: 30,
      ativo: true,
    });
  });
});

describe("InvestmentQuestionsPanel", () => {
  it("renders diagram toggle, questions table and actions", () => {
    const html = renderToStaticMarkup(
      <InvestmentQuestionsPanel
        diagramType="acoes"
        data={questions}
        saving={false}
        deletingId={null}
        restoring={false}
        onDiagramChange={() => undefined}
        onCreate={() => undefined}
        onUpdate={() => undefined}
        onDelete={() => undefined}
        onRestoreDefaults={() => undefined}
      />,
    );

    expect(html).toContain("Perguntas de Score");
    expect(html).toContain("Acoes");
    expect(html).toContain("Imobiliario");
    expect(html).toContain("ROE historico maior que 8%?");
    expect(html).toContain("Crescimento");
    expect(html).toContain("Inativa");
    expect(html).toContain("Restaurar padrao");
    expect(html).toContain("Adicionar pergunta");
  });
});
