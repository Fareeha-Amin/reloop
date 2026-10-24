import { useEffect } from 'react';

import { useNotifications } from '../app/queries';
import { useSession } from '../app/session';
import { useSeenMarker } from '../app/unread';
import { ApiErrorAlert } from '../components/ApiErrorAlert';
import { NotificationList } from '../components/NotificationList';
import { POLL_MS } from '../config';
import { t } from '../i18n';
import { Card } from '../ui/Card';
import { EmptyState, LoadingBlock } from '../ui/feedback';
import { Page, PageHeader } from '../ui/layout';

export function Notifications() {
  const { user } = useSession();
  const feed = useNotifications(true);
  const { seen, markSeen } = useSeenMarker(user?.id ?? null);
  // Mark everything shown as seen after a moment, so new items are visible as new first.
  const newest = feed.data?.[0]?.id;

  useEffect(() => {
    if (newest === undefined) return;
    const timer = window.setTimeout(() => markSeen(newest), 1500);
    return () => window.clearTimeout(timer);
  }, [newest, markSeen]);

  return (
    <Page width="narrow">
      <PageHeader eyebrow={t('notifications.eyebrow')} title={t('notifications.title')} subtitle={t('notifications.subtitle', { seconds: POLL_MS.notifications / 1000 })} />
      <ApiErrorAlert error={feed.error} />
      {feed.isPending ? (
        <LoadingBlock label={t('common.loading')} />
      ) : feed.data && feed.data.length > 0 && user ? (
        <Card padded={false} className="p-2">
          <NotificationList items={feed.data} role={user.role} seen={seen} />
        </Card>
      ) : (
        <EmptyState icon="bell" title={t('notifications.empty')}>
          {t('notifications.emptyText')}
        </EmptyState>
      )}
    </Page>
  );
}
