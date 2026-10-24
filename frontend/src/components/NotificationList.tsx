import { Link } from 'react-router';

import type { NotificationOut } from '../api/schema';
import { formatRelative } from '../i18n/format';
import { has, t } from '../i18n';
import { ToneDot } from '../ui/Tag';
import { statusTone, vocabLabel } from '../vocab/display';
import { notificationLink } from '../vocab/roles';
import { donationTitle } from './donation';

/** One event as a sentence: notify.<ACTION> in the locale file, or a generic fallback. */
export function notificationText(n: NotificationOut): string {
  const params = {
    item: donationTitle(n),
    org: n.organization_name ?? t('notifications.anOrganisation'),
    from: vocabLabel('DonationStatus', n.from_state),
    to: vocabLabel('DonationStatus', n.to_state),
  };
  const key = `notify.${n.action}`;
  return has(key) ? t(key, params) : t('notify.generic', params);
}

export function NotificationList({
  items,
  role,
  seen,
  compact = false,
}: {
  items: NotificationOut[];
  role: string;
  seen: number;
  compact?: boolean;
}) {
  return (
    <ul className="divide-y divide-line">
      {items.map((n) => {
        const unread = n.id > seen;
        return (
          <li key={n.id}>
            <Link
              to={notificationLink(role, n.donation_id)}
              className={`flex gap-3 rounded-control px-3 transition hover:bg-surface-muted ${compact ? 'py-2.5' : 'py-3.5'}`}
            >
              <ToneDot tone={statusTone(n.to_state)} className="mt-1.5 size-2.5" />
              <div className="min-w-0 flex-1">
                <p className={`text-sm ${unread ? 'font-semibold text-ink' : 'text-ink-soft'}`}>{notificationText(n)}</p>
                <p className="mt-0.5 text-xs text-ink-muted">
                  {formatRelative(n.at)}
                  {n.cause && ` · ${vocabLabel('EscalationCause', n.cause)}`}
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
