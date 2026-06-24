import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SavingsGoalCard } from "@/components/metas/SavingsGoalCard";
import type { SavingsGoal } from "@/lib/types";
import { PrivacyProvider } from "@/providers/PrivacyProvider";

const goal: SavingsGoal = {
  id: 1,
  name: "Viagem",
  target_amount: 3000,
  term_months: 6,
  saved_amount: 500,
  saved_manual: 500,
  saved_from_tx: 250,
  saved_total: 750,
  linked_count: 2,
  priority: 1,
  monthly_required: 375,
  progress_pct: 25,
  fits_surplus: true,
};

describe("SavingsGoalCard", () => {
  it("renders saved total and reconciliation entrypoint", () => {
    const html = renderToStaticMarkup(
      <PrivacyProvider>
        <SavingsGoalCard
          goal={goal}
          onEdit={() => undefined}
          onDelete={() => undefined}
          onReconcile={() => undefined}
        />
      </PrivacyProvider>,
    );

    expect(html).toContain("Guardado");
    expect(html).toContain("R$ 750,00");
    expect(html).toContain("manual + R$ 250,00 em lançamentos");
    expect(html).toContain("2 lançamentos");
    expect(html).toContain('href="/transacoes?savings_goal_id=1"');
    expect(html).toContain("Conciliar");
  });
});
