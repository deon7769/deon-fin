import { DataTable } from "@/components/ui/DataTable";
import { KpiCard } from "@/components/ui/KpiCard";
import { SectionCard } from "@/components/ui/SectionCard";
import { resultRows, summaryCards, type SimulationResponse } from "@/lib/simulacoes";
import { SimulationLineChart } from "./SimulationLineChart";

export function SimulationResultPanel({ result }: { result: SimulationResponse }) {
  const cards = summaryCards(result);
  const rows = resultRows(result);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        {cards.map((card) => (
          <KpiCard key={card.key} title={card.label} value={card.value} />
        ))}
      </div>

      {rows.length ? (
        <>
          <SectionCard title="Gráfico" subtitle="Evolução das duas métricas principais">
            <SimulationLineChart result={result} />
          </SectionCard>
          <SectionCard title="Série mensal" subtitle={`${rows.length} linha(s)`}>
            <DataTable
              rows={rows}
              getRowKey={(row) => row.key}
              columns={[
                { key: "month", header: "Mês", cell: (row) => row.month },
                { key: "firstMetric", header: "Métrica 1", cell: (row) => row.firstMetric },
                { key: "secondMetric", header: "Métrica 2", cell: (row) => row.secondMetric },
              ]}
            />
          </SectionCard>
        </>
      ) : null}
    </div>
  );
}
