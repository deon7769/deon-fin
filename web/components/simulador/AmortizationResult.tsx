import { amortizationRows, type ResultTone } from "@/lib/simulator";
import type { AmortizationResponse } from "@/lib/types";
import { cn } from "@/lib/cn";

type AmortizationResultProps = {
  result: AmortizationResponse;
};

const toneClasses: Record<ResultTone, string> = {
  neutral: "text-text",
  positive: "text-positive",
  negative: "text-negative",
};

export function AmortizationResult({ result }: AmortizationResultProps) {
  const rows = amortizationRows(result);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-sm">
        <thead className="text-xs uppercase text-muted">
          <tr className="border-b border-border">
            <th className="pb-3 font-semibold">Cenário</th>
            <th className="pb-3 text-right font-semibold">Prazo</th>
            <th className="pb-3 text-right font-semibold">Juros pagos</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-b border-border last:border-b-0">
              <td className="py-3 font-medium text-text">{row.label}</td>
              <td className={cn("py-3 text-right tabular-nums", toneClasses[row.tone])}>
                {row.months}
              </td>
              <td className={cn("py-3 text-right font-semibold tabular-nums", toneClasses[row.tone])}>
                {row.interest}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
