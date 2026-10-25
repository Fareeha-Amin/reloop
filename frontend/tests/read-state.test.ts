import { describe, expect, it } from 'vitest';

import {
  EMPTY_READ_STATE,
  isRead,
  markAllRead,
  markRead,
  parseReadState,
  unreadCount,
  type Readable,
} from '../src/app/readState';

const item = (key: string, minute: number): Readable => ({ key, at: new Date(Date.UTC(2026, 9, 25, 10, minute)).toISOString() });
const a = item('DONATION_EVENT:1', 1);
const b = item('CHAT_MESSAGE:7', 2);
const c = item('ORGANISATION_REGISTERED:x', 3);
const feed = [c, b, a]; // newest first, as the API sends it
const MAX = 500;

describe('notification read state', () => {
  it('starts with everything unread', () => {
    expect(unreadCount(EMPTY_READ_STATE, feed)).toBe(3);
  });

  it('marks one item read and leaves the others alone', () => {
    const state = markRead(EMPTY_READ_STATE, [b], MAX);
    expect(isRead(state, b)).toBe(true);
    expect(isRead(state, a)).toBe(false);
    expect(isRead(state, c)).toBe(false);
    expect(unreadCount(state, feed)).toBe(2);
  });

  it('returns the same state when nothing new is marked, so nothing is written', () => {
    const once = markRead(EMPTY_READ_STATE, [b], MAX);
    expect(markRead(once, [b], MAX)).toBe(once);
    expect(markAllRead(EMPTY_READ_STATE, [], MAX)).toBe(EMPTY_READ_STATE);
  });

  it('marks all read up to the newest item, including older ones never loaded', () => {
    const state = markAllRead(EMPTY_READ_STATE, [c, b], MAX);
    expect(unreadCount(state, feed)).toBe(0);
    expect(isRead(state, item('DONATION_EVENT:0', 0))).toBe(true); // an older page
    expect(isRead(state, item('DONATION_EVENT:9', 4))).toBe(false); // arrived later
  });

  it('drops keys the watermark covers, and keeps at most the newest max keys', () => {
    const marked = markRead(EMPTY_READ_STATE, [a, b], MAX);
    expect(Object.keys(markAllRead(marked, [a], MAX).keys)).toEqual(['CHAT_MESSAGE:7']);

    const many = Array.from({ length: 5 }, (_, i) => item(`CHAT_MESSAGE:${i}`, i));
    const capped = markRead(EMPTY_READ_STATE, many, 3);
    expect(Object.keys(capped.keys).sort()).toEqual(['CHAT_MESSAGE:2', 'CHAT_MESSAGE:3', 'CHAT_MESSAGE:4']);
  });

  it('round-trips through storage and tolerates junk', () => {
    const state = markRead(markAllRead(EMPTY_READ_STATE, [a], MAX), [c], MAX);
    expect(parseReadState(JSON.stringify(state))).toEqual(state);
    expect(parseReadState(null)).toEqual(EMPTY_READ_STATE);
    expect(parseReadState('not json')).toEqual(EMPTY_READ_STATE);
    expect(parseReadState('12345')).toEqual(EMPTY_READ_STATE); // the old "newest id seen" marker
    expect(parseReadState(JSON.stringify({ readBefore: 'never', keys: { k: 'bad', [b.key]: b.at } }))).toEqual({
      readBefore: null,
      keys: { [b.key]: b.at },
    });
  });
});
