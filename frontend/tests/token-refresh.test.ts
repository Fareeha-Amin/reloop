import { describe, expect, it, vi } from 'vitest';

import { createApi } from '../src/api/client';
import { unwrap } from '../src/api/errors';
import { REFRESH_TOKEN_KEY } from '../src/api/tokens';
import { BASE, fakeBackend, json, MemoryStorage } from './fakeBackend';

/** A backend whose only valid access token is `valid`, refreshed from refresh token R1. */
function backendWithTokens(options: { refreshStatus?: number; valid?: string } = {}) {
  const valid = options.valid ?? 'A2';
  let refreshes = 0;
  const backend = fakeBackend(async (request, body) => {
    const path = new URL(request.url).pathname;
    if (path === '/api/auth/refresh') {
      refreshes += 1;
      await new Promise((resolve) => setTimeout(resolve, 5)); // let concurrent 401s pile up
      if (options.refreshStatus) return json(options.refreshStatus, { detail: 'nope' });
      expect(JSON.parse(body)).toEqual({ refresh_token: 'R1' });
      return json(200, { access_token: valid, token_type: 'bearer' });
    }
    if (request.headers.get('Authorization') !== `Bearer ${valid}`) {
      return json(401, { detail: 'Token has expired.' });
    }
    return json(200, { path, body });
  });
  return { ...backend, refreshCount: () => refreshes };
}

function apiWith(backend: ReturnType<typeof backendWithTokens>, access: string | null) {
  const storage = new MemoryStorage();
  const onSessionEnded = vi.fn();
  const api = createApi({ baseUrl: BASE, storage, onSessionEnded, fetch: backend.fetch });
  storage.setItem(REFRESH_TOKEN_KEY, 'R1');
  if (access) api.store.setAccess(access);
  return { api, storage, onSessionEnded };
}

describe('token refresh', () => {
  it('refreshes once on a 401 and retries the request with the new token', async () => {
    const backend = backendWithTokens();
    const { api } = apiWith(backend, 'A1-expired');

    const data = await unwrap(api.client.GET('/notifications'));

    expect(data).toEqual({ path: '/api/notifications', body: '' });
    expect(backend.refreshCount()).toBe(1);
    expect(api.store.accessToken).toBe('A2');
    expect(backend.requests.map((r) => [r.path, r.authorization])).toEqual([
      ['/notifications', 'Bearer A1-expired'],
      ['/auth/refresh', null],
      ['/notifications', 'Bearer A2'],
    ]);
  });

  it('shares one refresh between requests that fail together', async () => {
    const backend = backendWithTokens();
    const { api } = apiWith(backend, 'A1-expired');

    const results = await Promise.all([
      unwrap(api.client.GET('/notifications')),
      unwrap(api.client.GET('/donations')),
      unwrap(api.client.GET('/auth/me')),
    ]);

    expect(results).toHaveLength(3);
    expect(backend.refreshCount()).toBe(1);
  });

  it('replays the request body on the retry', async () => {
    const backend = backendWithTokens();
    const { api } = apiWith(backend, 'A1-expired');

    const data = await unwrap(
      api.client.POST('/donations/{donation_id}/offer', {
        params: { path: { donation_id: 'd1' } },
        body: { organization_id: 'o1' },
      }),
    );

    expect(data).toEqual({ path: '/api/donations/d1/offer', body: '{"organization_id":"o1"}' });
  });

  it('resumes a session after reload by refreshing before the first request', async () => {
    const backend = backendWithTokens();
    const { api } = apiWith(backend, null); // only the refresh token survived the reload

    await unwrap(api.client.GET('/auth/me'));

    expect(backend.requests.map((r) => r.path)).toEqual(['/auth/refresh', '/auth/me']);
  });

  it('ends the session when the refresh token is refused', async () => {
    const backend = backendWithTokens({ refreshStatus: 401 });
    const { api, storage, onSessionEnded } = apiWith(backend, 'A1-expired');

    const error = await unwrap(api.client.GET('/notifications')).catch((e) => e);

    expect(error.status).toBe(401);
    expect(onSessionEnded).toHaveBeenCalledTimes(1);
    expect(api.store.accessToken).toBeNull();
    expect(storage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
  });

  it('keeps the session when the refresh fails for a server fault', async () => {
    const backend = backendWithTokens({ refreshStatus: 503 });
    const { api, storage, onSessionEnded } = apiWith(backend, 'A1-expired');

    await expect(unwrap(api.client.GET('/notifications'))).rejects.toThrow();

    expect(onSessionEnded).not.toHaveBeenCalled();
    expect(storage.getItem(REFRESH_TOKEN_KEY)).toBe('R1');
  });

  it('does not retry when there is no session to refresh', async () => {
    const backend = backendWithTokens();
    const storage = new MemoryStorage();
    const api = createApi({ baseUrl: BASE, storage, onSessionEnded: () => {}, fetch: backend.fetch });

    const error = await unwrap(api.client.GET('/notifications')).catch((e) => e);

    expect(error.status).toBe(401);
    expect(backend.requests).toHaveLength(1);
  });
});
