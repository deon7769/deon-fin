import { describe, expect, it } from "vitest";

import {
  bucketAllocationStatus,
  goalViabilityLabel,
  plannedKindLabel,
  sumBucketAllocationDraft,
  sumBadgeState,
  toBucketPlanPatch,
} from "@/lib/metas";

describe("metas helpers", () => {
  it("labels bucket planning modes", () => {
    expect(plannedKindLabel("percent")).toBe("Percentual");
    expect(plannedKindLabel("amount")).toBe("Valor fixo");
  });

  it("marks balanced percent plans as ok and mismatches as warning", () => {
    expect(sumBadgeState({ sum_percent: 100, warning: null })).toEqual({
      tone: "ok",
      label: "100% planejado",
    });
    expect(
      sumBadgeState({
        sum_percent: 90,
        warning: { code: "percent_total_mismatch", message: "fechar em 100%" },
      }),
    ).toEqual({ tone: "warning", label: "90% planejado" });
  });

  it("describes goal viability from monthly surplus", () => {
    expect(goalViabilityLabel({ fits_surplus: true, monthly_required: 250 })).toBe(
      "Cabe na sobra",
    );
    expect(goalViabilityLabel({ fits_surplus: false, monthly_required: 250 })).toBe(
      "Ajustar prazo",
    );
    expect(goalViabilityLabel({ fits_surplus: false, monthly_required: 0 })).toBe(
      "Concluída",
    );
  });

  it("normalizes bucket patch inputs", () => {
    expect(
      toBucketPlanPatch({
        name: "  Metas longas  ",
        color: "#ABC123",
        planned_kind: "amount",
        planned_value: "250,45",
      }),
    ).toEqual({
      name: "Metas longas",
      color: "#ABC123",
      planned_kind: "amount",
      planned_value: 250.45,
    });
    expect(
      toBucketPlanPatch({
        name: "Metas",
        color: "#ABC123",
        planned_kind: "amount",
        planned_value: "250.45",
      }).planned_value,
    ).toBe(250.45);
  });

  it("sums bucket allocation drafts and describes total status", () => {
    expect(sumBucketAllocationDraft({ 1: 25, 2: 30, 3: 45 })).toBe(100);
    expect(bucketAllocationStatus(100)).toEqual({
      state: "valid",
      message: "100% alocado",
      canSave: true,
    });
    expect(bucketAllocationStatus(92)).toEqual({
      state: "under",
      message: "Faltam 8% para 100%",
      canSave: false,
    });
    expect(bucketAllocationStatus(111)).toEqual({
      state: "over",
      message: "Excedeu 11% do total",
      canSave: false,
    });
  });
});
