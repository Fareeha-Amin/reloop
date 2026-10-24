import { describe, expect, it } from 'vitest';

import { createApi } from '../src/api/client';
import { ApiError, toApiError, unwrap } from '../src/api/errors';
import { REFRESH_TOKEN_KEY } from '../src/api/tokens';
import { BASE, fakeBackend, json, MemoryStorage, USER } from './fakeBackend';

function setup(handler: Parameters<typeof fakeBackend>[0]) {
  const backend = fakeBackend(handler);
  const storage = new MemoryStorage();
  const api = createApi({ baseUrl: BASE, storage, onSessionEnded: () => {}, fetch: backend.fetch });
  return { api, storage, requests: backend.requests };
}

describe('API client', () => {
  it('logs in with the OAuth2 form, keeps the access token in memory and the refresh token in storage', async () => {
    const { api, storage, requests } = setup((request) => {
      const path = new URL(request.url).pathname;
      if (path === '/api/auth/login') return json(200, { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' });
      if (path === '/api/auth/me') return json(200, USER);
      return json(404, { detail: 'Not found' });
    });

    const user = await api.login('asha@example.org', 'correct-horse');

    expect(user.email).toBe('asha@example.org');
    expect(requests[0]).toMatchObject({
      method: 'POST',
      path: '/auth/login',
      contentType: 'application/x-www-form-urlencoded',
      body: 'username=asha%40example.org&password=correct-horse&scope=',
    });
    expect(requests[1]).toMatchObject({ path: '/auth/me', authorization: 'Bearer A1' });
    expect(api.store.accessToken).toBe('A1');
    expect(storage.getItem(REFRESH_TOKEN_KEY)).toBe('R1');
    expect(storage.keys()).toEqual([REFRESH_TOKEN_KEY]); // the access token is never persisted
  });

  it('sends no Authorization header without a session', async () => {
    const { api, requests } = setup(() => json(200, []));
    await unwrap(api.client.GET('/notifications'));
    expect(requests[0].authorization).toBeNull();
  });

  it('resolves paths under the base URL', async () => {
    const { api, requests } = setup(() => json(200, []));
    await unwrap(api.client.GET('/donations/{donation_id}/timeline', { params: { path: { donation_id: 'abc' } } }));
    expect(requests[0].path).toBe('/donations/abc/timeline');
  });

  it('uploads images as multipart form data, with the token', async () => {
    const { api, requests } = setup(() => json(201, []));
    api.store.setPair('A1', 'R1');
    const form = new FormData();
    form.append('files', new Blob([new Uint8Array([137, 80, 78, 71])], { type: 'image/png' }), 'a.png');

    await unwrap(
      api.client.POST('/donations/{donation_id}/images', {
        params: { path: { donation_id: 'd1' } },
        body: { files: [] },
        bodySerializer: () => form,
      }),
    );

    expect(requests[0].authorization).toBe('Bearer A1');
    expect(requests[0].contentType).toMatch(/^multipart\/form-data; boundary=/);
    expect(requests[0].body).toContain('name="files"; filename="a.png"');
  });

  it('logout forgets both tokens', async () => {
    const { api, storage } = setup(() => json(200, { access_token: 'A1', refresh_token: 'R1' }));
    api.store.setPair('A1', 'R1');
    api.logout();
    expect(api.store.accessToken).toBeNull();
    expect(storage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
    expect(api.hasSession()).toBe(false);
  });
});

describe('API errors', () => {
  it('turns a text detail into an ApiError', async () => {
    const { api } = setup(() => json(409, { detail: 'A MATCHED donation can no longer be edited.' }));
    const error = await unwrap(api.client.GET('/notifications')).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(409);
    expect(error.detail).toBe('A MATCHED donation can no longer be edited.');
  });

  it('maps validation errors to field paths, and model-level ones to the form', () => {
    const error = toApiError(422, {
      detail: [
        { loc: ['body', 'quantity'], msg: 'Input should be greater than or equal to 1', type: 'greater_than_equal' },
        { loc: ['body', 'organization', 'name'], msg: 'Field required', type: 'missing' },
        { loc: ['body'], msg: 'Value error, pickup_window_end must be after pickup_window_start.', type: 'value_error' },
        { loc: ['query', 'limit'], msg: 'Input should be less than or equal to 100', type: 'less_than_equal' },
      ],
    });
    expect(error.fieldErrors).toEqual({
      quantity: 'Input should be greater than or equal to 1',
      'organization.name': 'Field required',
      limit: 'Input should be less than or equal to 100',
    });
    expect(error.formErrors).toEqual(['pickup_window_end must be after pickup_window_start.']);
    expect(error.detail).toBeNull();
  });

  it('copes with a body that is not JSON-shaped', () => {
    const error = toApiError(502, null);
    expect(error.status).toBe(502);
    expect(error.message).toBe('HTTP 502');
  });
});
