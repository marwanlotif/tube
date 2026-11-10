import type {
  Collection,
  CollectionEntry,
  CollectionInfo,
  DownloadList,
  DownloadOut,
  Preset,
  Settings,
  VideoFormat,
  VideoInfo,
} from "@/api/models";

export function makeDownload(overrides: Partial<DownloadOut> = {}): DownloadOut {
  return {
    id: "d1",
    url: "https://example.com/watch?v=abc",
    site: "Youtube",
    video_id: "abc",
    title: "A video",
    uploader: null,
    thumbnail_url: null,
    duration_s: 61,
    mode: "video",
    status: "queued",
    format_label: "Up to 1080p",
    format_selector: null,
    container: null,
    output_dir: "/media/Videos",
    output_path: null,
    file_size: null,
    downloaded_bytes: 0,
    total_bytes: null,
    progress: 0,
    speed: null,
    eta_s: null,
    error_code: null,
    error_message: null,
    attempts: 0,
    resumable: false,
    created_at: "2026-11-08T10:00:00Z",
    started_at: null,
    finished_at: null,
    collection_id: null,
    playlist_index: null,
    ...overrides,
  };
}

export function makeList(items: DownloadOut[]): DownloadList {
  return { items, total: items.length };
}

export function makeCollection(overrides: Partial<Collection> = {}): Collection {
  return {
    id: "c1",
    url: "https://www.youtube.com/playlist?list=PL1",
    collection_type: "playlist",
    title: "A playlist",
    uploader: "Someone",
    site: "YoutubeTab",
    thumbnail_url: null,
    mode: "video",
    preset_key: "best_1080",
    output_dir: "/media/Videos/A playlist",
    entry_total: 3,
    item_total: 3,
    counts: { queued: 3 },
    active_total: 3,
    completed_total: 0,
    failed_total: 0,
    progress: 0,
    created_at: "2026-11-08T10:00:00Z",
    ...overrides,
  };
}

export function makeVideoInfo(overrides: Partial<VideoInfo> = {}): VideoInfo {
  const preset = (key: string, label: string, extra: Partial<Preset> = {}): Preset => ({
    key,
    label,
    available: true,
    container: "mp4",
    height: null,
    fps: null,
    vcodec: null,
    acodec: null,
    requires_merge: true,
    estimated_bytes: null,
    selector_label: null,
    ...extra,
  });
  const format = (extra: Partial<VideoFormat> & Pick<VideoFormat, "format_id" | "kind">) => ({
    ext: "mp4",
    vcodec: null,
    acodec: null,
    width: null,
    height: null,
    fps: null,
    tbr: null,
    filesize: null,
    hdr: false,
    label: extra.format_id,
    ...extra,
  });
  return {
    kind: "video",
    id: "abc123",
    site: "Youtube",
    title: "Test Video",
    uploader: "Tester",
    duration_s: 120,
    webpage_url: "https://www.youtube.com/watch?v=abc123",
    thumbnail_url: null,
    is_live: false,
    playlist_hint: false,
    formats: [
      format({ format_id: "137", kind: "video", height: 1080, vcodec: "avc1", label: "1080p" }),
      format({ format_id: "18", kind: "combined", height: 360, label: "360p" }),
      format({ format_id: "140", kind: "audio", ext: "m4a", acodec: "mp4a", label: "AAC" }),
    ],
    presets: [
      preset("best_1080", "Up to 1080p", { height: 1080, selector_label: "1080p + AAC" }),
      preset("best_720", "Up to 720p", { height: 720 }),
      preset("best_2160", "Up to 4K", { available: false }),
      preset("audio", "Audio only", { container: "m4a", requires_merge: false }),
    ],
    ...overrides,
  };
}

export function makeSettings(overrides: Partial<Settings> = {}): Settings {
  return {
    video_dir: "/media/Videos/VidDwn",
    audio_dir: "/media/Music/VidDwn",
    filename_template: "%(title).200B [%(id)s].%(ext)s",
    video: { max_height: 1080, prefer_codec: "h264", container: "mp4" },
    audio: { format: "mp3", quality: "0" },
    subtitles: { enabled: false, langs: "en", auto: false, embed: false },
    network: { fragments: 4, rate_limit: null, retries: 10, socket_timeout: 30 },
    cookies_from_browser: null,
    max_concurrent_downloads: 1,
    ...overrides,
  };
}

export function makeEntry(overrides: Partial<CollectionEntry> = {}): CollectionEntry {
  const id = overrides.id ?? "vid001";
  return {
    id,
    index: 1,
    title: `Video ${id}`,
    url: `https://www.youtube.com/watch?v=${id}`,
    duration_s: 60,
    kind: "video",
    available: true,
    reason: null,
    ...overrides,
  };
}

export function makeCollectionInfo(overrides: Partial<CollectionInfo> = {}): CollectionInfo {
  const presets = makeVideoInfo().presets.map((p) => ({ ...p, available: true }));
  return {
    kind: "collection",
    id: "PLtest123",
    collection_type: "playlist",
    title: "Test Playlist",
    uploader: "Tester",
    site: "YoutubeTab",
    webpage_url: "https://www.youtube.com/playlist?list=PLtest123",
    thumbnail_url: null,
    total: 4,
    truncated: false,
    max_entries: 500,
    entries: [
      makeEntry({ id: "vid001", index: 1, title: "First Video", duration_s: 61 }),
      makeEntry({ id: "vid002", index: 2, title: "Second Video", duration_s: 125 }),
      makeEntry({
        id: "vidpriv", index: 3, title: "[Private video]", duration_s: null,
        available: false, reason: "No longer available",
      }),
      makeEntry({ id: "vid003", index: 4, title: "Third Video", duration_s: null }),
    ],
    presets,
    ...overrides,
  };
}
