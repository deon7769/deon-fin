import type { Bucket } from "./types";

function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

export function filterBuckets(buckets: Bucket[], query: string): Bucket[] {
  const needle = normalize(query);
  if (!needle) {
    return buckets;
  }
  return buckets.filter((bucket) => normalize(bucket.name).includes(needle));
}

export function bucketById(buckets: Bucket[], bucketId: number | null | undefined): Bucket | null {
  if (bucketId === null || bucketId === undefined) {
    return null;
  }
  return buckets.find((bucket) => bucket.id === bucketId) ?? null;
}
