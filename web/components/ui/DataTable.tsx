import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";
import { Skeleton } from "./Skeleton";

export type DataTableColumn<T> = {
  key: string;
  header: ReactNode;
  cell?: (row: T) => ReactNode;
  className?: string;
};

type DataTableProps<T> = {
  columns: DataTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T, index: number) => string;
  loading?: boolean;
  empty?: ReactNode;
};

export function DataTable<T>({ columns, rows, getRowKey, loading = false, empty }: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (!rows.length) {
    return empty ?? <EmptyState title="Nenhum registro" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase text-muted">
            {columns.map((column) => (
              <th key={column.key} className={column.className ?? "px-3 py-3 font-semibold"}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={getRowKey(row, index)} className="border-b border-border last:border-0">
              {columns.map((column) => (
                <td key={column.key} className={column.className ?? "px-3 py-3 text-text"}>
                  {column.cell ? column.cell(row) : null}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
