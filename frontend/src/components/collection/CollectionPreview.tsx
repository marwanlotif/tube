import { ExternalLink, ImageOff, ListVideo } from "lucide-react";

import type { CollectionInfo } from "@/api/models";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDuration } from "@/lib/utils";

import { nestedOf, videosOf } from "./selection";

export function CollectionPreview({
  collection,
  onOpen,
}: {
  collection: CollectionInfo;
  onOpen: (url: string) => void;
}) {
  const videos = videosOf(collection.entries);
  const nested = nestedOf(collection.entries);
  const duration = videos.reduce((sum, entry) => sum + (entry.duration_s ?? 0), 0);
  const kindLabel = collection.collection_type === "channel" ? "Channel" : "Playlist";

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="relative aspect-video w-full shrink-0 overflow-hidden rounded-lg border border-edge-soft bg-surface sm:w-56">
          {collection.thumbnail_url ? (
            <img
              src={collection.thumbnail_url}
              alt=""
              className="h-full w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-faint">
              <ImageOff size={22} />
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">{kindLabel}</Badge>
            {collection.site ? <Badge tone="muted">{collection.site}</Badge> : null}
          </div>
          <h2 className="mt-2 line-clamp-2 text-lg font-semibold leading-snug text-ink">
            {collection.title}
          </h2>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            {collection.uploader ? (
              <span className="truncate">{collection.uploader}</span>
            ) : null}
            {videos.length ? (
              <span className="flex items-center gap-1">
                <ListVideo size={13} className="text-faint" />
                {videos.length} {videos.length === 1 ? "video" : "videos"}
                {duration ? ` · ${formatDuration(duration)}` : null}
              </span>
            ) : null}
          </div>
          {collection.truncated ? (
            <p className="mt-2 text-xs text-warn">
              Showing the first {collection.max_entries}
              {collection.total ? ` of ${collection.total}` : ""} entries. The limit is set
              by VID_DWN_MAX_COLLECTION_ENTRIES.
            </p>
          ) : null}
          {collection.webpage_url ? (
            <a
              href={collection.webpage_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs text-faint transition-colors hover:text-accent"
            >
              Open source <ExternalLink size={11} />
            </a>
          ) : null}
        </div>
      </div>

      {nested.length ? (
        <div className="rounded-lg border border-edge-soft bg-surface/60 p-3.5">
          <p className="text-[13px] font-medium text-ink">
            {videos.length ? "Also on this page" : `This ${kindLabel.toLowerCase()} has sections`}
          </p>
          <p className="mt-0.5 text-xs text-muted">Open one to choose videos from it.</p>
          <ul className="mt-2.5 divide-y divide-edge-soft">
            {nested.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between gap-3 py-2">
                <span className="min-w-0 truncate text-[13px] text-ink">{entry.title}</span>
                <Button size="sm" variant="outline" onClick={() => onOpen(entry.url ?? "")}>
                  Open
                </Button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
