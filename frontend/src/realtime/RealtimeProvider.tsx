import { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { getToken } from "@/api/client";
import { queryKeys } from "@/api/queries";
import type { Collection, CollectionList, DownloadList, DownloadOut } from "@/api/models";

import {
  filterOf,
  removeCollection,
  removeDownload,
  upsertCollection,
  upsertDownload,
} from "./cache";

const RealtimeContext = createContext(false);

export function useRealtimeStatus() {
  return useContext(RealtimeContext);
}

type Message =
  | { type: "snapshot"; downloads: DownloadOut[] }
  | { type: "download.updated"; download: DownloadOut }
  | { type: "download.deleted"; id: string }
  | { type: "stats.updated" }
  | { type: "collection.created"; collection: Collection }
  | { type: "collection.updated"; collection: Collection }
  | { type: "collection.deleted"; id: string }
  | { type: "pong" };

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let pingTimer: number | undefined;
    let disposed = false;
    let attempt = 0;

    // Each cached download list is updated according to its own filter.
    const patchLists = (
      updater: (list: DownloadList, key: readonly unknown[]) => DownloadList,
    ) => {
      for (const [key, list] of queryClient.getQueriesData<DownloadList>({
        queryKey: queryKeys.downloads,
      })) {
        if (list) queryClient.setQueryData(key, updater(list, key));
      }
    };
    const patchCollections = (updater: (list: CollectionList) => CollectionList) => {
      queryClient.setQueryData<CollectionList>(queryKeys.collections, (old) =>
        old ? updater(old) : old,
      );
    };

    const handle = (message: Message) => {
      switch (message.type) {
        case "snapshot":
          setConnected(true);
          attempt = 0;
          // Events may have been missed while disconnected: refetch what is cached.
          queryClient.invalidateQueries({ queryKey: queryKeys.downloads });
          queryClient.invalidateQueries({ queryKey: queryKeys.collections });
          queryClient.invalidateQueries({ queryKey: queryKeys.stats });
          return;
        case "download.updated":
          patchLists((list, key) => upsertDownload(list, message.download, filterOf(key)));
          queryClient.setQueryData(["download", message.download.id], message.download);
          return;
        case "download.deleted":
          patchLists((list) => removeDownload(list, message.id));
          queryClient.removeQueries({ queryKey: ["download", message.id] });
          return;
        case "collection.created":
        case "collection.updated":
          patchCollections((list) => upsertCollection(list, message.collection));
          return;
        case "collection.deleted":
          patchCollections((list) => removeCollection(list, message.id));
          queryClient.removeQueries({
            queryKey: queryKeys.downloadList({ collectionId: message.id }),
          });
          return;
        case "stats.updated":
          queryClient.invalidateQueries({ queryKey: queryKeys.stats });
          return;
      }
    };

    const schedule = () => {
      if (disposed) return;
      const delay = Math.min(10_000, 1_000 * 2 ** attempt);
      attempt += 1;
      retryTimer = window.setTimeout(connect, delay);
    };

    async function connect() {
      if (disposed) return;
      try {
        const token = await getToken();
        if (disposed) return;
        socket = new WebSocket(
          `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/api/ws`,
        );
        socket.onopen = () => {
          socket?.send(JSON.stringify({ type: "auth", token }));
        };
        socket.onmessage = (event) => {
          try {
            handle(JSON.parse(event.data) as Message);
          } catch {
            /* ignore malformed frames */
          }
        };
        socket.onclose = () => {
          setConnected(false);
          schedule();
        };
        socket.onerror = () => socket?.close();
      } catch {
        schedule();
      }
    }

    connect();
    pingTimer = window.setInterval(() => {
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "ping" }));
      }
    }, 25_000);

    return () => {
      disposed = true;
      window.clearTimeout(retryTimer);
      window.clearInterval(pingTimer);
      socket?.close();
    };
  }, [queryClient]);

  return <RealtimeContext.Provider value={connected}>{children}</RealtimeContext.Provider>;
}
