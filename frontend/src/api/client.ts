import createClient from 'openapi-fetch';

import { createAuthFetch } from './authFetch';
import { unwrap } from './errors';
import type { paths, TokenPair, UserOut } from './schema';
import { TokenStore, type KeyValueStorage } from './tokens';

export type ApiClient = ReturnType<typeof createClient<paths>>;

export interface ApiOptions {
  /** Absolute, or relative to the page in a browser ("/api"). */
  baseUrl: string;
  storage: KeyValueStorage | null;
  onSessionEnded: () => void;
  fetch?: (input: Request) => Promise<Response>;
}

export interface Api {
  client: ApiClient;
  store: TokenStore;
  /** True when a refresh token is stored, so a session can be resumed. */
  hasSession(): boolean;
  login(email: string, password: string): Promise<UserOut>;
  logout(): void;
}

export function createApi(options: ApiOptions): Api {
  const store = new TokenStore(options.storage);
  const baseFetch = options.fetch ?? ((input: Request) => globalThis.fetch(input));
  const base = options.baseUrl.replace(/\/$/, '');

  async function refresh(refreshToken: string): Promise<string | null> {
    const response = await baseFetch(
      new Request(`${base}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }),
    );
    if (response.status === 401 || response.status === 422) return null;
    if (!response.ok) throw new Error(`Token refresh failed with HTTP ${response.status}`);
    return ((await response.json()) as { access_token: string }).access_token;
  }

  const authFetch = createAuthFetch({
    store,
    refresh,
    onSessionEnded: options.onSessionEnded,
    fetch: baseFetch,
  });
  const client = createClient<paths>({ baseUrl: base, fetch: authFetch });

  return {
    client,
    store,
    hasSession: () => store.refreshToken !== null,
    async login(email, password) {
      // OAuth2 password flow: form-encoded, and the username is the email address.
      const tokens = await unwrap<TokenPair>(
        client.POST('/auth/login', {
          body: { username: email, password, scope: '' },
          bodySerializer: (body) => new URLSearchParams(body as Record<string, string>).toString(),
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        }),
      );
      store.setPair(tokens.access_token, tokens.refresh_token);
      return unwrap(client.GET('/auth/me'));
    },
    logout() {
      store.clear();
    },
  };
}
