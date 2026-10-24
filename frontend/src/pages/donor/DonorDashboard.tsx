import { paths } from '../../app/paths';
import { useMyDonations, useNotifications } from '../../app/queries';
import { useSession } from '../../app/session';
import { useSeenMarker } from '../../app/unread';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { DonationCard } from '../../components/donation';
import { NotificationList } from '../../components/NotificationList';
import { t } from '../../i18n';
import { LinkButton } from '../../ui/Button';
import { Card, CardTitle } from '../../ui/Card';
import { EmptyState, Skeleton } from '../../ui/feedback';
import { Icon } from '../../ui/icons';
import { Page } from '../../ui/layout';

const RECENT_NOTIFICATIONS = 6;

export function DonorDashboard() {
  const { user } = useSession();
  const donations = useMyDonations();
  const notifications = useNotifications(true);
  const { seen } = useSeenMarker(user?.id ?? null);
  const firstName = user?.full_name.split(' ')[0] ?? '';

  return (
    <Page>
      <div className="relative mb-10 overflow-hidden rounded-card bg-brand-900 p-6 text-brand-50 shadow-lift sm:p-10">
        <div className="pointer-events-none absolute -top-24 -right-16 size-72 rounded-full bg-leaf/25 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 left-10 size-72 rounded-full bg-clay-500/20 blur-3xl" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold tracking-[0.14em] text-leaf uppercase">{t('donor.eyebrow')}</p>
            <h1 className="mt-2 text-3xl font-semibold text-surface sm:text-4xl">{t('donor.greeting', { name: firstName })}</h1>
            <p className="mt-2 max-w-lg text-brand-100">{t('donor.intro')}</p>
          </div>
          <LinkButton to={paths.newDonation} variant="inverse" size="lg" icon="plus">
            {t('donor.newDonation')}
          </LinkButton>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <h2 className="mb-4 text-xl font-semibold">{t('donor.myDonations')}</h2>
          <ApiErrorAlert error={donations.error} />
          {donations.isPending ? (
            <div className="space-y-3">
              <Skeleton />
              <Skeleton />
            </div>
          ) : donations.data && donations.data.length > 0 ? (
            <div className="space-y-3">
              {donations.data.map((d) => (
                <DonationCard key={d.id} donation={d} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon="heart"
              title={t('donor.emptyTitle')}
              action={
                <LinkButton to={paths.newDonation} icon="plus">
                  {t('donor.newDonation')}
                </LinkButton>
              }
            >
              {t('donor.emptyText')}
            </EmptyState>
          )}
        </section>

        <aside>
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
              <NotificationList items={notifications.data.slice(0, RECENT_NOTIFICATIONS)} role={user.role} seen={seen} compact />
            ) : (
              <p className="text-sm text-ink-muted">{notifications.isPending ? t('common.loading') : t('notifications.empty')}</p>
            )}
          </Card>
        </aside>
      </div>
    </Page>
  );
}
