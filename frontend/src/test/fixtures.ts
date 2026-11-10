import type { Collection, DownloadList, DownloadOut } from "@/api/models";

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
