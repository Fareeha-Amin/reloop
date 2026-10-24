/**
 * Which notifications this user has seen, kept in this browser only: the id of the
 * newest event shown on the notifications page. There is no server-side read state, so
 * it does not follow the user to another device (README).
 */

import { useCallback, useSyncExternalStore } from 'react';

const key = (userId: string) => `reloop.notificationsSeen.${userId}`;
const listeners = new Set<() => void>();

function read(userId: string | null): number {
  if (!userId) return 0;
  try {
    return Number(window.localStorage.getItem(key(userId)) ?? 0) || 0;
  } catch {
    return 0;
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useSeenMarker(userId: string | null) {
  const seen = useSyncExternalStore(subscribe, () => read(userId));
  const markSeen = useCallback(
    (newestId: number) => {
      if (!userId || newestId <= read(userId)) return;
      try {
        window.localStorage.setItem(key(userId), String(newestId));
      } catch {
        // Storage unavailable: unread counts reset on reload.
      }
      listeners.forEach((listener) => listener());
    },
    [userId],
  );
  return { seen, markSeen };
}
