/** The app's one API instance. */

import { createApi } from '../api/client';
import { browserStorage } from '../api/tokens';
import { API_BASE_URL } from '../config';

const sessionEndedListeners = new Set<() => void>();

export const api = createApi({
  baseUrl: API_BASE_URL,
  storage: browserStorage(),
  onSessionEnded: () => sessionEndedListeners.forEach((listener) => listener()),
});

/** Subscribe to the session ending (a refresh token was refused). Returns an unsubscribe. */
export function onSessionEnded(listener: () => void): () => void {
  sessionEndedListeners.add(listener);
  return () => sessionEndedListeners.delete(listener);
}

export const client = api.client;
