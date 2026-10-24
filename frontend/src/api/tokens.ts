/**
 * Where the tokens live.
 *
 * The access token is kept in memory only, so it is gone on reload and never written to
 * disk. The refresh token is kept in localStorage so a session survives a reload. That is
 * the XSS trade-off stated in the README: script injected into this origin could read
 * the refresh token. The backend's refresh tokens are not revocable (see README, Known
 * limitations), so a stolen one is valid until it expires.
 */

export interface KeyValueStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export const REFRESH_TOKEN_KEY = 'reloop.refreshToken';

export class TokenStore {
  private access: string | null = null;

  constructor(private readonly storage: KeyValueStorage | null) {}

  get accessToken(): string | null {
    return this.access;
  }

  get refreshToken(): string | null {
    try {
      return this.storage?.getItem(REFRESH_TOKEN_KEY) ?? null;
    } catch {
      return null;
    }
  }

  setAccess(token: string): void {
    this.access = token;
  }

  setPair(access: string, refresh: string): void {
    this.access = access;
    try {
      this.storage?.setItem(REFRESH_TOKEN_KEY, refresh);
    } catch {
      // Storage unavailable (private mode, blocked): the session lasts until reload.
    }
  }

  clear(): void {
    this.access = null;
    try {
      this.storage?.removeItem(REFRESH_TOKEN_KEY);
    } catch {
      // Nothing stored.
    }
  }
}

/** localStorage, or null where the browser refuses access to it. */
export function browserStorage(): KeyValueStorage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}
