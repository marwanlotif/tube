import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { removeCollection, upsertCollection } from "@/realtime/cache";

import { api } from "./client";
import type {
  Collection,
  CollectionList,
  CreateCollection,
  CreateDownload,
  DownloadFilter,
  Settings,
} from "./models";

export const queryKeys = {
  /** Prefix shared by every download list, whatever its filter. */
  downloads: ["downloads"] as const,
  downloadList: (filter: DownloadFilter = {}) => ["downloads", filter] as const,
  collections: ["collections"] as const,
  stats: ["stats"] as const,
  settings: ["settings"] as const,
  system: ["system"] as const,
};

export function useDownloads(filter: DownloadFilter = {}, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.downloadList(filter),
    queryFn: () => api.listDownloads(filter),
    enabled: options.enabled ?? true,
  });
}

export function useCollections() {
  return useQuery({
    queryKey: queryKeys.collections,
    queryFn: api.listCollections,
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

export function useProbe() {
  return useMutation({
    mutationFn: ({ url, playlist = false }: { url: string; playlist?: boolean }) =>
      api.probe(url, playlist),
  });
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

function storeCollection(
  queryClient: ReturnType<typeof useQueryClient>,
  collection: Collection,
) {
  queryClient.setQueryData<CollectionList>(queryKeys.collections, (old) =>
    old ? upsertCollection(old, collection) : old,
  );
}

export function useCreateCollection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateCollection) => api.createCollection(payload),
    onSuccess: ({ collection }) => {
      storeCollection(queryClient, collection);
      queryClient.invalidateQueries({ queryKey: queryKeys.stats });
    },
  });
}

export function useCollectionAction(action: "cancel" | "retry") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      action === "cancel" ? api.cancelCollection(id) : api.retryCollection(id),
    onSuccess: (collection) => {
      storeCollection(queryClient, collection);
      queryClient.invalidateQueries({
        queryKey: queryKeys.downloadList({ collectionId: collection.id }),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.stats });
    },
  });
}

export function useDeleteCollection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, deleteFiles }: { id: string; deleteFiles: boolean }) =>
      api.removeCollection(id, deleteFiles),
    onSuccess: (_, { id }) => {
      queryClient.setQueryData<CollectionList>(queryKeys.collections, (old) =>
        old ? removeCollection(old, id) : old,
      );
      queryClient.removeQueries({ queryKey: queryKeys.downloadList({ collectionId: id }) });
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
