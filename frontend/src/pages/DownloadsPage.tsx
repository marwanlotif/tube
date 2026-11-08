import { Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useCollections, useDownloads, useStats } from "@/api/queries";
import { CollectionCard } from "@/components/downloads/CollectionCard";
import { DownloadCard } from "@/components/downloads/DownloadCard";
import { StatsBar } from "@/components/downloads/StatsBar";
import {
  buildTimeline,
  countByFilter,
  type Filter,
  matches,
} from "@/components/downloads/timeline";
import { cn } from "@/lib/utils";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "completed", label: "Completed" },
  { key: "failed", label: "Needs attention" },
];

export function DownloadsPage() {
  const downloads = useDownloads({ standalone: true });
  const collections = useCollections();
  const { data: stats } = useStats();
  const [filter, setFilter] = useState<Filter>("all");

  const rows = useMemo(
    () => buildTimeline(downloads.data?.items ?? [], collections.data?.items ?? []),
    [downloads.data, collections.data],
  );
  const counts = countByFilter(rows);
  const visible = rows.filter((row) => matches(row, filter));
  const isLoading = downloads.isLoading || collections.isLoading;
  const error = downloads.error ?? collections.error;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Downloads</h1>
          <p className="mt-0.5 text-sm text-muted">
            {stats?.active_total
              ? `${stats.active_total} active — progress updates live`
              : "Queue is idle"}
          </p>
        </div>
        <Link
          to="/"
          className="rounded-lg border border-edge bg-raised px-3.5 py-2 text-[13px] font-medium text-ink transition-colors hover:border-[#39414d]"
        >
          New download
        </Link>
      </header>

      <StatsBar />

      <div className="flex flex-wrap gap-1 border-b border-edge-soft pb-2">
        {FILTERS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setFilter(item.key)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
              filter === item.key
                ? "bg-white/[0.06] text-ink"
                : "text-muted hover:bg-white/[0.03] hover:text-ink",
            )}
          >
            {item.label}
            <span
              className={cn(
                "rounded px-1 text-[11px] tabular",
                filter === item.key ? "bg-white/10 text-ink" : "text-faint",
              )}
            >
              {counts[item.key]}
            </span>
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center gap-2 rounded-xl border border-edge-soft bg-panel/40 py-16 text-sm text-muted">
          <Loader2 size={15} className="animate-spin" /> Loading downloads
        </div>
      ) : error ? (
        <div className="rounded-xl border border-[#3d2020] bg-[#1c1010] p-5 text-sm text-danger">
          Could not load downloads: {error instanceof Error ? error.message : "unknown error"}
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-xl border border-dashed border-edge bg-panel/30 px-6 py-16 text-center">
          <p className="text-sm font-medium text-ink">
            {filter === "all"
              ? "Nothing downloaded yet"
              : filter === "active"
                ? "Nothing in the queue"
                : filter === "completed"
                  ? "No completed downloads"
                  : "Nothing needs attention"}
          </p>
          <p className="mx-auto mt-1 max-w-xs text-xs leading-relaxed text-muted">
            {filter === "all"
              ? "Paste a link on the downloader page to add your first file."
              : "Switch tabs to see the rest of your downloads."}
          </p>
          {filter === "all" ? (
            <Link
              to="/"
              className="mt-4 inline-block text-[13px] font-medium text-accent hover:underline"
            >
              Open the downloader
            </Link>
          ) : null}
        </div>
      ) : (
        <div className="space-y-2.5">
          {visible.map((row) =>
            row.type === "collection" ? (
              <CollectionCard key={row.id} collection={row.collection} />
            ) : (
              <DownloadCard key={row.id} download={row.download} />
            ),
          )}
        </div>
      )}
    </div>
  );
}
