import { useParams } from 'react-router';

import { paths } from '../../app/paths';
import { useOffer } from '../../app/queries';
import { ActionBar } from '../../components/ActionBar';
import { ApiErrorAlert } from '../../components/ApiErrorAlert';
import { CategoryBadge, donationTitle } from '../../components/donation';
import { ImageGallery } from '../../components/images';
import { approxDistance } from '../../components/offer';
import { formatDateTime, formatRelative } from '../../i18n/format';
import { t } from '../../i18n';
import { Card, CardTitle, Facts } from '../../ui/Card';
import { Alert, LoadingBlock } from '../../ui/feedback';
import { Icon } from '../../ui/icons';
import { Page, PageHeader } from '../../ui/layout';
import { Marker, Tag } from '../../ui/Tag';
import { vocabLabel } from '../../vocab/display';

/** One offer, as the organisation sees it before deciding: no address, a rounded distance. */
export function OfferDetail() {
  const { matchId = '' } = useParams();
  const offer = useOffer(matchId);

  if (offer.isPending) return <LoadingBlock label={t('common.loading')} />;
  if (offer.error) {
    return (
      <Page width="narrow">
        <ApiErrorAlert error={offer.error} />
      </Page>
    );
  }

  const o = offer.data;
  const open = o.response === null;

  return (
    <Page>
      <PageHeader
        back={{ to: paths.acceptor, label: t('acceptor.back') }}
        eyebrow={t('offer.eyebrow')}
        title={
          <span className="flex items-center gap-4">
            <CategoryBadge category={o.category} size="lg" />
            {donationTitle(o)}
          </span>
        }
        subtitle={
          <span className="mt-1 flex flex-wrap items-center gap-2">
            {open && (
              <Tag tone="progress" icon="clock" size="md">
                {t('offer.expires', { when: formatRelative(o.expires_at) })}
              </Tag>
            )}
            {o.is_priority && (
              <Tag tone="attention" icon="flag" size="md">
                {t('donation.priority')}
              </Tag>
            )}
          </span>
        }
        actions={<ActionBar surface="offer" id={o.match_id} allowed={o.allowed_actions} size="lg" />}
      />

      {!open && o.response && (
        <div className="mb-6">
          <Alert kind="info" title={t('offer.closed', { response: vocabLabel('OfferResponse', o.response) })}>
            {o.reason_code && t('timeline.declineReason', { reason: vocabLabel('RejectReason', o.reason_code) })}
          </Alert>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardTitle>{t('donation.details')}</CardTitle>
          <Facts
            items={[
              { label: t('fields.condition'), value: vocabLabel('Condition', o.condition) },
              { label: t('donation.quantity'), value: t('common.items', { count: o.quantity }) },
              {
                label: t('fields.window'),
                value: t('common.range', { from: formatDateTime(o.pickup_window_start), to: formatDateTime(o.pickup_window_end) }),
              },
              o.note && { label: t('donation.donorNote'), value: o.note },
              { label: t('offer.offeredAt'), value: formatDateTime(o.offered_at) },
              open && { label: t('offer.expiresAt'), value: formatDateTime(o.expires_at) },
            ]}
          />
          <p className="mt-5 text-xs text-ink-muted">{t('donation.windowAdvisory')}</p>
          {open && (
            <div className="mt-6">
              <h3 className="mb-3 font-sans text-xs font-semibold tracking-wide text-ink-muted uppercase">{t('donation.photos')}</h3>
              <ImageGallery donationId={o.donation_id} imageIds={o.image_ids} />
            </div>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <CardTitle>{t('offer.whereTitle')}</CardTitle>
          <div className="flex items-center gap-3">
            <span className="grid size-12 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-700">
              <Icon name="pin" className="size-6" />
            </span>
            <div>
              <p className="text-lg font-semibold">{approxDistance(o.distance_km)}</p>
              <Marker>{t('honesty.approximate')}</Marker>
            </div>
          </div>
          <p className="mt-4 text-sm text-ink-soft">{t('offer.wherePrivacy')}</p>
        </Card>
      </div>
    </Page>
  );
}
