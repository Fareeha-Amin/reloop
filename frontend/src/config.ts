/**
 * Frontend settings: polling, map defaults and paging. Business tunables (weights,
 * timeouts, radii) live in the backend's app/constants.py and are never copied here.
 */

/** API base path. In development Vite proxies it to the backend (vite.config.ts). */
export const API_BASE_URL = '/api';

/** How often open pages re-read the API (TanStack Query; paused while the tab is hidden). */
export const POLL_MS = {
  notifications: 30_000,
  donation: 15_000,
  list: 30_000,
};

/** The notification feed page size, and where the unread badge stops counting. */
export const FEED_PAGE_SIZE = 30;
export const UNREAD_BADGE_MAX = 9;

export const MAP = {
  /** Central Bengaluru: where a location picker opens before a pin is placed. */
  center: [12.9716, 77.5946] as [number, number],
  zoom: 12,
  pinnedZoom: 15,
  maxZoom: 19,
  /** OpenStreetMap's public tiles: no API key. Fine for development and demos; production needs a tile provider (README). */
  tileUrl: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
};

/** Pickup windows are pre-filled as tomorrow, between these local hours. */
export const DEFAULT_WINDOW_HOURS = { start: 10, end: 18 };
