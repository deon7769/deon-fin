import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { formatBRL } from "@/lib/format";
import type { MaintenanceSection } from "@/lib/maintenance";

type MaintenanceSectionTableProps = {
  rows: MaintenanceSection[];
};

const columns: DataTableColumn<MaintenanceSection>[] = [
  {
    key: "section",
    header: "Seção",
    cell: (row) => (
      <div className="min-w-0">
        <p className="font-medium text-text">{row.label}</p>
        <p className="mt-1 text-xs text-muted">{row.description}</p>
      </div>
    ),
  },
  {
    key: "count",
    header: "Registros",
    className: "px-3 py-3 text-right",
    cell: (row) => <span className="text-muted">{row.count}</span>,
  },
  {
    key: "total",
    header: "Total",
    className: "px-3 py-3 text-right",
    cell: (row) => (
      <span className="font-medium text-text">
        {row.total === null ? "--" : formatBRL(row.total)}
      </span>
    ),
  },
];

export function MaintenanceSectionTable({ rows }: MaintenanceSectionTableProps) {
  return (
    <DataTable
      columns={columns}
      rows={rows}
      getRowKey={(row) => row.key}
    />
  );
}
