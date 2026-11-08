import type {
  Collection,
  CollectionCreated,
  CollectionList,
  CreateCollection,
  CreateDownload,
  DownloadFilter,
  DownloadList,
  DownloadOut,
  ApiErrorBody,
  ProbeResult,
  Settings,
  Stats,
  SystemInfo,
} from "./models";

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: Record<string, unknown>;

  constructor(
    status: number,
    message: string,
    code?: string,
    details?: Record<string, unknown>,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let tokenPromise: Promise<string> | null = null;

export function getToken(): Promise<string> {
  const meta = document
    .querySelector('meta[name="vid-dwn-token"]')
    ?.getAttribute("content");
  if (meta && !meta.includes("__VID_DWN_TOKEN__")) {
    return Promise.resolve(meta);
  }
  if (!tokenPromise) {
    tokenPromise = fetch("/api/session")
      .then(async (response) => {
        if (!response.ok) throw new Error("Cannot establish a session");
        const data = (await response.json()) as { token: string };
        return data.token;
      })
      .catch((error) => {
        tokenPromise = null;
        throw error;
      });
  }
  return tokenPromise;
}

export function downloadQuery(filter: DownloadFilter): string {
  const params = new URLSearchParams();
  if (filter.collectionId) {
    // A collection holds at most VID_DWN_MAX_COLLECTION_ENTRIES items (5000 at most);
    // 500 per page covers the default cap in one request.
    params.set("collection_id", filter.collectionId);
    params.set("limit", "500");
  } else {
    params.set("limit", "200");
    if (filter.standalone) params.set("standalone", "true");
  }
  return params.toString();
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const method = (init.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    headers.set("X-Vid-Dwn-Token", await getToken());
  }
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw new ApiError(
      response.status,
      body?.error?.message || response.statusText || "Request failed",
      body?.error?.code,
      body?.error?.details,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  /** Describe a link; `playlist` asks for the playlist when it names a video too. */
  probe: (url: string, playlist = false) =>
    request<ProbeResult>("/api/videos/info", {
      method: "POST",
      body: JSON.stringify({ url, playlist }),
    }),

  createDownload: (payload: CreateDownload) =>
    request<DownloadOut>("/api/downloads", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listDownloads: (filter: DownloadFilter = {}) =>
    request<DownloadList>(`/api/downloads?${downloadQuery(filter)}`),
  getDownload: (id: string) => request<DownloadOut>(`/api/downloads/${id}`),

  cancel: (id: string) =>
    request<DownloadOut>(`/api/downloads/${id}/cancel`, { method: "POST" }),
  retry: (id: string) =>
    request<DownloadOut>(`/api/downloads/${id}/retry`, { method: "POST" }),
  remove: (id: string, deleteFile = false) =>
    request<void>(
      `/api/downloads/${id}?delete_file=${deleteFile ? "true" : "false"}`,
      { method: "DELETE" },
    ),
  reveal: (id: string) =>
    request<void>(`/api/downloads/${id}/reveal`, { method: "POST" }),

  createCollection: (payload: CreateCollection) =>
    request<CollectionCreated>("/api/collections", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listCollections: () => request<CollectionList>("/api/collections?limit=200"),
  cancelCollection: (id: string) =>
    request<Collection>(`/api/collections/${id}/cancel`, { method: "POST" }),
  retryCollection: (id: string) =>
    request<Collection>(`/api/collections/${id}/retry`, { method: "POST" }),
  removeCollection: (id: string, deleteFiles = false) =>
    request<void>(
      `/api/collections/${id}?delete_files=${deleteFiles ? "true" : "false"}`,
      { method: "DELETE" },
    ),

  getSettings: () => request<Settings>("/api/settings"),
  updateSettings: (settings: Settings) =>
    request<Settings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),

  getSystem: () => request<SystemInfo>("/api/system"),
  getStats: () => request<Stats>("/api/stats"),
};
