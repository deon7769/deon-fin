import type { PainelTagSlice } from "./types";

export function hasUntaggedSlice(items: PainelTagSlice[]): boolean {
  return items.some((item) => item.tag_id === null && item.total > 0);
}
