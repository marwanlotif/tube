import { Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { DownloadOut } from "@/api/models";
import { useDownloads, useStats } from "@/api/queries";
import { DownloadCard } from "@/components/downloads/DownloadCard";
import { StatsBar } from "@/components/downloads/StatsBar";
import { cn } from "@/lib/utils";

type Filter = "all" | "active" | "completed" | "failed";

const ACTIVE = new Set(["queued", "extracting", "downloading", "processing", "verifying"]);
const FAILED = new Set(["failed", "canceled", "interrupted"]);

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "completed", label: "Completed" },
  { key: "failed", label: "Needs attention" },
];

function matches(download: DownloadOut, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "active") return ACTIVE.has(download.status);
  if (filter === "completed") return download.status === "completed";
  return FAILED.has(download.status);
}

export function DownloadsPage() {
  const { data, isLoading, isError, error } = useDownloads();
  const { data: stats } = useStats();
  const [filter, setFilter] = useState<Filter>("all");

  const items = useMemo(() => {
    const rows = [...(data?.items ?? [])];
    rows.sort((a, b) => {
      const activeDelta = Number(ACTIVE.has(b.status)) - Number(ACTIVE.has(a.status));
      if (activeDelta !== 0) return activeDelta;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return rows;
  }, [data]);

  const counts: Record<Filter, number> = {
    all: items.length,
    active: items.filter((item) => ACTIVE.has(item.status)).length,
    completed: items.filter((item) => item.status === "completed").length,
    failed: items.filter((item) => FAILED.has(item.status)).length,
  };
  const visible = items.filter((item) => matches(item, filter));

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
      ) : isError ? (
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
          {visible.map((download) => (
            <DownloadCard key={download.id} download={download} />
          ))}
        </div>
      )}
    </div>
  );
}
