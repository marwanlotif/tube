import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "./client";
import type { CreateDownload, DownloadList, Settings } from "./models";

export const queryKeys = {
  downloads: ["downloads"] as const,
  stats: ["stats"] as const,
  settings: ["settings"] as const,
  system: ["system"] as const,
};

export function useDownloads() {
  return useQuery({
    queryKey: queryKeys.downloads,
    queryFn: api.listDownloads,
  });
}

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: api.getStats,
    refetchInterval: 15000,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: api.getSettings,
  });
}

export function useSystem() {
  return useQuery({
    queryKey: queryKeys.system,
    queryFn: api.getSystem,
    staleTime: 60_000,
  });
}

function patchDownloadList(
  queryClient: ReturnType<typeof useQueryClient>,
  updater: (list: DownloadList) => DownloadList,
) {
  queryClient.setQueriesData<DownloadList>(
    { queryKey: queryKeys.downloads },
    (old) => (old ? updater(old) : old),
  );
}

export function useCreateDownload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDownload) => api.createDownload(payload),
    onSuccess: (download) => {
      queryClient.setQueryData(["download", download.id], download);
      queryClient.invalidateQueries({ queryKey: queryKeys.downloads });
      queryClient.invalidateQueries({ queryKey: queryKeys.stats });
    },
  });
}

export function useDownloadAction(action: "cancel" | "retry" | "reveal") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string): Promise<unknown> => api[action](id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.downloads });
      queryClient.invalidateQueries({ queryKey: queryKeys.stats });
    },
  });
}

export function useDeleteDownload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, deleteFile }: { id: string; deleteFile: boolean }) =>
      api.remove(id, deleteFile),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.downloads });
      queryClient.invalidateQueries({ queryKey: queryKeys.stats });
    },
  });
}

export function useSaveSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: Settings) => api.updateSettings(settings),
    onSuccess: (settings) => {
      queryClient.setQueryData(queryKeys.settings, settings);
      queryClient.invalidateQueries({ queryKey: queryKeys.system });
    },
  });
}

export { patchDownloadList };
