import { paths } from '../../app/paths';
import { useMyDonations } from '../../app/queries';
import { useSession } from '../../app/session';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { DonationCard } from '../../components/donation';
import { RecentActivity } from '../../components/NotificationList';
import { t } from '../../i18n';
import { LinkButton } from '../../ui/Button';
import { EmptyState, Skeleton } from '../../ui/feedback';
import { HeroBanner, Page } from '../../ui/layout';

export function DonorDashboard() {
  const { user } = useSession();
  const donations = useMyDonations();
  const firstName = user?.full_name.split(' ')[0] ?? '';

  return (
    <Page>
      <HeroBanner
        eyebrow={t('donor.eyebrow')}
        title={t('donor.greeting', { name: firstName })}
        intro={t('donor.intro')}
        actions={
          <LinkButton to={paths.newDonation} variant="inverse" size="lg" icon="plus">
            {t('donor.newDonation')}
          </LinkButton>
        }
      />

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
          <RecentActivity />
        </aside>
      </div>
    </Page>
  );
}
