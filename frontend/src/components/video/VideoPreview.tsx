import { Clock, ExternalLink, ImageOff } from "lucide-react";

import type { VideoInfo } from "@/api/models";
import { Badge } from "@/components/ui/badge";
import { formatDuration } from "@/lib/utils";

export function VideoPreview({ video }: { video: VideoInfo }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row">
      <div className="relative aspect-video w-full shrink-0 overflow-hidden rounded-lg border border-edge-soft bg-surface sm:w-56">
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-faint">
            <ImageOff size={22} />
          </div>
        )}
        {video.duration_s ? (
          <span className="absolute bottom-1.5 right-1.5 rounded bg-black/75 px-1.5 py-0.5 font-mono text-[11px] text-white">
            {formatDuration(video.duration_s)}
          </span>
        ) : null}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {video.site ? <Badge tone="accent">{video.site}</Badge> : null}
          {video.is_live ? <Badge tone="warn">Live</Badge> : null}
        </div>
        <h2 className="mt-2 line-clamp-2 text-lg font-semibold leading-snug text-ink">
          {video.title}
        </h2>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
          {video.uploader ? <span className="truncate">{video.uploader}</span> : null}
          {video.duration_s ? (
            <span className="flex items-center gap-1">
              <Clock size={13} className="text-faint" />
              {formatDuration(video.duration_s)}
            </span>
          ) : null}
        </div>
        <a
          href={video.webpage_url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-flex items-center gap-1 text-xs text-faint transition-colors hover:text-accent"
        >
          Open source <ExternalLink size={11} />
        </a>
      </div>
    </div>
  );
}
