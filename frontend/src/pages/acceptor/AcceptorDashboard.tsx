import type { OrganizationOut } from '../../api/schema';
import { useHeldDonations, useMyOrganisation, useOffers } from '../../app/queries';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { NeedsCard } from '../../components/needs';
import { RecentActivity } from '../../components/NotificationList';
import { HeldCard, OfferCard } from '../../components/offer';
import { VerificationTag } from '../../components/StatusTag';
import { has, t } from '../../i18n';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { EmptyState, LoadingBlock, Skeleton } from '../../ui/feedback';
import { Icon } from '../../ui/icons';
import { HeroBanner, Page, Section } from '../../ui/layout';
import { vocabLabel } from '../../vocab/display';

function Stat({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="rounded-control bg-brand-50/10 px-4 py-2.5 ring-1 ring-brand-50/15">
      <p className="font-display text-2xl font-semibold text-surface">{value}</p>
      <p className="text-xs text-brand-100">{label}</p>
    </div>
  );
}

function ProfileCard({ org }: { org: OrganizationOut }) {
  return (
    <Card>
      <CardTitle>{t('acceptor.profile')}</CardTitle>
      <Facts
        items={[
          { label: t('holder.address'), value: org.address_text },
          { label: t('holder.contact'), value: org.contact_person },
          { label: t('holder.phone'), value: org.phone },
          { label: t('acceptor.capacity'), value: t('common.items', { count: org.storage_capacity }) },
          { label: t('fields.categoriesAccepted'), value: org.categories_accepted.map((c) => vocabLabel('Category', c)).join(', ') },
          { label: t('acceptor.handover'), value: org.pickup_capable ? t('candidates.collects') : t('candidates.dropoffOnly') },
        ]}
      />
    </Card>
  );
}

export function AcceptorDashboard() {
  const org = useMyOrganisation();
  const offers = useOffers();
  const held = useHeldDonations();

  if (org.isPending) return <LoadingBlock label={t('common.loading')} />;
  if (org.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={org.error} />
      </Page>
    );
  }

  const o = org.data;
  // Held now (the address is released to us) versus earlier acceptances.
  const current = held.data?.filter((d) => d.address_released) ?? [];
  const earlier = held.data?.filter((d) => !d.address_released) ?? [];
  const verificationKey = `acceptor.verification.${o.verification_status}`;

  return (
    <Page>
      <HeroBanner
        eyebrow={t('acceptor.eyebrow')}
        title={o.name}
        intro={
          <>
            <span className="mb-2 inline-block">
              <VerificationTag status={o.verification_status} />
            </span>
            {has(verificationKey) && <p>{t(verificationKey)}</p>}
            {o.verification_note && <p className="mt-1 text-sm italic">{t('acceptor.verificationNote', { note: o.verification_note })}</p>}
          </>
        }
        actions={
          <div className="flex gap-2">
            <Stat value={offers.data?.length ?? '–'} label={t('acceptor.statOffers')} />
            <Stat value={held.data ? current.length : '–'} label={t('acceptor.statReceiving')} />
          </div>
        }
      />

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <section>
            <h2 className="mb-1 text-xl font-semibold">{t('acceptor.offersTitle')}</h2>
            <p className="mb-4 text-sm text-ink-muted">{t('acceptor.offersIntro')}</p>
            <ApiErrorAlert error={offers.error} />
            {offers.isPending ? (
              <Skeleton />
            ) : offers.data && offers.data.length > 0 ? (
              <div className="space-y-3">
                {offers.data.map((offer) => (
                  <OfferCard key={offer.match_id} offer={offer} />
                ))}
              </div>
            ) : (
              <EmptyState icon="hands" title={t('acceptor.noOffersTitle')}>
                {t('acceptor.noOffersText')}
              </EmptyState>
            )}
          </section>

          <Section title={t('acceptor.receivingTitle')}>
            <ApiErrorAlert error={held.error} />
            {held.isPending ? (
              <Skeleton />
            ) : current.length > 0 ? (
              <div className="space-y-3">
                {current.map((d) => (
                  <HeldCard key={d.donation_id} held={d} />
                ))}
              </div>
            ) : (
              <p className="rounded-card border border-dashed border-line-strong px-5 py-6 text-sm text-ink-muted">
                {t('acceptor.noReceiving')}
              </p>
            )}
            {earlier.length > 0 && (
              <details className="group mt-6">
                <summary className="flex cursor-pointer list-none items-center gap-1.5 text-sm font-semibold text-ink-muted">
                  <Icon name="chevronRight" className="size-4 transition group-open:rotate-90" />
                  {t('acceptor.earlier', { count: earlier.length })}
                </summary>
                <div className="mt-3 space-y-3">
                  {earlier.map((d) => (
                    <HeldCard key={d.donation_id} held={d} />
                  ))}
                </div>
              </details>
            )}
          </Section>
        </div>

        <aside className="space-y-6">
          <NeedsCard categories={o.categories_accepted} />
          <RecentActivity />
          <ProfileCard org={o} />
        </aside>
      </div>
    </Page>
  );
}
