/**
 * Which notifications a user has read, as plain data (no storage, no React), so the rules
 * are unit-tested. The API keeps no read state; src/app/unread.ts stores this per user in
 * the browser.
 *
 * An item is read if its key was marked read, or if it is no newer than `readBefore`, the
 * time of the newest item when "Mark all as read" was last used. The watermark also covers
 * older pages of the feed that were never loaded. Keys at or before the watermark are
 * dropped, and at most `max` keys are kept (the newest), so storage stays bounded.
 */

export interface Readable {
  key: string;
  /** ISO timestamp from the API. */
  at: string;
}

export interface ReadState {
  readBefore: string | null;
  /** key -> the item's time, kept for pruning. */
  keys: Record<string, string>;
}

export const EMPTY_READ_STATE: ReadState = { readBefore: null, keys: {} };

const time = (iso: string): number => Date.parse(iso);

function coveredByWatermark(state: ReadState, at: string): boolean {
  return state.readBefore !== null && time(at) <= time(state.readBefore);
}

export function isRead(state: ReadState, item: Readable): boolean {
  return coveredByWatermark(state, item.at) || Object.hasOwn(state.keys, item.key);
}

export function unreadCount(state: ReadState, items: Readable[]): number {
  return items.filter((item) => !isRead(state, item)).length;
}

export function prune(state: ReadState, max: number): ReadState {
  const kept = Object.entries(state.keys)
    .filter(([, at]) => !coveredByWatermark(state, at))
    .sort(([, a], [, b]) => time(b) - time(a))
    .slice(0, max);
  return { readBefore: state.readBefore, keys: Object.fromEntries(kept) };
}

/** Mark one item read; the rest are untouched. */
export function markRead(state: ReadState, items: Readable[], max: number): ReadState {
  const fresh = items.filter((item) => !isRead(state, item));
  if (fresh.length === 0) return state;
  const keys = { ...state.keys };
  for (const item of fresh) keys[item.key] = item.at;
  return prune({ readBefore: state.readBefore, keys }, max);
}

/** Everything up to the newest of `items` (and anything older, loaded or not) is read. */
export function markAllRead(state: ReadState, items: Readable[], max: number): ReadState {
  const newest = items.reduce<string | null>((acc, item) => (acc === null || time(item.at) > time(acc) ? item.at : acc), null);
  if (newest === null || coveredByWatermark(state, newest)) return state;
  return prune({ readBefore: newest, keys: state.keys }, max);
}

/** Tolerates missing or malformed stored data: anything unreadable counts as nothing read. */
export function parseReadState(raw: string | null): ReadState {
  if (!raw) return EMPTY_READ_STATE;
  try {
    const value = JSON.parse(raw) as Partial<ReadState>;
    const readBefore = typeof value.readBefore === 'string' && !Number.isNaN(time(value.readBefore)) ? value.readBefore : null;
    const keys =
      value.keys && typeof value.keys === 'object'
        ? Object.fromEntries(Object.entries(value.keys).filter(([, at]) => typeof at === 'string' && !Number.isNaN(time(at))))
        : {};
    return { readBefore, keys };
  } catch {
    return EMPTY_READ_STATE;
  }
}
