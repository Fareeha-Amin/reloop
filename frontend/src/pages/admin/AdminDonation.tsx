import { useParams } from 'react-router';

import { paths } from '../../app/paths';
import { useAdminDonation } from '../../app/queries';
import { ActionBar } from '../../components/ActionBar';
import { RankingRuns } from '../../components/admin';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { CategoryBadge, donationTitle, HolderCard } from '../../components/donation';
import { ImageGallery } from '../../components/images';
import { PointMap } from '../../components/maps';
import { StatusTag } from '../../components/StatusTag';
import { Timeline } from '../../components/Timeline';
import { formatDateTime } from '../../i18n/format';
import { t } from '../../i18n';
import { Button } from '../../ui/Button';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { Alert, LoadingBlock } from '../../ui/feedback';
import { Page, PageHeader, Section } from '../../ui/layout';
import { Tag } from '../../ui/Tag';
import { vocabLabel } from '../../vocab/display';

/**
 * The full record, precise address included. Each load is recorded in the address-access
 * log, so this page never polls (app/queries: useAdminDonation); "Reload" reads again.
 */
export function AdminDonation() {
  const { id = '' } = useParams();
  const detail = useAdminDonation(id);

  if (detail.isPending) return <LoadingBlock label={t('common.loading')} />;
  if (detail.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={detail.error} />
      </Page>
    );
  }

  const { donation: d, timeline, ranking_runs: runs } = detail.data;

  return (
    <Page>
      <PageHeader
        back={{ to: paths.admin, label: t('admin.back') }}
        eyebrow={t('admin.donationEyebrow')}
        title={
          <span className="flex items-center gap-4">
            <CategoryBadge category={d.category} size="lg" />
            {donationTitle(d)}
          </span>
        }
        subtitle={
          <span className="mt-1 flex flex-wrap items-center gap-2">
            <StatusTag status={d.status} size="md" />
            {d.is_priority && (
              <Tag tone="attention" icon="flag" size="md">
                {t('donation.priority')}
              </Tag>
            )}
          </span>
        }
        actions={<ActionBar surface="admin" id={d.id} allowed={d.allowed_actions} size="lg" />}
      />

      <div className="mb-6">
        <Alert
          kind="info"
          title={t('admin.recordedTitle')}
          action={
            <Button variant="secondary" size="sm" icon="clock" busy={detail.isFetching} onClick={() => detail.refetch()}>
              {t('admin.reload')}
            </Button>
          }
        >
          {t('admin.recordedText', { at: formatDateTime(new Date(detail.dataUpdatedAt).toISOString()) })}
        </Alert>
      </div>

      <div className="space-y-6">
        {d.escalation_cause && (
          <Alert kind="warning" title={t('admin.escalated')}>
            {vocabLabel('EscalationCause', d.escalation_cause)}
          </Alert>
        )}
        {d.holder && <HolderCard holder={d.holder} title={t('admin.holder')} note={t('admin.holderNote')} />}

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
                d.note && { label: t('donation.donorNote'), value: d.note },
                { label: t('donation.created'), value: formatDateTime(d.created_at) },
                { label: t('admin.donorId'), value: <span className="font-mono text-xs">{d.donor_id}</span> },
                { label: t('admin.donationId'), value: <span className="font-mono text-xs">{d.id}</span> },
              ]}
            />
            <div className="mt-6">
              <h3 className="mb-3 font-sans text-xs font-semibold tracking-wide text-ink-muted uppercase">{t('donation.photos')}</h3>
              <ImageGallery donationId={d.id} imageIds={d.images.map((i) => i.id)} />
            </div>
          </Card>
          <Card className="lg:col-span-2">
            <CardTitle>{t('donation.pickupPoint')}</CardTitle>
            <PointMap point={{ lat: d.pickup_latitude, lng: d.pickup_longitude }} className="h-64" />
          </Card>
        </div>
      </div>

      <Section title={t('donation.timeline')}>
        <Timeline timeline={timeline} />
      </Section>

      <Section title={t('admin.rankingRuns')}>
        <Card>
          <p className="mb-4 text-sm text-ink-muted">{t('admin.rankingRunsIntro')}</p>
          <RankingRuns runs={runs} />
        </Card>
      </Section>
    </Page>
  );
}
