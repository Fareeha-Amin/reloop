/**
 * Frontend settings: polling, map defaults and paging. Business tunables (weights,
 * timeouts, radii) live in the backend's app/constants.py and are never copied here.
 */

/** API base path. In development Vite proxies it to the backend (vite.config.ts). */
export const API_BASE_URL = '/api';

/**
 * Whether pages show where a breakdown's weights came from: the version, whether they are
 * the assigned prior or a fit, what a fit was trained on, and the "demo fit" marker. OFF for
 * the college demo, which discloses the demo fit verbally instead. This hides the display
 * only: the API still returns every field (ModelOut) and the admin JSON still has it. Turn it
 * back on for anything beyond that demo, so a viewer is never left to assume learned weights.
 */
export const SHOW_MODEL_NOTE = false;

/** How often open pages re-read the API (TanStack Query; paused while the tab is hidden). */
export const POLL_MS = {
  notifications: 30_000,
  donation: 15_000,
  list: 30_000,
  chat: 10_000,
};

/** The notification feed page size, and where the unread badge stops counting. */
export const FEED_PAGE_SIZE = 30;
export const UNREAD_BADGE_MAX = 9;
/** How many individually-read notification keys a browser remembers per user (src/app/readState.ts). */
export const READ_KEYS_MAX = 500;

/** Rows per page in the admin panel's lists. */
export const ADMIN_PAGE_SIZE = 25;

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
