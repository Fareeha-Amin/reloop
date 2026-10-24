import type { TokenStore } from './tokens';

export interface AuthFetchOptions {
  store: TokenStore;
  /**
   * Exchange a refresh token for a new access token. Resolve null if the server refused
   * it (expired, invalid): the session is over. Reject on a network or server fault: the
   * session is kept and the request fails, so a backend restart does not log anyone out.
   */
  refresh: (refreshToken: string) => Promise<string | null>;
  /** Called once when a refresh is refused and the tokens have been cleared. */
  onSessionEnded: () => void;
  fetch?: (input: Request) => Promise<Response>;
}

/**
 * A fetch that adds the bearer token, and on a 401 refreshes the access token once and
 * retries the request once. Requests that fail together share a single refresh.
 */
export function createAuthFetch(options: AuthFetchOptions): (input: Request) => Promise<Response> {
  const { store } = options;
  const baseFetch = options.fetch ?? ((input: Request) => globalThis.fetch(input));
  let inflight: Promise<string | null> | null = null;

  function refreshOnce(): Promise<string | null> {
    const refreshToken = store.refreshToken;
    if (refreshToken === null) return Promise.resolve(null);
    inflight ??= options
      .refresh(refreshToken)
      .then((token) => {
        if (token === null) {
          store.clear();
          options.onSessionEnded();
        } else {
          store.setAccess(token);
        }
        return token;
      })
      .finally(() => {
        inflight = null;
      });
    return inflight;
  }

  function withToken(request: Request, token: string | null): Request {
    const authorised = new Request(request);
    if (token !== null) authorised.headers.set('Authorization', `Bearer ${token}`);
    return authorised;
  }

  return async function authFetch(input: Request): Promise<Response> {
    const retry = input.clone();
    let token = store.accessToken;
    if (token === null && store.refreshToken !== null) token = await refreshOnce();

    const response = await baseFetch(withToken(input, token));
    if (response.status !== 401 || store.refreshToken === null) return response;

    // Another request may already have refreshed while this one was in flight.
    const current = store.accessToken;
    const fresh = current !== null && current !== token ? current : await refreshOnce();
    if (fresh === null) return response;
    return baseFetch(withToken(retry, fresh));
  };
}
