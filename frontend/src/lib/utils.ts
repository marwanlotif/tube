import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { DownloadStatus } from "@/api/models";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes?: number | null, decimals = 1): string {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 100 ? 0 : decimals)} ${units[index]}`;
}

export function formatSpeed(bytes?: number | null): string | null {
  if (!bytes) return null;
  return `${formatBytes(bytes)}/s`;
}

export function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds < 0) return "—";
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function formatEta(seconds?: number | null): string {
  if (!seconds || seconds <= 0) return "";
  if (seconds < 60) return `${Math.round(seconds)}s left`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  if (minutes < 60) return `${minutes}m ${rest}s left`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m left`;
}

export function formatRelative(iso: string): string {
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

type StatusMeta = {
  label: string;
  tone: "accent" | "muted" | "danger" | "warn" | "info" | "success";
  active: boolean;
};

export const STATUS_META: Record<DownloadStatus, StatusMeta> = {
  queued: { label: "Queued", tone: "muted", active: true },
  extracting: { label: "Reading source", tone: "info", active: true },
  downloading: { label: "Downloading", tone: "accent", active: true },
  processing: { label: "Processing", tone: "info", active: true },
  verifying: { label: "Verifying", tone: "info", active: true },
  completed: { label: "Completed", tone: "success", active: false },
  failed: { label: "Failed", tone: "danger", active: false },
  canceled: { label: "Canceled", tone: "muted", active: false },
  interrupted: { label: "Interrupted", tone: "warn", active: false },
};

export function statusMeta(status: string): StatusMeta {
  return STATUS_META[status as DownloadStatus] ?? STATUS_META.queued;
}

export function shortContainer(container?: string | null): string {
  return container ? container.toUpperCase() : "—";
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}
