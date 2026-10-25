import { useNotifications } from '../app/queries';
import { useSession } from '../app/session';
import { useReadState } from '../app/unread';
import { ApiErrorAlert } from '../components/ApiErrorAlert';
import { NotificationList } from '../components/NotificationList';
import { POLL_MS } from '../config';
import { t } from '../i18n';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { EmptyState, LoadingBlock } from '../ui/feedback';
import { Page, PageHeader } from '../ui/layout';

export function Notifications() {
  const { user } = useSession();
  const feed = useNotifications(true);
  const { isRead, unreadCount, markRead, markAllRead } = useReadState(user?.id ?? null);
  const items = feed.data ?? [];
  const unread = unreadCount(items);

  return (
    <Page width="narrow">
      <PageHeader
        eyebrow={t('notifications.eyebrow')}
        title={t('notifications.title')}
        subtitle={t('notifications.subtitle', { seconds: POLL_MS.notifications / 1000 })}
        actions={
          <Button variant="secondary" size="sm" icon="check" disabled={unread === 0} onClick={() => markAllRead(items)}>
            {t('notifications.markAllRead')}
          </Button>
        }
      />
      <ApiErrorAlert error={feed.error} />
      {feed.isPending ? (
        <LoadingBlock label={t('common.loading')} />
      ) : items.length > 0 && user ? (
        <>
          <p className="mb-3 text-sm text-ink-muted">
            {unread > 0 ? t('notifications.unreadCount', { count: unread }) : t('notifications.allRead')}
          </p>
          <Card padded={false} className="p-2">
            <NotificationList items={items} role={user.role} isRead={isRead} onOpen={(n) => markRead(n)} />
          </Card>
        </>
      ) : (
        <EmptyState icon="bell" title={t('notifications.empty')}>
          {t('notifications.emptyText')}
        </EmptyState>
      )}
    </Page>
  );
}
