"use client";

import { Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { emptyMaintenanceRow, type MaintenanceEditorState } from "@/lib/maintenance";

export type EditableColumn<Row extends Record<string, unknown>> = {
  key: Extract<keyof Row, string>;
  label: string;
  type: "text" | "number" | "select";
  options?: string[];
};

type EditableMaintenanceTableProps<K extends keyof MaintenanceEditorState> = {
  section: K;
  title: string;
  rows: MaintenanceEditorState[K];
  columns: EditableColumn<MaintenanceEditorState[K][number] & Record<string, unknown>>[];
  onChange: (rows: MaintenanceEditorState[K]) => void;
};

function parseInputValue(type: EditableColumn<Record<string, unknown>>["type"], value: string) {
  if (type !== "number") {
    return value;
  }
  if (value.trim() === "") {
    return 0;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function EditableMaintenanceTable<K extends keyof MaintenanceEditorState>({
  section,
  title,
  rows,
  columns,
  onChange,
}: EditableMaintenanceTableProps<K>) {
  const typedRows = rows as Array<Record<string, unknown>>;
  const inputClass =
    "h-9 w-full rounded-md border border-border bg-surface px-2 text-sm text-text outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20";

  const updateCell = (rowIndex: number, key: string, value: unknown) => {
    const nextRows = typedRows.map((row, index) =>
      index === rowIndex ? { ...row, [key]: value } : row,
    );
    onChange(nextRows as MaintenanceEditorState[K]);
  };

  const removeRow = (rowIndex: number) => {
    onChange(typedRows.filter((_, index) => index !== rowIndex) as MaintenanceEditorState[K]);
  };

  const addRow = () => {
    onChange([...typedRows, emptyMaintenanceRow(section)] as MaintenanceEditorState[K]);
  };

  const renderControl = (
    row: Record<string, unknown>,
    rowIndex: number,
    column: EditableColumn<Record<string, unknown>>,
    className?: string,
  ) => {
    const value = row[column.key];
    if (column.type === "select") {
      return (
        <select
          aria-label={`${title}: ${column.label}`}
          value={String(value ?? column.options?.[0] ?? "")}
          onChange={(event) => updateCell(rowIndex, column.key, event.currentTarget.value)}
          className={cn(inputClass, className)}
        >
          {(column.options ?? []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }
    return (
      <input
        aria-label={`${title}: ${column.label}`}
        type={column.type}
        step={column.type === "number" ? "0.01" : undefined}
        value={String(value ?? "")}
        onChange={(event) =>
          updateCell(rowIndex, column.key, parseInputValue(column.type, event.currentTarget.value))
        }
        className={cn(inputClass, className)}
      />
    );
  };

  if (columns.length > 4) {
    return (
      <div className="space-y-3" data-layout="cards">
        <div className="space-y-3">
          {typedRows.map((row, rowIndex) => (
            <div key={rowIndex} className="rounded-md border border-border bg-surface2 p-3">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-text">Linha {rowIndex + 1}</p>
                <button
                  type="button"
                  onClick={() => removeRow(rowIndex)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted transition hover:bg-negative/10 hover:text-negative"
                  title="Remover linha"
                  aria-label={`Remover linha de ${title}`}
                >
                  <Trash2 size={15} aria-hidden />
                </button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {columns.map((column) => (
                  <label key={column.key} className="space-y-1 text-xs font-medium text-muted">
                    <span>{column.label}</span>
                    {renderControl(row, rowIndex, column)}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addRow}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
        >
          <Plus size={15} aria-hidden />
          Adicionar linha
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[620px] text-left text-sm">
          <thead className="text-xs uppercase text-muted">
            <tr className="border-b border-border">
              {columns.map((column) => (
                <th key={column.key} className="pb-2 pr-3 font-semibold">
                  {column.label}
                </th>
              ))}
              <th className="w-12 pb-2 font-semibold" aria-label="Ações" />
            </tr>
          </thead>
          <tbody>
            {typedRows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b border-border last:border-b-0">
                {columns.map((column) => {
                  return (
                    <td key={column.key} className="py-2 pr-3">
                      {renderControl(row, rowIndex, column, "min-w-28")}
                    </td>
                  );
                })}
                <td className="py-2">
                  <button
                    type="button"
                    onClick={() => removeRow(rowIndex)}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted transition hover:bg-negative/10 hover:text-negative"
                    title="Remover linha"
                    aria-label={`Remover linha de ${title}`}
                  >
                    <Trash2 size={15} aria-hidden />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        onClick={addRow}
        className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-text transition hover:bg-surface2"
      >
        <Plus size={15} aria-hidden />
        Adicionar linha
      </button>
    </div>
  );
}
