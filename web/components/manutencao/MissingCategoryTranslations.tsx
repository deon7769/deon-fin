import { EmptyState } from "@/components/ui/EmptyState";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { MoneyText } from "@/components/ui/MoneyText";
import type { MissingCategoryTranslationRow } from "@/lib/maintenance";

type MissingCategoryTranslationsProps = {
  rows: MissingCategoryTranslationRow[];
};

const columns: DataTableColumn<MissingCategoryTranslationRow>[] = [
  {
    key: "category",
    header: "Categoria",
    cell: (row) => <span className="font-medium text-text">{row.category}</span>,
  },
  {
    key: "txCount",
    header: "Transações",
    className: "min-w-[120px] px-3 py-3 text-right align-top",
    cell: (row) => <span className="tabular-nums text-text">{row.txCount}</span>,
  },
  {
    key: "totalAbs",
    header: "Movimento",
    className: "min-w-[130px] px-3 py-3 text-right align-top",
    cell: (row) => <MoneyText value={row.totalAbs} className="font-semibold" />,
  },
];

export function MissingCategoryTranslations({ rows }: MissingCategoryTranslationsProps) {
  return (
    <DataTable
      columns={columns}
      rows={rows}
      getRowKey={(row) => row.category}
      empty={<EmptyState title="Todas as categorias vistas já têm tradução" />}
    />
  );
}
