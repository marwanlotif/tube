import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { type MockInstance, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/api/client";
import type { CollectionCreated } from "@/api/models";
import { makeCollection, makeCollectionInfo, makeEntry } from "@/test/fixtures";
import { renderWithApp } from "@/test/render";

import { CollectionPicker } from "./CollectionPicker";

const SOURCE = "https://www.youtube.com/playlist?list=PLtest123";

const created: CollectionCreated = {
  collection: makeCollection(),
  created: 3,
  skipped: { not_found: 0, unavailable: 0, blocked: 0, already_downloaded: 0 },
};

function checkbox(title: string): HTMLInputElement {
  const row = screen.getByText(title).closest("label");
  if (!row) throw new Error(`no row for ${title}`);
  return within(row).getByRole("checkbox") as HTMLInputElement;
}

describe("CollectionPicker", () => {
  let createCollection: MockInstance<typeof api.createCollection>;

  beforeEach(() => {
    createCollection = vi.spyOn(api, "createCollection").mockResolvedValue(created);
  });

  function show(collection = makeCollectionInfo()) {
    return renderWithApp(<CollectionPicker collection={collection} sourceUrl={SOURCE} />);
  }

  async function submit(label = /^Download \d+ videos?$/) {
    fireEvent.click(screen.getByRole("button", { name: label }));
    await waitFor(() => expect(createCollection).toHaveBeenCalledTimes(1));
    return createCollection.mock.calls[0][0];
  }

  it("selects every available video and queues them with the defaults", async () => {
    show();
    expect(checkbox("[Private video]").disabled).toBe(true);
    expect(screen.getByText("No longer available")).toBeDefined();
    expect(screen.getByText(/3 of 4 selected/)).toBeDefined();

    expect(await submit(/^Download 3 videos$/)).toEqual({
      url: SOURCE,
      entry_ids: ["vid001", "vid002", "vid003"],
      mode: "video",
      preset: "best_1080",
      subfolder: true,
      skip_existing: true,
      subtitles: false,
      subtitle_langs: null,
    });
    expect(await screen.findByText("downloads page")).toBeDefined();
  });

  it("sends the chosen subset in playlist order", async () => {
    show();
    fireEvent.click(checkbox("Second Video"));
    fireEvent.click(checkbox("Second Video"));
    fireEvent.click(checkbox("First Video"));
    expect((await submit(/^Download 2 videos$/)).entry_ids).toEqual(["vid002", "vid003"]);
  });

  it("disables download when nothing is selected", () => {
    show();
    fireEvent.click(screen.getByRole("button", { name: "Select none" }));
    expect(screen.getByRole("button", { name: "Download 0 videos" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  it("selects only the videos matching the filter", async () => {
    const entries = Array.from({ length: 10 }, (_, i) =>
      makeEntry({ id: `v${i}`, index: i + 1, title: i < 2 ? `Go part ${i}` : `Rust ${i}` }),
    );
    show(makeCollectionInfo({ entries }));
    fireEvent.click(screen.getByRole("button", { name: "Select none" }));
    fireEvent.change(screen.getByLabelText("Filter videos by title"), {
      target: { value: "go" },
    });
    expect(screen.queryByText("Rust 5")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Select all" }));
    expect((await submit(/^Download 2 videos$/)).entry_ids).toEqual(["v0", "v1"]);
  });

  it("queues audio with the chosen format and the folder options", async () => {
    show();
    fireEvent.click(screen.getByRole("button", { name: "Audio" }));
    fireEvent.change(screen.getByLabelText(/^Audio format/), { target: { value: "opus" } });
    fireEvent.click(screen.getByRole("switch", { name: "Save into a playlist folder" }));
    fireEvent.click(screen.getByRole("switch", { name: "Skip videos already downloaded" }));
    expect(await submit()).toMatchObject({
      mode: "audio",
      preset: "audio",
      audio_format: "opus",
      subfolder: false,
      skip_existing: false,
      subtitles: false,
    });
  });

  it("explains why nothing could be added", async () => {
    createCollection.mockRejectedValue(
      new ApiError(422, "None of the selected videos can be added", "NOTHING_TO_DOWNLOAD", {
        skipped: { already_downloaded: 3 },
      }),
    );
    show();
    fireEvent.click(screen.getByRole("button", { name: "Download 3 videos" }));
    expect(
      await screen.findByText("None of the selected videos can be added: 3 already downloaded."),
    ).toBeDefined();
  });

  it("renders nothing for a listing without videos", () => {
    const { container } = show(
      makeCollectionInfo({
        entries: [makeEntry({ id: "tab", kind: "collection", url: "https://x.test/@c/videos" })],
      }),
    );
    expect(container.textContent).toBe("");
  });
});
