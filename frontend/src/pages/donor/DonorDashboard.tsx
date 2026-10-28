import { paths } from '../../app/paths';
import { useImpact, useMyDonations, useWallet } from '../../app/queries';
import { useSession } from '../../app/session';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { DonationCard } from '../../components/donation';
import { ImpactCard } from '../../components/impact';
import { RecentActivity } from '../../components/NotificationList';
import { formatMoney } from '../../i18n/format';
import { t } from '../../i18n';
import { LinkButton } from '../../ui/Button';
import { LinkCard } from '../../ui/Card';
import { EmptyState, Skeleton } from '../../ui/feedback';
import { Icon } from '../../ui/icons';
import { HeroBanner, Page } from '../../ui/layout';

export function DonorDashboard() {
  const { user } = useSession();
  const donations = useMyDonations();
  const wallet = useWallet();
  const impact = useImpact();
  const firstName = user?.full_name.split(' ')[0] ?? '';

  return (
    <Page>
      {impact.data && (
        <div className="mb-8">
          <ImpactCard totals={impact.data} title={t('impact.donorTitle')} />
        </div>
      )}

      <HeroBanner
        eyebrow={t('donor.eyebrow')}
        title={t('donor.greeting', { name: firstName })}
        intro={t('donor.intro')}
        actions={
          <div className="flex flex-wrap gap-2">
            <LinkButton to={paths.newDonation} variant="inverse" size="lg" icon="plus">
              {t('donor.newDonation')}
            </LinkButton>
            <LinkButton to={paths.sendToRecycling} variant="outlineInverse" size="lg" icon="recycle">
              {t('donor.sendToRecycling')}
            </LinkButton>
          </div>
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

        <aside className="space-y-6">
          {wallet.data && (
            <LinkCard to={paths.wallet} className="p-4">
              <div className="flex items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-control bg-brand-50 text-brand-700">
                  <Icon name="wallet" />
                </span>
                <div className="min-w-0">
                  <p className="font-semibold">{t('donor.walletLink')}</p>
                  <p className="text-sm text-ink-muted">{t('donor.walletLinkBalance', { amount: formatMoney(wallet.data.balance, wallet.data.currency) })}</p>
                </div>
              </div>
            </LinkCard>
          )}
          <RecentActivity />
        </aside>
      </div>
    </Page>
  );
}
