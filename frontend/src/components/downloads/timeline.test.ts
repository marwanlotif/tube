import { describe, expect, it } from "vitest";

import { makeCollection, makeDownload } from "@/test/fixtures";

import {
  buildTimeline,
  collectionStatusLine,
  countByFilter,
  matches,
  type TimelineRow,
} from "./timeline";

const asRow = (collection = makeCollection()): TimelineRow => ({
  type: "collection",
  id: collection.id,
  collection,
});

describe("buildTimeline", () => {
  it("puts active rows first, then newest first, across both kinds", () => {
    const rows = buildTimeline(
      [
        makeDownload({ id: "old-done", status: "completed", created_at: "2026-11-01T00:00:00Z" }),
        makeDownload({ id: "new-done", status: "completed", created_at: "2026-11-07T00:00:00Z" }),
      ],
      [
        makeCollection({ id: "running", active_total: 2, created_at: "2026-10-01T00:00:00Z" }),
        makeCollection({ id: "finished", active_total: 0, created_at: "2026-11-05T00:00:00Z" }),
      ],
    );
    expect(rows.map((row) => row.id)).toEqual(["running", "new-done", "finished", "old-done"]);
  });
});

describe("collection filters", () => {
  it("is completed only when every item is", () => {
    const done = makeCollection({ active_total: 0, completed_total: 3, item_total: 3 });
    const partial = makeCollection({ active_total: 0, completed_total: 2, item_total: 3 });
    const empty = makeCollection({ active_total: 0, completed_total: 0, item_total: 0 });
    expect(matches(asRow(done), "completed")).toBe(true);
    expect(matches(asRow(partial), "completed")).toBe(false);
    expect(matches(asRow(empty), "completed")).toBe(false);
  });

  it("needs attention while any item can be retried", () => {
    const row = asRow(makeCollection({ active_total: 1, failed_total: 1 }));
    expect(matches(row, "failed")).toBe(true);
    expect(matches(row, "active")).toBe(true);
    expect(matches(asRow(makeCollection({ failed_total: 0 })), "failed")).toBe(false);
  });

  it("counts a collection once per filter", () => {
    const rows = buildTimeline(
      [makeDownload({ status: "failed" })],
      [makeCollection({ active_total: 0, completed_total: 3, item_total: 3 })],
    );
    expect(countByFilter(rows)).toEqual({ all: 2, active: 0, completed: 1, failed: 1 });
  });
});

describe("collectionStatusLine", () => {
  it("summarises the item states that are present", () => {
    const line = collectionStatusLine(
      makeCollection({
        item_total: 10,
        completed_total: 4,
        counts: { completed: 4, downloading: 1, extracting: 1, queued: 2, failed: 1, canceled: 1 },
      }),
    );
    expect(line).toBe("4 of 10 done · 2 downloading · 2 queued · 1 failed · 1 canceled");
    expect(collectionStatusLine(makeCollection({ completed_total: 0, counts: {} }))).toBe(
      "0 of 3 done",
    );
  });
});
