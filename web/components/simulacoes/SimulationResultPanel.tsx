import { DataTable } from "@/components/ui/DataTable";
import { KpiCard } from "@/components/ui/KpiCard";
import { MoneyText } from "@/components/ui/MoneyText";
import { SectionCard } from "@/components/ui/SectionCard";
import { resultRows, summaryCards, type SimulationResponse } from "@/lib/simulacoes";
import { SimulationLineChart } from "./SimulationLineChart";

export function SimulationResultPanel({ result }: { result: SimulationResponse }) {
  const cards = summaryCards(result);
  const rows = resultRows(result);

  return (
    <div className="space-y-4">
      {result.avisos?.length ? (
        <div className="space-y-2">
          {result.avisos.map((aviso) => (
            <p
              key={aviso.code}
              className="rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning"
            >
              {aviso.message}
            </p>
          ))}
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-3">
        {cards.map((card) => (
          <KpiCard
            key={card.key}
            title={card.label}
            value={
              card.moneyValue === undefined ? (
                card.value
              ) : (
                <MoneyText value={card.moneyValue} />
              )
            }
          />
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
                {
                  key: "firstMetric",
                  header: "Métrica 1",
                  cell: (row) =>
                    row.firstMetricMoneyValue === undefined ? (
                      row.firstMetric
                    ) : (
                      <MoneyText value={row.firstMetricMoneyValue} />
                    ),
                },
                {
                  key: "secondMetric",
                  header: "Métrica 2",
                  cell: (row) =>
                    row.secondMetricMoneyValue === undefined ? (
                      row.secondMetric
                    ) : (
                      <MoneyText value={row.secondMetricMoneyValue} />
                    ),
                },
              ]}
            />
          </SectionCard>
        </>
      ) : null}
    </div>
  );
}
