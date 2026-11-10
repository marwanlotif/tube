import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, downloadQuery } from "./client";

function respond(status: number, body?: unknown, statusText = "") {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    statusText,
    headers: { "Content-Type": "application/json" },
  });
}

describe("downloadQuery", () => {
  it("encodes each list filter", () => {
    expect(downloadQuery({})).toBe("limit=200");
    expect(downloadQuery({ standalone: true })).toBe("limit=200&standalone=true");
    expect(downloadQuery({ collectionId: "c 1" })).toBe("collection_id=c+1&limit=500");
  });
});

describe("api requests", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    const meta = document.createElement("meta");
    meta.name = "vid-dwn-token";
    meta.content = "secret-token";
    document.head.append(meta);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
    document.head.innerHTML = "";
  });

  it("sends the token and the playlist flag when probing a link", async () => {
    fetchMock.mockResolvedValue(respond(200, { kind: "collection" }));
    await api.probe("https://x.test/list", true);

    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/videos/info");
    expect(new Headers(init?.headers).get("X-Vid-Dwn-Token")).toBe("secret-token");
    expect(JSON.parse(String(init?.body))).toEqual({
      url: "https://x.test/list",
      playlist: true,
    });
  });

  it("does not send the token on reads", async () => {
    fetchMock.mockResolvedValue(respond(200, { items: [], total: 0 }));
    await api.listDownloads({ collectionId: "c1" });
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/api/downloads?collection_id=c1&limit=500");
    expect(new Headers(init?.headers).has("X-Vid-Dwn-Token")).toBe(false);
  });

  it("surfaces the error code, message and details", async () => {
    fetchMock.mockResolvedValue(
      respond(422, {
        error: {
          code: "NOTHING_TO_DOWNLOAD",
          message: "None of the selected videos can be added",
          details: { skipped: { already_downloaded: 3 } },
        },
      }),
    );
    const error = await api
      .createCollection({
        url: "https://x.test/list",
        entry_ids: ["a"],
        mode: "video",
        subfolder: true,
        skip_existing: true,
      })
      .catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: "NOTHING_TO_DOWNLOAD",
      message: "None of the selected videos can be added",
      details: { skipped: { already_downloaded: 3 } },
    });
  });

  it("falls back to a generic message when the body is not an API error", async () => {
    fetchMock.mockResolvedValue(new Response("<html>", { status: 502, statusText: "" }));
    await expect(api.listCollections()).rejects.toMatchObject({
      status: 502,
      message: "Request failed",
    });
  });

  it("resolves deletes without a body", async () => {
    fetchMock.mockResolvedValue(respond(204));
    await expect(api.removeCollection("c1", true)).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/collections/c1?delete_files=true");
  });
});
