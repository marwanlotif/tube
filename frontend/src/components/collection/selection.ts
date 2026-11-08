import type { CollectionCreated, CollectionEntry } from "@/api/models";

/** Pure helpers behind the playlist entry picker. */

export function videosOf(entries: CollectionEntry[]): CollectionEntry[] {
  return entries.filter((entry) => entry.kind === "video");
}

export function nestedOf(entries: CollectionEntry[]): CollectionEntry[] {
  return entries.filter((entry) => entry.kind === "collection" && entry.url);
}

/** Everything that can be downloaded starts selected. */
export function initialSelection(entries: CollectionEntry[]): Set<string> {
  return new Set(videosOf(entries).filter((e) => e.available).map((e) => e.id));
}

export function matchingEntries(entries: CollectionEntry[], query: string): CollectionEntry[] {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return entries;
  return entries.filter((entry) => entry.title.toLocaleLowerCase().includes(needle));
}

/** Select or clear the given (e.g. currently visible) entries, leaving the rest as is. */
export function setSelected(
  selection: Set<string>,
  entries: CollectionEntry[],
  selected: boolean,
): Set<string> {
  const next = new Set(selection);
  for (const entry of entries) {
    if (!entry.available) continue;
    if (selected) next.add(entry.id);
    else next.delete(entry.id);
  }
  return next;
}

export function toggle(selection: Set<string>, id: string): Set<string> {
  const next = new Set(selection);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}

/** Selected ids in playlist order, as the API expects them. */
export function selectedIds(entries: CollectionEntry[], selection: Set<string>): string[] {
  return videosOf(entries)
    .filter((entry) => entry.available && selection.has(entry.id))
    .map((entry) => entry.id);
}

export function totalDuration(entries: CollectionEntry[], selection: Set<string>): number {
  return entries
    .filter((entry) => selection.has(entry.id))
    .reduce((sum, entry) => sum + (entry.duration_s ?? 0), 0);
}

const SKIP_LABELS: Record<keyof CollectionCreated["skipped"], string> = {
  already_downloaded: "already downloaded",
  unavailable: "unavailable",
  not_found: "no longer in the playlist",
  blocked: "on a blocked host",
};

/** "3 already downloaded, 1 unavailable" — empty when nothing was skipped. */
export function describeSkipped(skipped: Partial<CollectionCreated["skipped"]>): string {
  return (Object.keys(SKIP_LABELS) as (keyof typeof SKIP_LABELS)[])
    .filter((reason) => (skipped[reason] ?? 0) > 0)
    .map((reason) => `${skipped[reason]} ${SKIP_LABELS[reason]}`)
    .join(", ");
}
