import { describe, expect, it } from "vitest";

import type { CollectionEntry } from "@/api/models";

import {
  describeSkipped,
  initialSelection,
  matchingEntries,
  nestedOf,
  selectedIds,
  setSelected,
  toggle,
  totalDuration,
  videosOf,
} from "./selection";

const entry = (id: string, overrides: Partial<CollectionEntry> = {}): CollectionEntry => ({
  id,
  index: Number(id.replace(/\D/g, "")) || 1,
  title: `Video ${id}`,
  url: `https://x.test/${id}`,
  duration_s: 60,
  kind: "video",
  available: true,
  reason: null,
  ...overrides,
});

const entries = [
  entry("v1", { title: "Intro to Go" }),
  entry("v2", { title: "Goroutines", duration_s: 120 }),
  entry("v3", { available: false, reason: "Private video" }),
  entry("v4", { title: "Channels", duration_s: null }),
  entry("tab", { kind: "collection", url: "https://x.test/@c/videos", title: "Videos" }),
  entry("orphan", { kind: "collection", url: null }),
];

describe("entry kinds", () => {
  it("separates videos from nested listings that can be opened", () => {
    expect(videosOf(entries).map((e) => e.id)).toEqual(["v1", "v2", "v3", "v4"]);
    expect(nestedOf(entries).map((e) => e.id)).toEqual(["tab"]);
  });
});

describe("selection", () => {
  it("starts with every available video selected", () => {
    expect([...initialSelection(entries)]).toEqual(["v1", "v2", "v4"]);
  });

  it("filters by title, case-insensitively", () => {
    expect(matchingEntries(entries, "  go ").map((e) => e.id)).toEqual(["v1", "v2"]);
    expect(matchingEntries(entries, "")).toBe(entries);
  });

  it("selects or clears only the given entries and never unavailable ones", () => {
    const none = setSelected(initialSelection(entries), videosOf(entries), false);
    expect(none.size).toBe(0);
    const visible = matchingEntries(videosOf(entries), "go");
    expect([...setSelected(none, visible, true)]).toEqual(["v1", "v2"]);
    expect(setSelected(new Set(), [entries[2]], true).has("v3")).toBe(false);
  });

  it("toggles single entries without mutating the original", () => {
    const start = new Set(["v1"]);
    expect([...toggle(start, "v2")]).toEqual(["v1", "v2"]);
    expect([...toggle(start, "v1")]).toEqual([]);
    expect([...start]).toEqual(["v1"]);
  });

  it("reports selected ids in playlist order, skipping unavailable ones", () => {
    expect(selectedIds(entries, new Set(["v4", "v3", "v1"]))).toEqual(["v1", "v4"]);
  });

  it("sums the known durations of the selection", () => {
    expect(totalDuration(entries, new Set(["v1", "v2", "v4"]))).toBe(180);
  });
});

describe("describeSkipped", () => {
  it("lists only the reasons that apply", () => {
    expect(describeSkipped({ already_downloaded: 3, unavailable: 1, blocked: 0 })).toBe(
      "3 already downloaded, 1 unavailable",
    );
    expect(describeSkipped({})).toBe("");
  });
});
