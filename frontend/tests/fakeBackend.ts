/** A scripted stand-in for the API, recording every request it receives. */

export interface Recorded {
  method: string;
  path: string;
  authorization: string | null;
  contentType: string | null;
  body: string;
}

export type Handler = (request: Request, body: string) => Response | Promise<Response>;

export const BASE = 'http://reloop.test/api';

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

export class MemoryStorage {
  private data = new Map<string, string>();
  getItem(key: string) {
    return this.data.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.data.set(key, value);
  }
  removeItem(key: string) {
    this.data.delete(key);
  }
  keys() {
    return [...this.data.keys()];
  }
}

export function fakeBackend(handler: Handler) {
  const requests: Recorded[] = [];
  const fetch = async (request: Request): Promise<Response> => {
    const body = await request.clone().text();
    requests.push({
      method: request.method,
      path: new URL(request.url).pathname.replace(/^\/api/, ''),
      authorization: request.headers.get('Authorization'),
      contentType: request.headers.get('Content-Type'),
      body,
    });
    return handler(request, body);
  };
  return { fetch, requests };
}

export const USER = {
  id: '7f0c2b6e-1111-4c1e-9d1e-000000000001',
  email: 'asha@example.org',
  role: 'DONOR',
  full_name: 'Asha Rao',
  phone: null,
  created_at: '2026-10-01T00:00:00Z',
};
