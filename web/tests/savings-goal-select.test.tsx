import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SavingsGoalSelect } from "@/components/ui/SavingsGoalSelect";
import type { SavingsGoal } from "@/lib/types";

const goals: SavingsGoal[] = [
  {
    id: 1,
    name: "Viagem",
    target_amount: 8000,
    term_months: 12,
    saved_amount: 1200,
    priority: 1,
    monthly_required: 566.67,
    progress_pct: 15,
    fits_surplus: true,
    created_at: "2026-06-01T00:00:00",
    updated_at: "2026-06-01T00:00:00",
  },
  {
    id: 2,
    name: "Reserva",
    target_amount: 20000,
    term_months: 24,
    saved_amount: 5000,
    priority: 2,
    monthly_required: 625,
    progress_pct: 25,
    fits_surplus: true,
    created_at: "2026-06-01T00:00:00",
    updated_at: "2026-06-01T00:00:00",
  },
];

describe("SavingsGoalSelect", () => {
  it("renders the empty option and available savings goals", () => {
    const html = renderToStaticMarkup(
      <SavingsGoalSelect value={1} options={goals} onChange={() => undefined} />,
    );

    expect(html).toContain("Sem meta de poupança");
    expect(html).toContain("Viagem");
    expect(html).toContain("Reserva");
    expect(html).toContain("Meta de poupança");
    expect(html).toContain("value=\"1\" selected");
  });
});
