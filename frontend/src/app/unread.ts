/**
 * Which notifications this user has read, kept in this browser only (localStorage, per
 * user). There is no server-side read state, so it does not follow the user to another
 * device (README). The rules are in ./readState.
 */

import { useCallback, useMemo, useSyncExternalStore } from 'react';

import { READ_KEYS_MAX } from '../config';
import { isRead, markAllRead, markRead, parseReadState, unreadCount, type Readable, type ReadState } from './readState';

const storageKey = (userId: string) => `reloop.notificationsRead.${userId}`;
/** The Phase 3 (part 1) marker: the newest event id seen. Superseded; removed on sight. */
const legacyKey = (userId: string) => `reloop.notificationsSeen.${userId}`;

const listeners = new Set<() => void>();

function readRaw(userId: string | null): string | null {
  if (!userId) return null;
  try {
    return window.localStorage.getItem(storageKey(userId));
  } catch {
    return null;
  }
}

function write(userId: string, state: ReadState): void {
  try {
    window.localStorage.setItem(storageKey(userId), JSON.stringify(state));
    window.localStorage.removeItem(legacyKey(userId));
  } catch {
    // Storage unavailable: read state resets on reload.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  // Another tab of the same browser changed it.
  window.addEventListener('storage', listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener('storage', listener);
  };
}

export function useReadState(userId: string | null) {
  // The raw string is the snapshot: stable between changes, unlike a parsed object.
  const raw = useSyncExternalStore(subscribe, () => readRaw(userId));
  const state = useMemo(() => parseReadState(raw), [raw]);

  const update = useCallback(
    (change: (current: ReadState) => ReadState) => {
      if (!userId) return;
      const current = parseReadState(readRaw(userId));
      const next = change(current);
      if (next !== current) write(userId, next);
    },
    [userId],
  );

  return {
    isRead: useCallback((item: Readable) => isRead(state, item), [state]),
    unreadCount: useCallback((items: Readable[]) => unreadCount(state, items), [state]),
    /** Mark these items (one notification, or a thread's messages) read, and nothing else. */
    markRead: useCallback((...items: Readable[]) => update((s) => markRead(s, items, READ_KEYS_MAX)), [update]),
    markAllRead: useCallback((items: Readable[]) => update((s) => markAllRead(s, items, READ_KEYS_MAX)), [update]),
  };
}
