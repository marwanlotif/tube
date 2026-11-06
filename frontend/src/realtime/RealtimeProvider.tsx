import { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { getToken } from "@/api/client";
import { queryKeys } from "@/api/queries";
import type { DownloadList, DownloadOut } from "@/api/models";

const RealtimeContext = createContext(false);

export function useRealtimeStatus() {
  return useContext(RealtimeContext);
}

type Message =
  | { type: "snapshot"; downloads: DownloadOut[] }
  | { type: "download.updated"; download: DownloadOut }
  | { type: "download.deleted"; id: string }
  | { type: "stats.updated" }
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

    const patchList = (updater: (list: DownloadList) => DownloadList) => {
      queryClient.setQueriesData<DownloadList>(
        { queryKey: queryKeys.downloads },
        (old) => (old ? updater(old) : old),
      );
    };

    const handle = (message: Message) => {
      if (message.type === "snapshot") {
        setConnected(true);
        attempt = 0;
        queryClient.invalidateQueries({ queryKey: queryKeys.downloads });
        queryClient.invalidateQueries({ queryKey: queryKeys.stats });
        return;
      }
      if (message.type === "download.updated") {
        const download = message.download;
        patchList((list) => {
          const exists = list.items.some((item) => item.id === download.id);
          return {
            ...list,
            items: exists
              ? list.items.map((item) => (item.id === download.id ? download : item))
              : [download, ...list.items],
            total: exists ? list.total : list.total + 1,
          };
        });
        queryClient.setQueryData(["download", download.id], download);
        return;
      }
      if (message.type === "download.deleted") {
        patchList((list) => ({
          ...list,
          items: list.items.filter((item) => item.id !== message.id),
          total: Math.max(0, list.total - 1),
        }));
        queryClient.removeQueries({ queryKey: ["download", message.id] });
        return;
      }
      if (message.type === "stats.updated") {
        queryClient.invalidateQueries({ queryKey: queryKeys.stats });
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
