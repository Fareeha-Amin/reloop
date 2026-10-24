import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { ApiError, unwrap } from '../api/errors';
import type { UserOut } from '../api/schema';
import { api, client, onSessionEnded } from './api';

export type SessionState =
  | { status: 'loading' }
  | { status: 'anonymous' }
  | { status: 'unreachable' }
  | { status: 'authenticated'; user: UserOut };

interface Session {
  state: SessionState;
  user: UserOut | null;
  login(email: string, password: string): Promise<UserOut>;
  logout(): void;
  retry(): void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<SessionState>(() =>
    api.hasSession() ? { status: 'loading' } : { status: 'anonymous' },
  );

  const resume = useCallback(() => {
    if (!api.hasSession()) {
      setState({ status: 'anonymous' });
      return;
    }
    setState({ status: 'loading' });
    unwrap(client.GET('/auth/me'))
      .then((user) => setState({ status: 'authenticated', user }))
      .catch((error: unknown) => {
        // A refused session is over; a backend that cannot be reached is not a logout.
        if (error instanceof ApiError && error.status === 401) {
          api.logout();
          setState({ status: 'anonymous' });
        } else {
          setState({ status: 'unreachable' });
        }
      });
  }, []);

  useEffect(() => {
    resume();
  }, [resume]);

  useEffect(
    () =>
      onSessionEnded(() => {
        queryClient.clear();
        setState({ status: 'anonymous' });
      }),
    [queryClient],
  );

  const session = useMemo<Session>(
    () => ({
      state,
      user: state.status === 'authenticated' ? state.user : null,
      async login(email, password) {
        const user = await api.login(email, password);
        queryClient.clear();
        setState({ status: 'authenticated', user });
        return user;
      },
      logout() {
        api.logout();
        queryClient.clear();
        setState({ status: 'anonymous' });
      },
      retry: resume,
    }),
    [state, queryClient, resume],
  );

  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error('useSession must be used inside SessionProvider');
  return session;
}
