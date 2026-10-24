import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

import type { Role } from '../api/schema';
import { paths } from '../app/paths';
import { useSession } from '../app/session';
import { t } from '../i18n';
import { LoadingBlock } from '../ui/feedback';
import { homeFor } from '../vocab/roles';

/** Routing only: the API enforces every permission itself. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { state } = useSession();
  const location = useLocation();
  if (state.status === 'loading') return <LoadingBlock label={t('common.loading')} />;
  if (state.status !== 'authenticated') {
    return <Navigate to={paths.login} replace state={{ from: location.pathname }} />;
  }
  if (state.user.role !== role) return <Navigate to={homeFor(state.user.role)} replace />;
  return <>{children}</>;
}

/** Any signed-in user. */
export function RequireSession({ children }: { children: ReactNode }) {
  const { state } = useSession();
  const location = useLocation();
  if (state.status === 'loading') return <LoadingBlock label={t('common.loading')} />;
  if (state.status !== 'authenticated') {
    return <Navigate to={paths.login} replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
