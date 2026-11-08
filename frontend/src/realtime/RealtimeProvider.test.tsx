import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CollectionList, DownloadList } from "@/api/models";
import { queryKeys } from "@/api/queries";
import { makeCollection, makeDownload, makeList } from "@/test/fixtures";

import { RealtimeProvider } from "./RealtimeProvider";

class FakeSocket {
  static instances: FakeSocket[] = [];
  static OPEN = 1;
  readyState = FakeSocket.OPEN;
  sent: unknown[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(JSON.parse(data));
  }

  close() {}

  serverSends(message: unknown) {
    act(() => this.onmessage?.({ data: JSON.stringify(message) }));
  }
}

const standaloneKey = queryKeys.downloadList({ standalone: true });
const itemsKey = queryKeys.downloadList({ collectionId: "c1" });

async function mount(client: QueryClient): Promise<FakeSocket> {
  render(
    <QueryClientProvider client={client}>
      <RealtimeProvider>
        <span />
      </RealtimeProvider>
    </QueryClientProvider>,
  );
  await vi.waitFor(() => expect(FakeSocket.instances).toHaveLength(1));
  const socket = FakeSocket.instances[0];
  act(() => socket.onopen?.());
  return socket;
}

describe("RealtimeProvider", () => {
  let client: QueryClient;

  beforeEach(() => {
    FakeSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeSocket);
    const meta = document.createElement("meta");
    meta.name = "vid-dwn-token";
    meta.content = "secret-token";
    document.head.append(meta);
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData<DownloadList>(standaloneKey, makeList([makeDownload({ id: "solo" })]));
    client.setQueryData<DownloadList>(
      itemsKey,
      makeList([makeDownload({ id: "i1", collection_id: "c1", playlist_index: 1 })]),
    );
    client.setQueryData<CollectionList>(queryKeys.collections, {
      items: [makeCollection()],
      total: 1,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    document.head.innerHTML = "";
    client.clear();
  });

  it("authenticates with the page token as its first message", async () => {
    const socket = await mount(client);
    expect(socket.url).toMatch(/\/api\/ws$/);
    expect(socket.sent[0]).toEqual({ type: "auth", token: "secret-token" });
  });

  it("routes a playlist item update to its collection list only", async () => {
    const socket = await mount(client);
    socket.serverSends({
      type: "download.updated",
      download: makeDownload({ id: "i2", collection_id: "c1", playlist_index: 2 }),
    });

    expect(client.getQueryData<DownloadList>(itemsKey)?.items.map((d) => d.id)).toEqual([
      "i1",
      "i2",
    ]);
    expect(client.getQueryData<DownloadList>(standaloneKey)?.items.map((d) => d.id)).toEqual([
      "solo",
    ]);
  });

  it("applies collection progress and removal", async () => {
    const socket = await mount(client);
    socket.serverSends({
      type: "collection.updated",
      collection: makeCollection({ progress: 40, completed_total: 1 }),
    });
    expect(client.getQueryData<CollectionList>(queryKeys.collections)?.items[0]).toMatchObject({
      progress: 40,
      completed_total: 1,
    });

    socket.serverSends({ type: "collection.deleted", id: "c1" });
    expect(client.getQueryData<CollectionList>(queryKeys.collections)?.items).toEqual([]);
    expect(client.getQueryData(itemsKey)).toBeUndefined();
  });

  it("ignores malformed frames", async () => {
    const socket = await mount(client);
    act(() => socket.onmessage?.({ data: "not json" }));
    expect(client.getQueryData<DownloadList>(standaloneKey)?.items).toHaveLength(1);
  });
});
