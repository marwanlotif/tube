import type {
  CreateDownload,
  DownloadList,
  DownloadOut,
  ApiErrorBody,
  Settings,
  Stats,
  SystemInfo,
  VideoInfo,
} from "./models";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
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
      body?.error?.message ?? response.statusText ?? "Request failed",
      body?.error?.code,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  videoInfo: (url: string) =>
    request<VideoInfo>("/api/videos/info", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  createDownload: (payload: CreateDownload) =>
    request<DownloadOut>("/api/downloads", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listDownloads: () => request<DownloadList>("/api/downloads?limit=200"),
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

  getSettings: () => request<Settings>("/api/settings"),
  updateSettings: (settings: Settings) =>
    request<Settings>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),

  getSystem: () => request<SystemInfo>("/api/system"),
  getStats: () => request<Stats>("/api/stats"),
};
