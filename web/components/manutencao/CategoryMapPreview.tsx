import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import type { MaintenanceOverrides } from "@/lib/types";

type CategoryRow = {
  source: string;
  target: string;
};

type CategoryMapPreviewProps = {
  overrides: MaintenanceOverrides;
  limit?: number;
};

const columns: DataTableColumn<CategoryRow>[] = [
  {
    key: "source",
    header: "Origem",
    cell: (row) => <span className="font-medium text-text">{row.source}</span>,
  },
  {
    key: "target",
    header: "Tradução",
    cell: (row) => <span className="text-muted">{row.target}</span>,
  },
];

export function CategoryMapPreview({ overrides, limit = 10 }: CategoryMapPreviewProps) {
  const rows = Object.entries(overrides.categorias_pt ?? {})
    .filter(([source, target]) => source.trim() && target.trim())
    .slice(0, limit)
    .map(([source, target]) => ({ source, target }));

  return (
    <DataTable
      columns={columns}
      rows={rows}
      getRowKey={(row) => row.source}
      empty={<EmptyState title="Nenhuma tradução configurada" />}
    />
  );
}
