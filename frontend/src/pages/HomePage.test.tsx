import { fireEvent, screen, waitFor } from "@testing-library/react";
import { type MockInstance, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/api/client";
import { makeCollectionInfo, makeEntry, makeVideoInfo } from "@/test/fixtures";
import { renderWithApp } from "@/test/render";

import { HomePage } from "./HomePage";

const MIXED = "https://www.youtube.com/watch?v=abc123&list=PLtest123";

describe("HomePage", () => {
  let probe: MockInstance<typeof api.probe>;

  beforeEach(() => {
    probe = vi.spyOn(api, "probe");
    // jsdom has no layout, so scrolling the result into view is a no-op.
    Element.prototype.scrollIntoView = vi.fn();
  });

  function fetchLink(url: string) {
    fireEvent.change(screen.getByLabelText("Video URL"), { target: { value: url } });
    fireEvent.click(screen.getByRole("button", { name: /Fetch/ }));
  }

  it("shows the playlist picker for a playlist link", async () => {
    probe.mockResolvedValue(makeCollectionInfo());
    renderWithApp(<HomePage />);
    fetchLink("https://www.youtube.com/playlist?list=PLtest123");

    expect(await screen.findByRole("heading", { name: "Test Playlist" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Download 3 videos" })).toBeDefined();
    expect(probe).toHaveBeenCalledWith("https://www.youtube.com/playlist?list=PLtest123", false);
  });

  it("offers the playlist for a video that belongs to one", async () => {
    probe
      .mockResolvedValueOnce(makeVideoInfo({ playlist_hint: true }))
      .mockResolvedValueOnce(makeCollectionInfo());
    renderWithApp(<HomePage />);
    fetchLink(MIXED);

    fireEvent.click(await screen.findByRole("button", { name: "Load the playlist" }));
    await waitFor(() => expect(probe).toHaveBeenLastCalledWith(MIXED, true));
    expect(await screen.findByRole("heading", { name: "Test Playlist" })).toBeDefined();
  });

  it("does not offer a playlist for a plain video", async () => {
    probe.mockResolvedValue(makeVideoInfo());
    renderWithApp(<HomePage />);
    fetchLink("https://www.youtube.com/watch?v=abc123");
    expect(await screen.findByRole("heading", { name: "Test Video" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Load the playlist" })).toBeNull();
  });

  it("opens a channel section in place", async () => {
    const tabs = makeCollectionInfo({
      collection_type: "channel",
      title: "Tester",
      entries: [
        makeEntry({
          id: "https://www.youtube.com/@tester/videos",
          kind: "collection",
          title: "Tester - Videos",
          url: "https://www.youtube.com/@tester/videos",
        }),
      ],
    });
    probe.mockResolvedValueOnce(tabs).mockResolvedValueOnce(makeCollectionInfo());
    renderWithApp(<HomePage />);
    fetchLink("https://www.youtube.com/@tester");

    expect(await screen.findByText("This channel has sections")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    await waitFor(() =>
      expect(probe).toHaveBeenLastCalledWith("https://www.youtube.com/@tester/videos", false),
    );
    expect(screen.getByLabelText<HTMLInputElement>("Video URL").value).toBe(
      "https://www.youtube.com/@tester/videos",
    );
  });

  it("shows probe errors and clears them when the link changes", async () => {
    probe.mockRejectedValue(new ApiError(422, "This playlist has no entries", "NO_ENTRIES"));
    renderWithApp(<HomePage />);
    fetchLink("https://www.youtube.com/playlist?list=PLempty");
    expect(await screen.findByText("This playlist has no entries")).toBeDefined();

    fireEvent.change(screen.getByLabelText("Video URL"), { target: { value: "https://x" } });
    expect(screen.queryByText("This playlist has no entries")).toBeNull();
  });
});
