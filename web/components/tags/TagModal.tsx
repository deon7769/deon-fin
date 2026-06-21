"use client";

import { FormEvent, useState } from "react";
import { X } from "lucide-react";
import { isValidTagColor, normalizeTagColorInput } from "@/lib/tags";
import type { Tag } from "@/lib/types";

export const TAG_COLOR_PALETTE = [
  "#F5B301",
  "#EF4444",
  "#38BDF8",
  "#9F1239",
  "#3B82F6",
  "#F97316",
  "#A855F7",
  "#22C55E",
  "#06B6D4",
  "#9A9AA2",
];

type TagModalProps = {
  open: boolean;
  mode: "create" | "edit";
  tag?: Tag | null;
  saving?: boolean;
  error?: string | null;
  onClose: () => void;
  onSubmit: (input: { name: string; color: string | null }) => void | Promise<void>;
};

export function TagModal({
  open,
  mode,
  tag,
  saving = false,
  error = null,
  onClose,
  onSubmit,
}: TagModalProps) {
  if (!open) {
    return null;
  }

  return (
    <TagModalContent
      key={`${mode}-${tag?.id ?? "new"}`}
      mode={mode}
      tag={tag}
      saving={saving}
      error={error}
      onClose={onClose}
      onSubmit={onSubmit}
    />
  );
}

function TagModalContent({
  mode,
  tag,
  saving,
  error,
  onClose,
  onSubmit,
}: Omit<TagModalProps, "open">) {
  const [name, setName] = useState(tag?.name ?? "");
  const [color, setColor] = useState(tag?.color ?? TAG_COLOR_PALETTE[0]);
  const [localError, setLocalError] = useState<string | null>(null);
  const title = mode === "create" ? "Criar Tag" : "Editar Tag";
  const submitLabel = saving ? "Salvando..." : "Salvar";
  const normalizedColor = normalizeTagColorInput(color);
  const colorInvalid = Boolean(color.trim()) && !isValidTagColor(color);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedName = name.trim().replace(/\s+/g, " ");
    if (!normalizedName) {
      setLocalError("Informe um nome para a tag.");
      return;
    }
    if (normalizedName.length > 40) {
      setLocalError("Use no máximo 40 caracteres.");
      return;
    }
    if (colorInvalid) {
      setLocalError("Use uma cor hex como #F5B301.");
      return;
    }

    setLocalError(null);
    await onSubmit({
      name: normalizedName,
      color: normalizedColor,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="tag-modal-title"
        className="w-full max-w-md rounded-md border border-border bg-surface shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 id="tag-modal-title" className="text-base font-semibold text-text">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-muted transition hover:bg-surface2 hover:text-text"
          >
            <X size={17} aria-hidden />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4 px-5 py-5">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-text">Nome</span>
            <input
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                setLocalError(null);
              }}
              maxLength={40}
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none placeholder:text-muted focus:border-accent"
              placeholder="Ex.: Pets"
            />
          </label>

          <div className="space-y-3">
            <span className="text-sm font-medium text-text">Cor</span>
            <div className="grid grid-cols-10 gap-2">
              {TAG_COLOR_PALETTE.map((paletteColor) => {
                const selected = normalizeTagColorInput(paletteColor) === normalizedColor;
                return (
                  <button
                    key={paletteColor}
                    type="button"
                    aria-label={`Selecionar cor ${paletteColor}`}
                    aria-pressed={selected}
                    onClick={() => {
                      setColor(paletteColor);
                      setLocalError(null);
                    }}
                    className="h-7 w-7 rounded-full border border-border ring-offset-2 ring-offset-surface transition hover:scale-105 aria-pressed:ring-2 aria-pressed:ring-accent"
                    style={{ backgroundColor: paletteColor }}
                  />
                );
              })}
            </div>

            <input
              value={color}
              onChange={(event) => {
                setColor(event.target.value);
                setLocalError(null);
              }}
              className="h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text outline-none placeholder:text-muted focus:border-accent"
              placeholder="#F5B301"
            />
          </div>

          {localError || error ? (
            <p className="text-sm text-negative">{localError ?? error}</p>
          ) : null}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="h-10 rounded-md border border-border px-4 text-sm font-medium text-muted transition hover:bg-surface2 hover:text-text"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="h-10 rounded-md bg-accent px-4 text-sm font-semibold text-black transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
