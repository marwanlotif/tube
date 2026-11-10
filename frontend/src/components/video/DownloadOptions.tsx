import { Check, Film, Music2 } from "lucide-react";
import { useState } from "react";

import type { CreateDownload, Preset, Settings } from "@/api/models";
import { Field, Toggle } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { cn, formatBytes, shortContainer } from "@/lib/utils";

/** Option sections shared by the single-video and the playlist download forms. */

export type DownloadMode = "video" | "audio";
export type AudioFormat = NonNullable<CreateDownload["audio_format"]>;

export const AUDIO_FORMATS: { value: AudioFormat; label: string }[] = [
  { value: "mp3", label: "MP3 — compatible" },
  { value: "m4a", label: "M4A — AAC" },
  { value: "opus", label: "Opus — efficient" },
  { value: "flac", label: "FLAC — lossless" },
  { value: "wav", label: "WAV — uncompressed" },
];

/** Per-download overrides of the defaults in Settings. */
export function useDownloadOverrides(settings: Settings | undefined) {
  const [audioFormatOverride, setAudioFormat] = useState<string | null>(null);
  const [subsOverride, setSubtitles] = useState<boolean | null>(null);
  const [langsOverride, setSubtitleLangs] = useState<string | null>(null);

  const audioFormat = audioFormatOverride ?? settings?.audio.format ?? "mp3";
  const subtitles = subsOverride ?? settings?.subtitles.enabled ?? false;
  const subtitleLangs = langsOverride ?? settings?.subtitles.langs ?? "en";

  return {
    audioFormat,
    setAudioFormat,
    subtitles,
    setSubtitles,
    subtitleLangs,
    setSubtitleLangs,
    /** Subtitle fields of a request; audio-only downloads never carry subtitles. */
    subtitlePayload(mode: DownloadMode) {
      return {
        subtitles: mode === "video" ? subtitles : false,
        subtitle_langs: mode === "video" && subtitles ? subtitleLangs.trim() || "en" : null,
      };
    },
  };
}

export function ModeToggle({
  mode,
  onChange,
}: {
  mode: DownloadMode;
  onChange: (mode: DownloadMode) => void;
}) {
  return (
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
          onClick={() => onChange(value)}
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
  );
}

export function PresetGrid({
  presets,
  selected,
  onSelect,
}: {
  presets: Preset[];
  selected: string;
  onSelect: (key: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
      {presets.map((option) => {
        const active = option.key === selected;
        return (
          <button
            key={option.key}
            type="button"
            disabled={!option.available}
            onClick={() => onSelect(option.key)}
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
  );
}

export function AudioFormatField({
  value,
  onChange,
  hint,
}: {
  value: string;
  onChange: (value: string) => void;
  hint?: string;
}) {
  return (
    <Field label="Audio format" hint={hint}>
      <Select value={value} onChange={(event) => onChange(event.target.value)}>
        {AUDIO_FORMATS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </Field>
  );
}

export function SubtitleOptions({
  enabled,
  onEnabledChange,
  langs,
  onLangsChange,
}: {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  langs: string;
  onLangsChange: (langs: string) => void;
}) {
  return (
    <div className="space-y-2 rounded-lg border border-edge-soft bg-surface/60 p-3.5">
      <Toggle
        checked={enabled}
        onChange={onEnabledChange}
        label="Download subtitles"
        description="Saves subtitles next to the video. Embedding is configurable in Settings."
      />
      {enabled ? (
        <Field label="Languages" hint="comma separated, e.g. en,de">
          <Input
            value={langs}
            onChange={(event) => onLangsChange(event.target.value)}
            placeholder="en"
            className="h-9"
          />
        </Field>
      ) : null}
    </div>
  );
}
