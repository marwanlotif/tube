import type { components } from "./types";

export type VideoInfo = components["schemas"]["VideoInfoOut"];
export type VideoFormat = components["schemas"]["FormatOut"];
export type Preset = components["schemas"]["PresetOut"];
export type DownloadOut = components["schemas"]["DownloadOut"];
export type DownloadList = components["schemas"]["DownloadList"];
export type Stats = components["schemas"]["StatsOut"];
export type SystemInfo = components["schemas"]["SystemOut"];
export type SettingsBase = components["schemas"]["SettingsModel"];

export type VideoSettings = components["schemas"]["VideoSettings"];
export type AudioSettings = components["schemas"]["AudioSettings"];
export type SubtitleSettings = components["schemas"]["SubtitleSettings"];
export type NetworkSettings = components["schemas"]["NetworkSettings"];

export type Settings = SettingsBase & {
  video: VideoSettings;
  audio: AudioSettings;
  subtitles: SubtitleSettings;
  network: NetworkSettings;
};

export type DownloadStatus =
  | "queued"
  | "extracting"
  | "downloading"
  | "processing"
  | "verifying"
  | "completed"
  | "failed"
  | "canceled"
  | "interrupted";

export type CreateDownload = {
  url: string;
  preset?: string | null;
  video_id?: string | null;
  audio_id?: string | null;
  mode?: "video" | "audio";
  audio_format?: "mp3" | "m4a" | "flac" | "wav" | "opus" | null;
  subtitles?: boolean | null;
  subtitle_langs?: string | null;
};

export type ApiErrorBody = {
  error?: { code?: string; message?: string };
};
