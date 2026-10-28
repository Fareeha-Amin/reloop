import { useParams } from 'react-router';

import { paths } from '../../app/paths';
import { useHeldDonation } from '../../app/queries';
import { ActionBar } from '../../components/ActionBar';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { ChatButton } from '../../components/chat';
import { CategoryBadge, donationTitle } from '../../components/donation';
import { ImageGallery } from '../../components/images';
import { PointMap } from '../../components/maps';
import { StatusTag } from '../../components/StatusTag';
import { formatDateTime } from '../../i18n/format';
import { t } from '../../i18n';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { Alert, LoadingBlock } from '../../ui/feedback';
import { Page, PageHeader } from '../../ui/layout';
import { Tag } from '../../ui/Tag';
import { vocabLabel } from '../../vocab/display';

/** A donation the organisation accepted: the released address, the handover, and what to do next. */
export function HeldDonation() {
  const { id = '' } = useParams();
  const held = useHeldDonation(id);

  if (held.isPending) return <LoadingBlock label={t('common.loading')} />;
  if (held.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={held.error} />
      </Page>
    );
  }

  const d = held.data;
  const released = d.address_released && d.pickup_address_text !== null && d.pickup_latitude !== null && d.pickup_longitude !== null;

  return (
    <Page>
      <PageHeader
        back={{ to: paths.acceptor, label: t('acceptor.back') }}
        eyebrow={t('held.eyebrow')}
        title={
          <span className="flex items-center gap-4">
            <CategoryBadge category={d.category} size="lg" />
            {donationTitle(d)}
          </span>
        }
        subtitle={
          <span className="mt-1 inline-block">
            <StatusTag status={d.status} size="md" />
          </span>
        }
        actions={
          <>
            {d.chat && <ChatButton donationId={d.donation_id} summary={d.chat} audience="organisation" about={donationTitle(d)} size="lg" />}
            <ActionBar surface="held" id={d.donation_id} allowed={d.allowed_actions} size="lg" />
          </>
        }
      />

      <div className="space-y-6">
        {d.awaiting_donor_handover_choice && (
          <Alert kind="info" title={t('held.awaitingChoiceTitle')}>
            {t('held.awaitingChoiceText')}
          </Alert>
        )}
        {released ? (
          <Card>
            <CardTitle aside={<Tag tone="active" icon="check">{t('held.released')}</Tag>}>{t('held.addressTitle')}</CardTitle>
            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-4">
                <Facts
                  items={[
                    { label: t('holder.address'), value: d.pickup_address_text },
                    {
                      label: t('fields.window'),
                      value: t('common.range', { from: formatDateTime(d.pickup_window_start), to: formatDateTime(d.pickup_window_end) }),
                    },
                    d.handover && {
                      label: vocabLabel('HandoverMode', d.handover.mode),
                      value: formatDateTime(d.handover.scheduled_for),
                    },
                  ]}
                />
                <p className="text-xs text-ink-muted">{t('held.privacy')}</p>
              </div>
              <PointMap point={{ lat: d.pickup_latitude!, lng: d.pickup_longitude! }} />
            </div>
          </Card>
        ) : (
          <Alert kind="info" title={t('held.notHeldTitle')}>
            {t('held.notHeldText')}
          </Alert>
        )}

        <Card>
          <CardTitle>{t('donation.details')}</CardTitle>
          <Facts
            items={[
              { label: t('fields.condition'), value: vocabLabel('Condition', d.condition) },
              { label: t('donation.quantity'), value: t('common.items', { count: d.quantity }) },
              d.note && { label: t('donation.donorNote'), value: d.note },
              !released && d.handover && {
                label: vocabLabel('HandoverMode', d.handover.mode),
                value: formatDateTime(d.handover.scheduled_for),
              },
            ]}
          />
          {released && (
            <div className="mt-6">
              <h3 className="mb-3 font-sans text-xs font-semibold tracking-wide text-ink-muted uppercase">{t('donation.photos')}</h3>
              <ImageGallery donationId={d.donation_id} imageIds={d.image_ids} />
            </div>
          )}
        </Card>
      </div>
    </Page>
  );
}
