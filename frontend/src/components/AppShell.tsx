import { Link, NavLink, Outlet, useNavigate } from 'react-router';

import { paths } from '../app/paths';
import { useNotifications } from '../app/queries';
import { useSession } from '../app/session';
import { useSeenMarker } from '../app/unread';
import { UNREAD_BADGE_MAX } from '../config';
import { t } from '../i18n';
import { Button, LinkButton } from '../ui/Button';
import { Alert } from '../ui/feedback';
import { Icon, LogoMark } from '../ui/icons';
import { ThemeToggle } from '../ui/ThemeToggle';
import { homeFor, navFor } from '../vocab/roles';
import { vocabLabel } from '../vocab/display';

function NotificationBell({ userId }: { userId: string }) {
  const { data } = useNotifications(true);
  const { seen } = useSeenMarker(userId);
  const unread = (data ?? []).filter((n) => n.id > seen).length;
  const label = unread > UNREAD_BADGE_MAX ? `${UNREAD_BADGE_MAX}+` : String(unread);
  return (
    <Link
      to={paths.notifications}
      className="relative grid size-10 place-items-center rounded-full text-ink-soft transition hover:bg-surface-muted hover:text-ink"
      aria-label={t('nav.notificationsUnread', { count: unread })}
    >
      <Icon name="bell" />
      {unread > 0 && (
        <span className="absolute -top-0.5 -right-0.5 grid h-5 min-w-5 place-items-center rounded-pill bg-clay-500 px-1 text-[11px] font-bold text-surface ring-2 ring-canvas">
          {label}
        </span>
      )}
    </Link>
  );
}

function Header() {
  const { user, logout } = useSession();
  const navigate = useNavigate();
  const nav = user ? navFor(user.role) : [];

  return (
    <header className="sticky top-0 z-[1100] border-b border-line/80 bg-canvas/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <Link to={user ? homeFor(user.role) : paths.home} className="flex items-center gap-2.5">
          <LogoMark className="size-8" />
          <span className="font-display text-xl font-semibold tracking-tight">{t('app.name')}</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label={t('nav.main')}>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-pill px-3.5 py-2 text-sm font-semibold transition ${
                  isActive ? 'bg-brand-900 text-leaf' : 'text-ink-soft hover:bg-surface-muted hover:text-ink'
                }`
              }
            >
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <ThemeToggle toDarkLabel={t('nav.toDark')} toLightLabel={t('nav.toLight')} />
          {user ? (
            <>
              <NotificationBell userId={user.id} />
              <div className="hidden text-right leading-tight sm:block">
                <p className="text-sm font-semibold">{user.full_name}</p>
                <p className="text-xs text-ink-muted">{vocabLabel('Role', user.role)}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                icon="logout"
                onClick={() => {
                  logout();
                  navigate(paths.home);
                }}
              >
                <span className="hidden sm:inline">{t('nav.logout')}</span>
              </Button>
            </>
          ) : (
            <>
              <span className="hidden sm:contents">
                <LinkButton to={paths.map} variant="ghost" size="sm" icon="map">
                  {t('nav.map')}
                </LinkButton>
              </span>
              <LinkButton to={paths.login} variant="ghost" size="sm">
                {t('nav.login')}
              </LinkButton>
              <LinkButton to={paths.register} size="sm">
                {t('nav.getStarted')}
              </LinkButton>
            </>
          )}
        </div>
      </div>

      {nav.length > 0 && (
        <nav className="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden" aria-label={t('nav.main')}>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `inline-flex shrink-0 items-center gap-1.5 rounded-pill px-3 py-1.5 text-sm font-semibold ${
                  isActive ? 'bg-brand-900 text-leaf' : 'bg-surface text-ink-soft ring-1 ring-line'
                }`
              }
            >
              <Icon name={item.icon} className="size-4" />
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  );
}

function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-ink-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="flex items-center gap-2">
          <LogoMark className="size-5" />
          {t('footer.tagline')}
        </p>
        <p>{t('footer.honesty')}</p>
      </div>
    </footer>
  );
}

export function AppShell() {
  const { state, retry } = useSession();
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      {state.status === 'unreachable' && (
        <div className="mx-auto mt-4 w-full max-w-6xl px-4 sm:px-6">
          <Alert
            kind="danger"
            title={t('errors.unreachableTitle')}
            action={
              <Button size="sm" variant="secondary" onClick={retry}>
                {t('common.retry')}
              </Button>
            }
          >
            {t('errors.unreachable')}
          </Alert>
        </div>
      )}
      <div className="flex-1">
        <Outlet />
      </div>
      <Footer />
    </div>
  );
}
