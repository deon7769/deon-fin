import { scenarioSummary, type ResultTone } from "@/lib/simulator";
import type { ScenarioSimulationResponse } from "@/lib/types";
import { cn } from "@/lib/cn";

type ScenarioResultProps = {
  result: ScenarioSimulationResponse;
};

const toneClasses: Record<ResultTone, string> = {
  neutral: "text-text",
  positive: "text-positive",
  negative: "text-negative",
};

export function ScenarioResult({ result }: ScenarioResultProps) {
  const cards = scenarioSummary(result);

  return (
    <div className="grid gap-5 lg:grid-cols-3">
      {cards.map((card) => (
        <article key={card.key} className="min-w-0 space-y-4 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-semibold text-text">{card.title}</h3>
            <p className="mt-1 text-sm text-muted">{card.subtitle}</p>
          </div>
          <dl className="space-y-3">
            {card.items.map((item) => (
              <div key={item.label} className="flex items-start justify-between gap-3 text-sm">
                <dt className="text-muted">{item.label}</dt>
                <dd className={cn("text-right font-semibold tabular-nums", toneClasses[item.tone])}>
                  {item.value}
                </dd>
              </div>
            ))}
          </dl>
        </article>
      ))}
    </div>
  );
}
