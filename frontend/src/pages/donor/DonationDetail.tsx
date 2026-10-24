import { Link, useLocation, useParams } from 'react-router';

import { paths } from '../../app/paths';
import { useDonation, useTimeline } from '../../app/queries';
import { ActionBar } from '../../components/ActionBar';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { CategoryBadge, donationTitle, HolderCard } from '../../components/donation';
import { ImageGallery } from '../../components/images';
import { PointMap } from '../../components/maps';
import { StatusTag } from '../../components/StatusTag';
import { Timeline } from '../../components/Timeline';
import { formatDateTime, formatRelative } from '../../i18n/format';
import { t } from '../../i18n';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { Alert, LoadingBlock } from '../../ui/feedback';
import { Icon } from '../../ui/icons';
import { Page, Section } from '../../ui/layout';
import { Tag } from '../../ui/Tag';
import { vocabLabel } from '../../vocab/display';

export function DonationDetail() {
  const { id = '' } = useParams();
  const photoError = (useLocation().state as { photoError?: string | null } | null)?.photoError;
  const donation = useDonation(id);
  const timeline = useTimeline(id);

  if (donation.isPending) return <LoadingBlock label={t('common.loading')} />;
  if (donation.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={donation.error} />
      </Page>
    );
  }

  const d = donation.data;
  const openOffer = timeline.data?.offers.find((o) => o.response === null);

  return (
    <Page>
      <header className="mb-8">
        <p className="mb-4">
          <Link to={paths.donor} className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink">
            <Icon name="arrowLeft" className="size-4" />
            {t('donor.back')}
          </Link>
        </p>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <CategoryBadge category={d.category} size="lg" />
            <div>
              <h1 className="text-3xl font-semibold sm:text-4xl">{donationTitle(d)}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <StatusTag status={d.status} size="md" />
                {d.is_priority && (
                  <Tag tone="attention" icon="flag" size="md">
                    {t('donation.priority')}
                  </Tag>
                )}
              </div>
            </div>
          </div>
          <ActionBar surface="donor" id={d.id} allowed={d.allowed_actions} size="lg" />
        </div>
        {openOffer && (
          <p className="mt-4 flex items-center gap-2 text-sm text-ink-soft">
            <Icon name="clock" className="size-4" />
            {t('donation.awaitingAnswer', { org: openOffer.organization_name, when: formatRelative(openOffer.expires_at) })}
          </p>
        )}
      </header>

      <div className="space-y-6">
        {photoError !== undefined && (
          <Alert kind="warning" title={t('donation.photoFailed')}>
            {photoError ?? t('errors.generic')}
          </Alert>
        )}
        {d.escalation_cause && (
          <Alert kind="warning" title={t('donation.escalatedTitle')}>
            <p>{vocabLabel('EscalationCause', d.escalation_cause)}</p>
            <p className="mt-1">{t('donation.escalatedText')}</p>
          </Alert>
        )}
        {d.holder && <HolderCard holder={d.holder} />}

        <div className="grid gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-3">
            <CardTitle>{t('donation.details')}</CardTitle>
            <Facts
              items={[
                { label: t('fields.condition'), value: vocabLabel('Condition', d.condition) },
                { label: t('donation.quantity'), value: t('common.items', { count: d.quantity }) },
                { label: t('fields.pickupAddress'), value: d.pickup_address_text },
                {
                  label: t('fields.window'),
                  value: t('common.range', { from: formatDateTime(d.pickup_window_start), to: formatDateTime(d.pickup_window_end) }),
                },
                d.note && { label: t('donation.yourNote'), value: d.note },
                { label: t('donation.created'), value: formatDateTime(d.created_at) },
              ]}
            />
            <p className="mt-5 text-xs text-ink-muted">{t('donation.windowAdvisory')}</p>
            <div className="mt-6">
              <h3 className="mb-3 font-sans text-xs font-semibold tracking-wide text-ink-muted uppercase">{t('donation.photos')}</h3>
              <ImageGallery donationId={d.id} imageIds={d.images.map((i) => i.id)} />
            </div>
          </Card>
          <Card className="lg:col-span-2">
            <CardTitle>{t('donation.pickupPoint')}</CardTitle>
            <PointMap point={{ lat: d.pickup_latitude, lng: d.pickup_longitude }} className="h-64" />
            <p className="mt-3 text-xs text-ink-muted">{t('donation.addressPrivacy')}</p>
          </Card>
        </div>
      </div>

      <Section title={t('donation.timeline')}>
        <ApiErrorAlert error={timeline.error} />
        {timeline.data ? <Timeline timeline={timeline.data} /> : <LoadingBlock label={t('common.loading')} />}
      </Section>
    </Page>
  );
}
