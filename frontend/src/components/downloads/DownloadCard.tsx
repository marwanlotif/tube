import {
  AlertTriangle,
  FileX2,
  FolderOpen,
  Loader2,
  RotateCcw,
  Trash2,
  X,
} from "lucide-react";

import type { DownloadOut } from "@/api/models";
import {
  useDeleteDownload,
  useDownloadAction,
} from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  cn,
  formatBytes,
  formatEta,
  formatRelative,
  formatSpeed,
  shortContainer,
  statusMeta,
} from "@/lib/utils";

const ACTIVE = new Set([
  "queued",
  "extracting",
  "downloading",
  "processing",
  "verifying",
]);
const RETRYABLE = new Set(["failed", "canceled", "interrupted"]);

export function DownloadCard({ download }: { download: DownloadOut }) {
  const cancel = useDownloadAction("cancel");
  const retry = useDownloadAction("retry");
  const reveal = useDownloadAction("reveal");
  const remove = useDeleteDownload();

  const meta = statusMeta(download.status);
  const isActive = ACTIVE.has(download.status);
  const isIndeterminate = ["extracting", "processing", "verifying"].includes(
    download.status,
  );
  const speed = formatSpeed(download.speed);
  const eta = formatEta(download.eta_s);

  const removeFromList = () => remove.mutate({ id: download.id, deleteFile: false });
  const deleteFromDisk = () => {
    if (!window.confirm("Permanently delete this file from disk?")) return;
    remove.mutate({ id: download.id, deleteFile: true });
  };

  let progressLine: string | null = null;
  if (download.status === "downloading") {
    progressLine = [
      download.total_bytes
        ? `${formatBytes(download.downloaded_bytes)} / ${formatBytes(download.total_bytes)}`
        : formatBytes(download.downloaded_bytes),
      speed,
      eta,
    ]
      .filter(Boolean)
      .join(" · ");
  } else if (download.status === "queued") {
    progressLine = "Waiting for a free worker";
  } else if (download.status === "interrupted") {
    progressLine = download.resumable
      ? "Interrupted — retry to resume the partial file"
      : "Interrupted — retry to start over";
  } else if (download.status === "completed") {
    progressLine = [formatBytes(download.file_size), download.output_path]
      .filter(Boolean)
      .join(" · ");
  }

  return (
    <div
      className={cn(
        "rounded-xl border bg-panel/60 p-3.5 transition-colors sm:p-4",
        download.status === "failed"
          ? "border-[#3d2020]"
          : download.status === "interrupted"
            ? "border-[#3f321d]"
            : "border-edge-soft",
      )}
    >
      <div className="flex gap-3.5">
        <div className="hidden h-16 w-28 shrink-0 overflow-hidden rounded-md border border-edge-soft bg-surface sm:block">
          {download.thumbnail_url ? (
            <img
              src={download.thumbnail_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-[10px] text-faint">
              {shortContainer(download.container)}
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="line-clamp-1 min-w-0 flex-1 text-[13.5px] font-medium text-ink">
              {download.title ?? download.url}
            </h3>
            <div className="flex shrink-0 items-center gap-1.5">
              <Badge tone={meta.tone}>{meta.label}</Badge>
              {download.mode === "audio" ? (
                <Badge tone="muted">{shortContainer(download.container)}</Badge>
              ) : null}
            </div>
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-faint">
            {download.uploader ? <span className="truncate">{download.uploader}</span> : null}
            {download.format_label ? <span>{download.format_label}</span> : null}
            <span>{formatRelative(download.created_at)}</span>
            {download.attempts > 0 ? (
              <span>
                attempt {download.attempts + 1}
              </span>
            ) : null}
          </div>

          {isActive || download.status === "interrupted" ? (
            <div className="mt-2.5">
              <Progress
                value={download.progress}
                indeterminate={isIndeterminate || download.status === "queued"}
              />
              {progressLine ? (
                <p className="mt-1 truncate text-[11px] text-faint">{progressLine}</p>
              ) : null}
            </div>
          ) : progressLine ? (
            <p className="mt-1.5 truncate text-[11px] text-faint" title={progressLine}>
              {progressLine}
            </p>
          ) : null}

          {download.status === "failed" ? (
            <p className="mt-1.5 flex items-start gap-1.5 text-[11px] text-danger">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" />
              <span className="line-clamp-2">{download.error_message ?? "Download failed"}</span>
            </p>
          ) : null}
        </div>

        <div className="flex shrink-0 flex-col items-end justify-center gap-1">
          {isActive ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => cancel.mutate(download.id)}
              disabled={cancel.isPending}
            >
              {cancel.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <X size={13} />
              )}
              Cancel
            </Button>
          ) : null}
          {RETRYABLE.has(download.status) ? (
            <Button
              size="sm"
              variant="primary"
              onClick={() => retry.mutate(download.id)}
              disabled={retry.isPending}
            >
              {retry.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <RotateCcw size={13} />
              )}
              Retry
            </Button>
          ) : null}
          {download.status === "completed" ? (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => reveal.mutate(download.id)}
              disabled={reveal.isPending}
            >
              <FolderOpen size={13} /> Show
            </Button>
          ) : null}
          <div className="flex items-center gap-1">
            <Button
              size="icon"
              variant="ghost"
              title="Remove from list"
              aria-label="Remove from list"
              onClick={removeFromList}
              disabled={remove.isPending}
            >
              <Trash2 size={13} />
            </Button>
            {download.status === "completed" && download.output_path ? (
              <Button
                size="icon"
                variant="ghost"
                title="Delete file from disk"
                aria-label="Delete file from disk"
                onClick={deleteFromDisk}
                disabled={remove.isPending}
                className="hover:text-danger"
              >
                <FileX2 size={13} />
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      {remove.isError && !isActive ? (
        <p className="mt-2 text-[11px] text-danger">
          Could not remove: {remove.error instanceof Error ? remove.error.message : "error"}
        </p>
      ) : null}
    </div>
  );
}
