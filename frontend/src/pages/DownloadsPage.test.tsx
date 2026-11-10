import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { DownloadFilter } from "@/api/models";
import { makeCollection, makeDownload, makeList } from "@/test/fixtures";
import { renderWithApp } from "@/test/render";

import { DownloadsPage } from "./DownloadsPage";

const running = makeCollection({
  id: "c-run",
  title: "Running playlist",
  active_total: 2,
  completed_total: 1,
  item_total: 3,
  counts: { completed: 1, downloading: 1, queued: 1 },
  progress: 45,
});
const broken = makeCollection({
  id: "c-broken",
  title: "Broken playlist",
  active_total: 0,
  completed_total: 1,
  failed_total: 2,
  item_total: 3,
  counts: { completed: 1, failed: 2 },
  created_at: "2026-11-01T00:00:00Z",
});

describe("DownloadsPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "getStats").mockResolvedValue({
      counts: {}, bytes_last_7d: 0, completed_total: 0, active_total: 2,
      disk_free: 1, disk_total: 2,
    });
    vi.spyOn(api, "listCollections").mockResolvedValue({ items: [running, broken], total: 2 });
    vi.spyOn(api, "listDownloads").mockImplementation(async (filter: DownloadFilter = {}) =>
      filter.collectionId
        ? makeList([
            makeDownload({
              id: "item-1", title: "Playlist item one", collection_id: filter.collectionId,
              playlist_index: 1,
            }),
          ])
        : makeList([makeDownload({
            id: "solo",
            title: "Standalone video",
            status: "completed",
            output_path: "/media/Videos/Standalone video.mp4",
          })]),
    );
  });

  it("lists collections alongside standalone downloads, active first", async () => {
    renderWithApp(<DownloadsPage />);
    const titles = await screen.findAllByRole("heading", { level: 3 });
    expect(titles.map((h) => h.textContent)).toEqual([
      "Running playlist",
      "Standalone video",
      "Broken playlist",
    ]);
    expect(api.listDownloads).toHaveBeenCalledWith({ standalone: true });
    expect(screen.getByText("1 of 3 done · 1 downloading · 1 queued")).toBeDefined();
  });

  it("filters collections as single rows", async () => {
    renderWithApp(<DownloadsPage />);
    await screen.findByText("Broken playlist");
    fireEvent.click(screen.getByRole("button", { name: /Needs attention/ }));
    expect(screen.getByText("Broken playlist")).toBeDefined();
    expect(screen.queryByText("Running playlist")).toBeNull();
    expect(screen.queryByText("Standalone video")).toBeNull();
  });

  it("loads a collection's videos only when it is expanded", async () => {
    renderWithApp(<DownloadsPage />);
    await screen.findByText("Running playlist");
    expect(api.listDownloads).not.toHaveBeenCalledWith({ collectionId: "c-run" });

    fireEvent.click(screen.getAllByRole("button", { name: "Show 3 videos" })[0]);
    expect(await screen.findByText("Playlist item one")).toBeDefined();
    expect(api.listDownloads).toHaveBeenCalledWith({ collectionId: "c-run" });
  });

  it("cancels a running collection and retries a failed one", async () => {
    const cancel = vi.spyOn(api, "cancelCollection").mockResolvedValue(running);
    const retry = vi.spyOn(api, "retryCollection").mockResolvedValue(broken);
    renderWithApp(<DownloadsPage />);
    await screen.findByText("Running playlist");

    fireEvent.click(screen.getByRole("button", { name: "Cancel all" }));
    fireEvent.click(screen.getByRole("button", { name: "Retry 2" }));
    await waitFor(() => expect(cancel).toHaveBeenCalledWith("c-run"));
    await waitFor(() => expect(retry).toHaveBeenCalledWith("c-broken"));
  });

  it("only removes settled collections and asks before deleting files", async () => {
    const remove = vi.spyOn(api, "removeCollection").mockResolvedValue(undefined);
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderWithApp(<DownloadsPage />);
    await screen.findByText("Broken playlist");

    // Only the settled collection offers removal; the running one does not.
    expect(screen.getAllByRole("button", { name: "Remove from list" })).toHaveLength(2);
    const deleteFiles = screen.getByRole("button", { name: "Delete files from disk" });
    fireEvent.click(deleteFiles);
    expect(confirm).toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();

    confirm.mockReturnValue(true);
    fireEvent.click(deleteFiles);
    await waitFor(() => expect(remove).toHaveBeenCalledWith("c-broken", true));
  });
});
