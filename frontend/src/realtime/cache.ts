import type { QueryKey } from "@tanstack/react-query";

import type {
  Collection,
  CollectionList,
  DownloadFilter,
  DownloadList,
  DownloadOut,
} from "@/api/models";

/**
 * Pure helpers that fold live WebSocket events into cached query data.
 *
 * Download lists are cached per filter (see `queryKeys.downloadList`): the history of
 * standalone downloads, one list per collection, or every download. An update must only
 * land in the lists it belongs to — otherwise every playlist item would be prepended to
 * the main history.
 */

export function filterOf(queryKey: QueryKey): DownloadFilter {
  const filter = queryKey[1];
  return filter && typeof filter === "object" ? (filter as DownloadFilter) : {};
}

export function belongsTo(download: DownloadOut, filter: DownloadFilter): boolean {
  if (filter.collectionId) return download.collection_id === filter.collectionId;
  if (filter.standalone) return !download.collection_id;
  return true;
}

function byPlaylistIndex(a: DownloadOut, b: DownloadOut): number {
  return (a.playlist_index ?? 0) - (b.playlist_index ?? 0);
}

export function upsertDownload(
  list: DownloadList,
  download: DownloadOut,
  filter: DownloadFilter,
): DownloadList {
  const exists = list.items.some((item) => item.id === download.id);
  if (!belongsTo(download, filter)) {
    return exists ? removeDownload(list, download.id) : list;
  }
  if (exists) {
    return {
      ...list,
      items: list.items.map((item) => (item.id === download.id ? download : item)),
    };
  }
  // Collection lists are in playlist order; every other list is newest first.
  const items = filter.collectionId
    ? [...list.items, download].sort(byPlaylistIndex)
    : [download, ...list.items];
  return { ...list, items, total: list.total + 1 };
}

export function removeDownload(list: DownloadList, id: string): DownloadList {
  if (!list.items.some((item) => item.id === id)) return list;
  return {
    ...list,
    items: list.items.filter((item) => item.id !== id),
    total: Math.max(0, list.total - 1),
  };
}

export function upsertCollection(list: CollectionList, collection: Collection): CollectionList {
  const exists = list.items.some((item) => item.id === collection.id);
  if (exists) {
    return {
      ...list,
      items: list.items.map((item) => (item.id === collection.id ? collection : item)),
    };
  }
  return { ...list, items: [collection, ...list.items], total: list.total + 1 };
}

export function removeCollection(list: CollectionList, id: string): CollectionList {
  if (!list.items.some((item) => item.id === id)) return list;
  return {
    ...list,
    items: list.items.filter((item) => item.id !== id),
    total: Math.max(0, list.total - 1),
  };
}
