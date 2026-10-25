import { Link } from 'react-router';

import type { NotificationOut } from '../api/schema';
import { paths } from '../app/paths';
import { useNotifications } from '../app/queries';
import { useSession } from '../app/session';
import { useReadState } from '../app/unread';
import { formatRelative } from '../i18n/format';
import { t } from '../i18n';
import { LinkButton } from '../ui/Button';
import { Card, CardTitle } from '../ui/Card';
import { Icon } from '../ui/icons';
import { ToneDot } from '../ui/Tag';
import { vocabLabel } from '../vocab/display';
import { notificationLink, notificationText, notificationTone } from '../vocab/notifications';
import { VerificationTag } from './StatusTag';

/** The feed. Opening an item marks that item read, and only that one. */
export function NotificationList({
  items,
  role,
  isRead,
  onOpen,
  compact = false,
}: {
  items: NotificationOut[];
  role: string;
  isRead: (n: NotificationOut) => boolean;
  onOpen: (n: NotificationOut) => void;
  compact?: boolean;
}) {
  return (
    <ul className="divide-y divide-line">
      {items.map((n) => {
        const unread = !isRead(n);
        return (
          <li key={n.key}>
            <Link
              to={notificationLink(role, n)}
              onClick={() => onOpen(n)}
              className={`flex gap-3 rounded-control px-3 transition hover:bg-surface-muted ${compact ? 'py-2.5' : 'py-3.5'}`}
            >
              <ToneDot tone={notificationTone(n)} className="mt-1.5 size-2.5" />
              <div className="min-w-0 flex-1">
                <p className={`text-sm ${unread ? 'font-semibold text-ink' : 'text-ink-soft'}`}>{notificationText(n)}</p>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-muted">
                  {formatRelative(n.at)}
                  {n.cause && <span>· {vocabLabel('EscalationCause', n.cause)}</span>}
                  {n.verification_status && !compact && <VerificationTag status={n.verification_status} />}
                </p>
              </div>
              {unread && <span className="mt-2 size-2 shrink-0 rounded-full bg-clay-500" aria-label={t('notifications.unread')} />}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

const RECENT_NOTIFICATIONS = 6;

/** The latest few notifications, for a dashboard's side column. */
export function RecentActivity() {
  const { user } = useSession();
  const notifications = useNotifications(true);
  const { isRead, markRead } = useReadState(user?.id ?? null);
  return (
    <Card>
      <CardTitle
        aside={
          <LinkButton to={paths.notifications} variant="ghost" size="sm" iconAfter="arrowRight">
            {t('common.seeAll')}
          </LinkButton>
        }
      >
        <span className="flex items-center gap-2">
          <Icon name="bell" className="size-5 text-brand-600" />
          {t('notifications.recent')}
        </span>
      </CardTitle>
      {notifications.data && notifications.data.length > 0 && user ? (
        <NotificationList
          items={notifications.data.slice(0, RECENT_NOTIFICATIONS)}
          role={user.role}
          isRead={isRead}
          onOpen={(n) => markRead(n)}
          compact
        />
      ) : (
        <p className="text-sm text-ink-muted">{notifications.isPending ? t('common.loading') : t('notifications.empty')}</p>
      )}
    </Card>
  );
}
