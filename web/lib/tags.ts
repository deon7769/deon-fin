import type { Tag } from "./types";

const HEX_COLOR_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

export function filterTags(tags: Tag[], query: string): Tag[] {
  const needle = normalize(query);
  if (!needle) {
    return tags;
  }
  return tags.filter((tag) => normalize(tag.name).includes(needle));
}

export function tagById(tags: Tag[], tagId: number | null | undefined): Tag | null {
  if (tagId === null || tagId === undefined) {
    return null;
  }
  return tags.find((tag) => tag.id === tagId) ?? null;
}

export function isValidTagColor(value: string): boolean {
  return HEX_COLOR_RE.test(value.trim());
}

export function normalizeTagColorInput(value: string | null | undefined): string | null {
  const normalized = (value ?? "").trim();
  if (!normalized) {
    return null;
  }
  if (!isValidTagColor(normalized)) {
    return normalized;
  }
  return normalized.toLowerCase();
}
