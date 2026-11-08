import {
  ChevronDown,
  ChevronRight,
  FileX2,
  ListVideo,
  Loader2,
  RotateCcw,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";

import type { Collection } from "@/api/models";
import {
  useCollectionAction,
  useDeleteCollection,
  useDownloads,
} from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn, errorMessage, formatRelative } from "@/lib/utils";

import { DownloadCard } from "./DownloadCard";
import { collectionStatusLine } from "./timeline";

function CollectionItems({ collectionId }: { collectionId: string }) {
  const { data, isLoading, isError, error } = useDownloads({ collectionId });
  if (isLoading) {
    return (
      <p className="flex items-center gap-2 py-3 text-xs text-muted">
        <Loader2 size={13} className="animate-spin" /> Loading videos
      </p>
    );
  }
  if (isError) {
    return <p className="py-3 text-xs text-danger">Could not load videos: {errorMessage(error)}</p>;
  }
  return (
    <div className="space-y-2">
      {(data?.items ?? []).map((download) => (
        <DownloadCard key={download.id} download={download} />
      ))}
    </div>
  );
}

export function CollectionCard({ collection }: { collection: Collection }) {
  const [expanded, setExpanded] = useState(false);
  const cancel = useCollectionAction("cancel");
  const retry = useCollectionAction("retry");
  const remove = useDeleteCollection();

  const active = collection.active_total > 0;
  const kindLabel = collection.collection_type === "channel" ? "Channel" : "Playlist";
  const failure = cancel.error ?? retry.error ?? remove.error;

  const deleteFromDisk = () => {
    if (!window.confirm(`Permanently delete the downloaded files of "${collection.title}"?`)) {
      return;
    }
    remove.mutate({ id: collection.id, deleteFiles: true });
  };

  return (
    <div
      className={cn(
        "rounded-xl border bg-panel/60 p-3.5 transition-colors sm:p-4",
        collection.failed_total > 0 && !active ? "border-[#3f321d]" : "border-edge-soft",
      )}
    >
      <div className="flex gap-3.5">
        <div className="hidden h-16 w-28 shrink-0 overflow-hidden rounded-md border border-edge-soft bg-surface sm:block">
          {collection.thumbnail_url ? (
            <img
              src={collection.thumbnail_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-faint">
              <ListVideo size={18} />
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="line-clamp-1 min-w-0 flex-1 text-[13.5px] font-medium text-ink">
              {collection.title ?? collection.url}
            </h3>
            <div className="flex shrink-0 items-center gap-1.5">
              <Badge tone={active ? "accent" : "muted"}>{kindLabel}</Badge>
              {collection.mode === "audio" ? <Badge tone="muted">Audio</Badge> : null}
            </div>
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-faint">
            {collection.uploader ? <span className="truncate">{collection.uploader}</span> : null}
            <span>{collectionStatusLine(collection)}</span>
            <span>{formatRelative(collection.created_at)}</span>
          </div>

          {active ? (
            <div className="mt-2.5">
              <Progress value={collection.progress} />
            </div>
          ) : collection.output_dir ? (
            <p
              className="mt-1.5 truncate text-[11px] text-faint"
              title={collection.output_dir}
            >
              {collection.output_dir}
            </p>
          ) : null}

          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            className="mt-2 inline-flex items-center gap-1 text-[11px] text-muted transition-colors hover:text-ink"
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {expanded ? "Hide videos" : `Show ${collection.item_total} videos`}
          </button>
        </div>

        <div className="flex shrink-0 flex-col items-end justify-center gap-1">
          {active ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => cancel.mutate(collection.id)}
              disabled={cancel.isPending}
            >
              {cancel.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <X size={13} />
              )}
              Cancel all
            </Button>
          ) : null}
          {collection.failed_total > 0 ? (
            <Button
              size="sm"
              variant="primary"
              onClick={() => retry.mutate(collection.id)}
              disabled={retry.isPending}
            >
              {retry.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <RotateCcw size={13} />
              )}
              Retry {collection.failed_total}
            </Button>
          ) : null}
          {!active ? (
            <div className="flex items-center gap-1">
              <Button
                size="icon"
                variant="ghost"
                title="Remove from list"
                aria-label="Remove from list"
                onClick={() => remove.mutate({ id: collection.id, deleteFiles: false })}
                disabled={remove.isPending}
              >
                <Trash2 size={13} />
              </Button>
              {collection.completed_total > 0 ? (
                <Button
                  size="icon"
                  variant="ghost"
                  title="Delete files from disk"
                  aria-label="Delete files from disk"
                  onClick={deleteFromDisk}
                  disabled={remove.isPending}
                  className="hover:text-danger"
                >
                  <FileX2 size={13} />
                </Button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {failure ? (
        <p className="mt-2 text-[11px] text-danger">{errorMessage(failure)}</p>
      ) : null}

      {expanded ? (
        <div className="mt-3 border-t border-edge-soft pt-3">
          <CollectionItems collectionId={collection.id} />
        </div>
      ) : null}
    </div>
  );
}
