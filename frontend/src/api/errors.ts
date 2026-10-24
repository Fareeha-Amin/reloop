/**
 * Errors from the API, in one shape. FastAPI sends either {detail: "message"} or, for
 * validation failures (422), {detail: [{loc: ["body", "field"], msg, type}]}.
 *
 * Server messages are shown as sent, in English: they are not translated (README).
 */

export class ApiError extends Error {
  constructor(
    readonly status: number,
    /** The server's message, when it sent one as text. */
    readonly detail: string | null,
    /** Validation messages by field path, e.g. "quantity" or "organization.name". */
    readonly fieldErrors: Record<string, string>,
    /** Validation messages that belong to no single field. */
    readonly formErrors: string[],
  ) {
    super(detail ?? ([...formErrors, ...Object.values(fieldErrors)].join(' ') || `HTTP ${status}`));
    this.name = 'ApiError';
  }
}

interface ValidationItem {
  loc?: unknown[];
  msg?: string;
}

const LOCATION_PREFIXES = new Set(['body', 'query', 'path', 'header', 'cookie']);

function cleanMessage(msg: string): string {
  // Pydantic prefixes messages raised by validators.
  return msg.replace(/^Value error, /, '');
}

export function toApiError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string') return new ApiError(status, detail, {}, []);
  if (!Array.isArray(detail)) return new ApiError(status, null, {}, []);

  const fieldErrors: Record<string, string> = {};
  const formErrors: string[] = [];
  for (const item of detail as ValidationItem[]) {
    const message = cleanMessage(item.msg ?? '');
    const loc = (item.loc ?? []).map(String);
    const path = (LOCATION_PREFIXES.has(loc[0] ?? '') ? loc.slice(1) : loc).join('.');
    if (path === '') formErrors.push(message);
    else fieldErrors[path] ??= message;
  }
  return new ApiError(status, null, fieldErrors, formErrors);
}

/** openapi-fetch's result, or a thrown ApiError. */
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await call;
  if (!response.ok) throw toApiError(response.status, error);
  return data as T;
}
