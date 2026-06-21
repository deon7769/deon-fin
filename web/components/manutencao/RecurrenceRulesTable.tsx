import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pill } from "@/components/ui/Pill";
import { recurrenceTypeLabel } from "@/lib/maintenance";
import type { MaintenanceOverrides } from "@/lib/types";

type RecurrenceRow = {
  match: string;
  tipo: string;
  rotulo: string;
};

type RecurrenceRulesTableProps = {
  overrides: MaintenanceOverrides;
  limit?: number;
};

const columns: DataTableColumn<RecurrenceRow>[] = [
  {
    key: "match",
    header: "Contém",
    cell: (row) => <span className="font-medium text-text">{row.match}</span>,
  },
  {
    key: "tipo",
    header: "Tipo",
    cell: (row) => <Pill>{recurrenceTypeLabel(row.tipo)}</Pill>,
  },
  {
    key: "rotulo",
    header: "Rótulo",
    cell: (row) => <span className="text-muted">{row.rotulo || "--"}</span>,
  },
];

export function RecurrenceRulesTable({ overrides, limit = 8 }: RecurrenceRulesTableProps) {
  const rows = (overrides.recorrencias ?? [])
    .filter((row) => row.match?.trim())
    .slice(0, limit)
    .map((row) => ({
      match: row.match ?? "",
      tipo: row.tipo ?? "recorrencia",
      rotulo: row.rotulo ?? "",
    }));

  return (
    <DataTable
      columns={columns}
      rows={rows}
      getRowKey={(row, index) => `${row.match}:${index}`}
      empty={<EmptyState title="Nenhuma regra de recorrência" />}
    />
  );
}
