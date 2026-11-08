import { FileAudio, Film, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { CreateDownload, VideoInfo } from "@/api/models";
import { useCreateDownload, useSettings } from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/input";
import {
  errorMessage,
  formatBytes,
  formatDuration,
  shortContainer,
} from "@/lib/utils";

import {
  AudioFormatField,
  type AudioFormat,
  type DownloadMode,
  ModeToggle,
  PresetGrid,
  SubtitleOptions,
  useDownloadOverrides,
} from "./DownloadOptions";

function presetsFor(video: VideoInfo) {
  return video.presets.filter((preset) => preset.key !== "audio");
}

export function FormatPicker({ video }: { video: VideoInfo }) {
  const { data: settings } = useSettings();
  const create = useCreateDownload();
  const navigate = useNavigate();

  const [mode, setMode] = useState<DownloadMode>("video");
  const [preset, setPreset] = useState<string | null>(null);
  const [custom, setCustom] = useState(false);
  const [videoId, setVideoId] = useState("");
  const [audioId, setAudioId] = useState("");
  const overrides = useDownloadOverrides(settings);
  const { audioFormat, subtitles, subtitleLangs } = overrides;

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
  const canSubmit =
    !create.isPending &&
    (mode === "audio" || (custom ? Boolean(effectiveVideoId) : Boolean(effectivePreset)));

  const submit = () => {
    if (!canSubmit) return;
    const payload: CreateDownload = {
      url: video.webpage_url,
      mode,
      ...overrides.subtitlePayload(mode),
    };
    if (mode === "audio") {
      payload.audio_format = audioFormat as AudioFormat;
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
      <ModeToggle mode={mode} onChange={setMode} />

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
            <PresetGrid presets={presets} selected={effectivePreset} onSelect={setPreset} />
          )}
          {selectedPreset?.selector_label && !custom ? (
            <p className="text-[11px] text-faint">{selectedPreset.selector_label}</p>
          ) : null}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <AudioFormatField
            value={audioFormat}
            onChange={overrides.setAudioFormat}
            hint={`${formatDuration(video.duration_s)} source`}
          />
          <div className="flex items-end">
            <p className="pb-2 text-[11px] text-faint">
              Audio is extracted from the best available stream and saved to your music
              folder.
            </p>
          </div>
        </div>
      )}

      {mode === "video" ? (
        <SubtitleOptions
          enabled={subtitles}
          onEnabledChange={overrides.setSubtitles}
          langs={subtitleLangs}
          onLangsChange={overrides.setSubtitleLangs}
        />
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
