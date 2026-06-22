import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { InvestmentTargetsPanel } from "@/components/investimentos/InvestmentTargetsPanel";
import {
  investmentTargetStatus,
  sumInvestmentTargets,
  targetsFromProfile,
} from "@/lib/investments";
import type { InvestmentProfilePreset, InvestmentTargetsResponse } from "@/lib/types";

const profiles: InvestmentProfilePreset[] = [
  {
    key: "moderado",
    label: "Moderado",
    description: "Equilibrado",
    targets: {
      rf: 35,
      rf_int: 5,
      acoes_nac: 20,
      acoes_int: 15,
      fii: 15,
      reit: 5,
      cripto: 5,
    },
  },
];

const targets: InvestmentTargetsResponse = {
  targets: {
    rf: 35,
    rf_int: 5,
    acoes_nac: 20,
    acoes_int: 15,
    fii: 15,
    reit: 5,
    cripto: 5,
  },
  classes: [
    { asset_class: "rf", label: "Renda fixa", target_pct: 35 },
    { asset_class: "rf_int", label: "Renda fixa internacional", target_pct: 5 },
    { asset_class: "acoes_nac", label: "Ações nacionais", target_pct: 20 },
    { asset_class: "acoes_int", label: "Ações internacionais", target_pct: 15 },
    { asset_class: "fii", label: "Fundos imobiliários", target_pct: 15 },
    { asset_class: "reit", label: "REITs", target_pct: 5 },
    { asset_class: "cripto", label: "Criptomoedas", target_pct: 5 },
  ],
  perfil: "moderado",
  ultimo_aporte: null,
  sum_pct: 100,
  valid: true,
};

describe("investment target helpers", () => {
  it("sums targets and describes under, valid and overflow states", () => {
    expect(sumInvestmentTargets({ rf: 60, acoes_nac: 20 })).toBe(80);
    expect(investmentTargetStatus(80)).toEqual({
      state: "under",
      message: "Faltam 20% para 100%",
      canSave: false,
    });
    expect(investmentTargetStatus(100).canSave).toBe(true);
    expect(investmentTargetStatus(112).message).toBe(
      "O valor ultrapassou 12% do valor das metas",
    );
  });

  it("copies preset targets without sharing references", () => {
    const first = targetsFromProfile(profiles[0]);
    first.rf = 10;

    expect(targetsFromProfile(profiles[0]).rf).toBe(35);
  });
});

describe("InvestmentTargetsPanel", () => {
  it("renders total, presets, sliders and disables save outside 100%", () => {
    const html = renderToStaticMarkup(
      <InvestmentTargetsPanel
        targets={{
          ...targets,
          targets: { ...targets.targets, rf: 50 },
          sum_pct: 115,
          valid: false,
        }}
        profiles={profiles}
        saving={false}
        onSave={() => undefined}
      />,
    );

    expect(html).toContain("Metas de Investimento");
    expect(html).toContain("Moderado");
    expect(html).toContain("Total: 115%");
    expect(html).toContain("O valor ultrapassou 15% do valor das metas");
    expect(html).toContain("Renda fixa");
    expect(html).toContain("disabled");
  });
});
