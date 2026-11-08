import { Loader2, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import type { CollectionInfo, CreateCollection } from "@/api/models";
import { useCreateCollection, useSettings } from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Toggle } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  AudioFormatField,
  type AudioFormat,
  type DownloadMode,
  ModeToggle,
  PresetGrid,
  SubtitleOptions,
  useDownloadOverrides,
} from "@/components/video/DownloadOptions";
import { cn, errorMessage, formatDuration } from "@/lib/utils";

import {
  describeSkipped,
  initialSelection,
  matchingEntries,
  selectedIds,
  setSelected,
  toggle,
  totalDuration,
  videosOf,
} from "./selection";

function submitError(error: unknown): string {
  const message = errorMessage(error);
  const skipped = error instanceof ApiError ? error.details?.skipped : undefined;
  const reasons = skipped && typeof skipped === "object" ? describeSkipped(skipped) : "";
  return reasons ? `${message}: ${reasons}.` : message;
}

export function CollectionPicker({
  collection,
  sourceUrl,
}: {
  collection: CollectionInfo;
  /** The link that was probed; the server re-reads (or reuses) that same listing. */
  sourceUrl: string;
}) {
  const { data: settings } = useSettings();
  const create = useCreateCollection();
  const navigate = useNavigate();
  const overrides = useDownloadOverrides(settings);

  const videos = useMemo(() => videosOf(collection.entries), [collection.entries]);
  const [selection, setSelection] = useState(() => initialSelection(collection.entries));
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<DownloadMode>("video");
  const [preset, setPreset] = useState("best_1080");
  const [subfolder, setSubfolder] = useState(true);
  const [skipExisting, setSkipExisting] = useState(true);

  const visible = matchingEntries(videos, query);
  const ids = selectedIds(collection.entries, selection);
  const duration = totalDuration(videos, selection);
  const presets = collection.presets.filter((item) => item.key !== "audio");
  const canSubmit = ids.length > 0 && !create.isPending;

  const submit = () => {
    if (!canSubmit) return;
    const payload: CreateCollection = {
      url: sourceUrl,
      entry_ids: ids,
      mode,
      subfolder,
      skip_existing: skipExisting,
      ...overrides.subtitlePayload(mode),
    };
    if (mode === "audio") {
      payload.preset = "audio";
      payload.audio_format = overrides.audioFormat as AudioFormat;
    } else {
      payload.preset = preset;
    }
    create.mutate(payload, { onSuccess: () => navigate("/downloads") });
  };

  if (!videos.length) return null;

  return (
    <div className="space-y-5">
      <div className="space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[13px] font-medium text-ink">
            Videos{" "}
            <span className="font-normal text-faint">
              {ids.length} of {videos.length} selected
              {duration ? ` · ${formatDuration(duration)}` : ""}
            </span>
          </p>
          <div className="flex items-center gap-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelection((current) => setSelected(current, visible, true))}
            >
              Select all
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelection((current) => setSelected(current, visible, false))}
            >
              Select none
            </Button>
          </div>
        </div>
        {videos.length > 8 ? (
          <div className="relative">
            <Search
              size={14}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filter by title"
              aria-label="Filter videos by title"
              className="h-9 pl-9"
            />
          </div>
        ) : null}
        <ul
          className="max-h-80 divide-y divide-edge-soft overflow-y-auto rounded-lg border border-edge-soft bg-surface/60"
          aria-label="Playlist videos"
        >
          {visible.map((entry) => (
            <li key={entry.id}>
              <label
                className={cn(
                  "flex items-center gap-3 px-3 py-2 text-[13px]",
                  entry.available
                    ? "cursor-pointer hover:bg-white/[0.02]"
                    : "cursor-not-allowed opacity-50",
                )}
              >
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 shrink-0 accent-accent"
                  checked={entry.available && selection.has(entry.id)}
                  disabled={!entry.available}
                  onChange={() => setSelection((current) => toggle(current, entry.id))}
                />
                <span className="w-8 shrink-0 text-right font-mono text-[11px] text-faint">
                  {entry.index}
                </span>
                <span className="min-w-0 flex-1 truncate text-ink">{entry.title}</span>
                {entry.available ? (
                  <span className="shrink-0 font-mono text-[11px] text-faint">
                    {entry.duration_s ? formatDuration(entry.duration_s) : ""}
                  </span>
                ) : (
                  <Badge tone="muted">{entry.reason ?? "Unavailable"}</Badge>
                )}
              </label>
            </li>
          ))}
          {visible.length === 0 ? (
            <li className="px-3 py-6 text-center text-xs text-muted">No titles match.</li>
          ) : null}
        </ul>
      </div>

      <div className="border-t border-edge-soft" />

      <ModeToggle mode={mode} onChange={setMode} />

      {mode === "video" ? (
        <div className="space-y-3">
          <div>
            <p className="text-[13px] font-medium text-ink">Quality</p>
            <p className="mt-0.5 text-[11px] text-faint">
              Applied to each video; it falls back to the best lower resolution when a video
              does not have it.
            </p>
          </div>
          <PresetGrid presets={presets} selected={preset} onSelect={setPreset} />
          <SubtitleOptions
            enabled={overrides.subtitles}
            onEnabledChange={overrides.setSubtitles}
            langs={overrides.subtitleLangs}
            onLangsChange={overrides.setSubtitleLangs}
          />
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <AudioFormatField value={overrides.audioFormat} onChange={overrides.setAudioFormat} />
        </div>
      )}

      <div className="space-y-1 rounded-lg border border-edge-soft bg-surface/60 p-3.5">
        <Toggle
          checked={subfolder}
          onChange={setSubfolder}
          label="Save into a playlist folder"
          description="Creates a folder named after the playlist inside your download folder."
        />
        <Toggle
          checked={skipExisting}
          onChange={setSkipExisting}
          label="Skip videos already downloaded"
          description="Leaves out videos you already have, or that are still in the queue."
        />
      </div>

      <div className="flex flex-col gap-3 border-t border-edge-soft pt-4 sm:flex-row sm:items-center sm:justify-end">
        <Button
          size="lg"
          onClick={submit}
          disabled={!canSubmit}
          className="h-11 px-6 sm:min-w-48"
        >
          {create.isPending ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Adding
            </>
          ) : (
            `Download ${ids.length} ${ids.length === 1 ? "video" : "videos"}`
          )}
        </Button>
      </div>

      {create.isError ? (
        <p className="text-sm text-danger">{submitError(create.error)}</p>
      ) : null}
    </div>
  );
}
