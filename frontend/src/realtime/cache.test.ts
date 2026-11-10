import { describe, expect, it } from "vitest";

import { queryKeys } from "@/api/queries";
import { makeCollection, makeDownload, makeList } from "@/test/fixtures";

import {
  belongsTo,
  filterOf,
  removeCollection,
  removeDownload,
  upsertCollection,
  upsertDownload,
} from "./cache";

const standalone = { standalone: true };
const collectionC1 = { collectionId: "c1" };

describe("filterOf", () => {
  it("reads the filter stored in a download list key", () => {
    expect(filterOf(queryKeys.downloadList(standalone))).toEqual(standalone);
    expect(filterOf(queryKeys.downloadList())).toEqual({});
    expect(filterOf(queryKeys.downloads)).toEqual({});
  });
});

describe("belongsTo", () => {
  const solo = makeDownload();
  const item = makeDownload({ id: "i1", collection_id: "c1", playlist_index: 1 });

  it("routes by collection", () => {
    expect(belongsTo(solo, standalone)).toBe(true);
    expect(belongsTo(item, standalone)).toBe(false);
    expect(belongsTo(item, collectionC1)).toBe(true);
    expect(belongsTo(item, { collectionId: "other" })).toBe(false);
    expect(belongsTo(item, {})).toBe(true);
  });
});

describe("upsertDownload", () => {
  it("never adds a playlist item to the standalone history", () => {
    const list = makeList([makeDownload()]);
    const item = makeDownload({ id: "i1", collection_id: "c1" });
    expect(upsertDownload(list, item, standalone)).toBe(list);
  });

  it("prepends new standalone downloads and replaces known ones", () => {
    const first = makeDownload({ id: "a" });
    const list = makeList([first]);
    const added = upsertDownload(list, makeDownload({ id: "b" }), standalone);
    expect(added.items.map((d) => d.id)).toEqual(["b", "a"]);
    expect(added.total).toBe(2);

    const updated = upsertDownload(added, { ...first, status: "downloading" }, standalone);
    expect(updated.items.find((d) => d.id === "a")?.status).toBe("downloading");
    expect(updated.total).toBe(2);
  });

  it("keeps a collection's items in playlist order", () => {
    const at = (id: string, index: number) =>
      makeDownload({ id, collection_id: "c1", playlist_index: index });
    let list = makeList([at("x1", 1), at("x3", 3)]);
    list = upsertDownload(list, at("x2", 2), collectionC1);
    expect(list.items.map((d) => d.id)).toEqual(["x1", "x2", "x3"]);
  });

  it("drops an entry that no longer belongs to the list", () => {
    const moved = makeDownload({ id: "a" });
    const list = makeList([moved]);
    const result = upsertDownload(list, { ...moved, collection_id: "c1" }, standalone);
    expect(result.items).toEqual([]);
    expect(result.total).toBe(0);
  });
});

describe("removeDownload", () => {
  it("removes by id and leaves unrelated lists untouched", () => {
    const list = makeList([makeDownload({ id: "a" }), makeDownload({ id: "b" })]);
    expect(removeDownload(list, "a").items.map((d) => d.id)).toEqual(["b"]);
    expect(removeDownload(list, "zzz")).toBe(list);
  });
});

describe("collections", () => {
  it("upserts newest first and removes by id", () => {
    const list = { items: [makeCollection({ id: "old" })], total: 1 };
    const added = upsertCollection(list, makeCollection({ id: "new" }));
    expect(added.items.map((c) => c.id)).toEqual(["new", "old"]);
    expect(added.total).toBe(2);

    const progressed = upsertCollection(added, makeCollection({ id: "old", progress: 50 }));
    expect(progressed.items.find((c) => c.id === "old")?.progress).toBe(50);
    expect(progressed.total).toBe(2);

    expect(removeCollection(progressed, "new").items.map((c) => c.id)).toEqual(["old"]);
    expect(removeCollection(progressed, "missing")).toBe(progressed);
  });
});
