import { Check, FileAudio, Film, Loader2, Music2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { CreateDownload, VideoInfo } from "@/api/models";
import { useCreateDownload, useSettings } from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Toggle } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import {
  cn,
  errorMessage,
  formatBytes,
  formatDuration,
  shortContainer,
} from "@/lib/utils";

const AUDIO_FORMATS = [
  { value: "mp3", label: "MP3 — compatible" },
  { value: "m4a", label: "M4A — AAC" },
  { value: "opus", label: "Opus — efficient" },
  { value: "flac", label: "FLAC — lossless" },
  { value: "wav", label: "WAV — uncompressed" },
];

function presetsFor(video: VideoInfo) {
  return video.presets.filter((preset) => preset.key !== "audio");
}

export function FormatPicker({ video }: { video: VideoInfo }) {
  const { data: settings } = useSettings();
  const create = useCreateDownload();
  const navigate = useNavigate();

  const [mode, setMode] = useState<"video" | "audio">("video");
  const [preset, setPreset] = useState<string | null>(null);
  const [custom, setCustom] = useState(false);
  const [videoId, setVideoId] = useState("");
  const [audioId, setAudioId] = useState("");
  const [audioFormatOverride, setAudioFormatOverride] = useState<string | null>(null);
  const [subsOverride, setSubsOverride] = useState<boolean | null>(null);
  const [langsOverride, setLangsOverride] = useState<string | null>(null);

  const presets = presetsFor(video);
  const videoFormats = useMemo(
    () =>
      [...video.formats.filter((format) => format.kind !== "audio")].sort(
        (a, b) => (b.height ?? 0) - (a.height ?? 0) || (b.tbr ?? 0) - (a.tbr ?? 0),
      ),
    [video.formats],
  );
  const audioFormats = useMemo(
    () => video.formats.filter((format) => format.kind === "audio"),
    [video.formats],
  );

  const effectivePreset =
    presets.find((item) => item.key === preset && item.available)?.key ??
    presets.find((item) => item.key === "best_1080" && item.available)?.key ??
    presets.find((item) => item.available)?.key ??
    "";
  const selectedPreset = presets.find((item) => item.key === effectivePreset);

  const effectiveVideoId = videoId || videoFormats[0]?.format_id || "";
  const selectedVideo = videoFormats.find((format) => format.format_id === effectiveVideoId);
  const audioFormat = audioFormatOverride ?? settings?.audio.format ?? "mp3";
  const subtitles = subsOverride ?? settings?.subtitles.enabled ?? false;
  const subtitleLangs = langsOverride ?? settings?.subtitles.langs ?? "en";

  const canSubmit =
    !create.isPending &&
    (mode === "audio" || (custom ? Boolean(effectiveVideoId) : Boolean(effectivePreset)));

  const submit = () => {
    if (!canSubmit) return;
    const payload: CreateDownload = {
      url: video.webpage_url,
      mode,
      subtitles: mode === "video" ? subtitles : false,
      subtitle_langs: mode === "video" && subtitles ? subtitleLangs.trim() || "en" : null,
    };
    if (mode === "audio") {
      payload.audio_format = audioFormat as CreateDownload["audio_format"];
      payload.preset = "audio";
    } else if (custom && effectiveVideoId) {
      payload.video_id = effectiveVideoId;
      payload.audio_id = selectedVideo?.kind === "video" ? audioId || null : null;
    } else {
      payload.preset = effectivePreset;
    }
    create.mutate(payload, { onSuccess: () => navigate("/downloads") });
  };

  return (
    <div className="space-y-5">
      <div className="inline-flex rounded-lg border border-edge bg-surface p-1">
        {(
          [
            { value: "video", label: "Video", icon: Film },
            { value: "audio", label: "Audio", icon: Music2 },
          ] as const
        ).map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => setMode(value)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-[13px] font-medium transition-colors",
              mode === value
                ? "bg-raised text-ink shadow-sm"
                : "text-muted hover:text-ink",
            )}
          >
            <Icon size={14} className={mode === value ? "text-accent" : "text-faint"} />
            {label}
          </button>
        ))}
      </div>

      {mode === "video" ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[13px] font-medium text-ink">Quality</p>
            <button
              type="button"
              onClick={() => setCustom((value) => !value)}
              className="text-xs text-faint transition-colors hover:text-accent"
            >
              {custom ? "Use presets" : "Choose exact formats"}
            </button>
          </div>

          {custom ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Video stream">
                <Select
                  value={effectiveVideoId}
                  onChange={(event) => {
                    setVideoId(event.target.value);
                    setAudioId("");
                  }}
                >
                  {videoFormats.map((format) => (
                    <option key={format.format_id} value={format.format_id}>
                      {format.label} · {format.ext.toUpperCase()} ·{" "}
                      {format.filesize ? formatBytes(format.filesize) : "size unknown"}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field
                label="Audio stream"
                hint={selectedVideo?.kind === "combined" ? "included in video" : "auto if empty"}
              >
                <Select
                  value={audioId}
                  disabled={selectedVideo?.kind === "combined"}
                  onChange={(event) => setAudioId(event.target.value)}
                >
                  <option value="">Best matching audio</option>
                  {audioFormats.map((format) => (
                    <option key={format.format_id} value={format.format_id}>
                      {format.label} · {format.ext.toUpperCase()}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
              {presets.map((option) => {
                const active = option.key === effectivePreset;
                return (
                  <button
                    key={option.key}
                    type="button"
                    disabled={!option.available}
                    onClick={() => setPreset(option.key)}
                    className={cn(
                      "relative rounded-lg border px-3 py-2.5 text-left transition-colors",
                      active
                        ? "border-accent/50 bg-accent/[0.07]"
                        : "border-edge bg-surface hover:border-[#333b46] hover:bg-white/[0.02]",
                      !option.available && "cursor-not-allowed opacity-35 hover:border-edge",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={cn(
                          "text-[13px] font-medium",
                          active ? "text-ink" : "text-muted",
                        )}
                      >
                        {option.label}
                      </span>
                      {active ? <Check size={13} className="text-accent" /> : null}
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-[11px] text-faint">
                      {option.container ? (
                        <span className="font-mono">{shortContainer(option.container)}</span>
                      ) : null}
                      {option.estimated_bytes ? (
                        <span>~{formatBytes(option.estimated_bytes)}</span>
                      ) : null}
                      {option.requires_merge ? <span>merge</span> : null}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
          {selectedPreset?.selector_label && !custom ? (
            <p className="text-[11px] text-faint">{selectedPreset.selector_label}</p>
          ) : null}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Audio format" hint={`${formatDuration(video.duration_s)} source`}>
            <Select
              value={audioFormat}
              onChange={(event) => setAudioFormatOverride(event.target.value)}
            >
              {AUDIO_FORMATS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </Field>
          <div className="flex items-end">
            <p className="pb-2 text-[11px] text-faint">
              Audio is extracted from the best available stream and saved to your music
              folder.
            </p>
          </div>
        </div>
      )}

      {mode === "video" ? (
        <div className="space-y-2 rounded-lg border border-edge-soft bg-surface/60 p-3.5">
          <Toggle
            checked={subtitles}
            onChange={setSubsOverride}
            label="Download subtitles"
            description="Saves subtitles next to the video. Embedding is configurable in Settings."
          />
          {subtitles ? (
            <Field label="Languages" hint="comma separated, e.g. en,de">
              <Input
                value={subtitleLangs}
                onChange={(event) => setLangsOverride(event.target.value)}
                placeholder="en"
                className="h-9"
              />
            </Field>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-col gap-3 border-t border-edge-soft pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2 text-xs text-faint">
          <Badge tone="muted">
            {mode === "audio" ? (
              <FileAudio size={11} />
            ) : (
              <Film size={11} />
            )}
            {mode === "audio"
              ? audioFormat.toUpperCase()
              : custom
                ? shortContainer(selectedVideo?.ext)
                : shortContainer(selectedPreset?.container)}
          </Badge>
          {mode === "video" && !custom && selectedPreset?.estimated_bytes ? (
            <span>~{formatBytes(selectedPreset.estimated_bytes)} estimated</span>
          ) : null}
          {mode === "video" && selectedPreset?.height ? (
            <span>{selectedPreset.height}p</span>
          ) : null}
          {mode === "audio" && settings ? (
            <span>quality {settings.audio.quality}</span>
          ) : null}
        </div>
        <Button
          size="lg"
          onClick={submit}
          disabled={!canSubmit}
          className="h-11 px-6 sm:min-w-40"
        >
          {create.isPending ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Adding
            </>
          ) : (
            "Download"
          )}
        </Button>
      </div>

      {create.isError ? (
        <p className="text-sm text-danger">{errorMessage(create.error)}</p>
      ) : null}
    </div>
  );
}
