import type { Collection, DownloadOut } from "@/api/models";

/**
 * The downloads page lists standalone downloads and collections side by side. A
 * collection counts as one row: active while any item is, completed once every item is,
 * and needing attention while any item failed, was canceled or was interrupted.
 */

export type Filter = "all" | "active" | "completed" | "failed";

export type TimelineRow =
  | { type: "download"; id: string; download: DownloadOut }
  | { type: "collection"; id: string; collection: Collection };

const ACTIVE = new Set(["queued", "extracting", "downloading", "processing", "verifying"]);
const NEEDS_ATTENTION = new Set(["failed", "canceled", "interrupted"]);

export function isActive(row: TimelineRow): boolean {
  return row.type === "download"
    ? ACTIVE.has(row.download.status)
    : row.collection.active_total > 0;
}

export function matches(row: TimelineRow, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "active") return isActive(row);
  if (row.type === "download") {
    return filter === "completed"
      ? row.download.status === "completed"
      : NEEDS_ATTENTION.has(row.download.status);
  }
  const { completed_total, item_total, failed_total } = row.collection;
  return filter === "completed"
    ? item_total > 0 && completed_total === item_total
    : failed_total > 0;
}

function createdAt(row: TimelineRow): number {
  return new Date(
    row.type === "download" ? row.download.created_at : row.collection.created_at,
  ).getTime();
}

/** Active rows first, then newest first. */
export function buildTimeline(
  downloads: DownloadOut[],
  collections: Collection[],
): TimelineRow[] {
  const rows: TimelineRow[] = [
    ...downloads.map((download) => ({ type: "download" as const, id: download.id, download })),
    ...collections.map((collection) => ({
      type: "collection" as const,
      id: collection.id,
      collection,
    })),
  ];
  return rows.sort(
    (a, b) => Number(isActive(b)) - Number(isActive(a)) || createdAt(b) - createdAt(a),
  );
}

export function countByFilter(rows: TimelineRow[]): Record<Filter, number> {
  return {
    all: rows.length,
    active: rows.filter((row) => matches(row, "active")).length,
    completed: rows.filter((row) => matches(row, "completed")).length,
    failed: rows.filter((row) => matches(row, "failed")).length,
  };
}

/** "12 of 37 done · 2 downloading · 1 failed" */
export function collectionStatusLine(collection: Collection): string {
  const counts = collection.counts;
  const running =
    (counts.extracting ?? 0) +
    (counts.downloading ?? 0) +
    (counts.processing ?? 0) +
    (counts.verifying ?? 0);
  const parts = [`${collection.completed_total} of ${collection.item_total} done`];
  if (running) parts.push(`${running} downloading`);
  if (counts.queued) parts.push(`${counts.queued} queued`);
  if (counts.failed) parts.push(`${counts.failed} failed`);
  if (counts.canceled) parts.push(`${counts.canceled} canceled`);
  if (counts.interrupted) parts.push(`${counts.interrupted} interrupted`);
  return parts.join(" · ");
}
