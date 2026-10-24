import type { EventOut, OfferHistoryOut, RecyclingOut, TimelineOut } from '../api/schema';
import { formatDateTime, formatMoney, formatNumber, formatRelative } from '../i18n/format';
import { t } from '../i18n';
import { Card, CardTitle, Facts } from '../ui/Card';
import { Icon } from '../ui/icons';
import { Marker, Tag, ToneDot } from '../ui/Tag';
import { statusTone, vocabLabel } from '../vocab/display';
import { OfferResponseTag, StatusTag } from './StatusTag';

function EventRow({ event, last }: { event: EventOut; last: boolean }) {
  return (
    <li className="relative flex gap-4 pb-6">
      {!last && <span className="absolute top-4 left-[7px] h-full w-0.5 bg-line" aria-hidden="true" />}
      <ToneDot tone={statusTone(event.to_state)} className="relative mt-1.5 size-4 ring-4 ring-surface" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{vocabLabel('DonationAction', event.action)}</span>
          <Icon name="arrowRight" className="size-3.5 text-ink-muted" />
          <StatusTag status={event.to_state} />
        </div>
        <p className="mt-1 text-sm text-ink-muted">
          {t('timeline.byAt', { actor: vocabLabel('Actor', event.actor), at: formatDateTime(event.at) })}
        </p>
        {event.cause && <p className="mt-1 text-sm text-ink-soft">{vocabLabel('EscalationCause', event.cause)}</p>}
        {event.reason && (
          <p className="mt-1 rounded-control bg-surface-muted px-3 py-2 text-sm text-ink-soft">
            {t('timeline.reason', { reason: event.reason })}
          </p>
        )}
      </div>
    </li>
  );
}

function OfferRow({ offer }: { offer: OfferHistoryOut }) {
  return (
    <li className="rounded-control border border-line bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold">{offer.organization_name}</p>
          <p className="text-sm text-ink-muted">
            {t('timeline.offerMeta', {
              rank: offer.rank,
              source: vocabLabel('OfferSource', offer.offered_by),
              at: formatDateTime(offer.offered_at),
            })}
          </p>
        </div>
        {offer.response ? (
          <OfferResponseTag response={offer.response} />
        ) : (
          <Tag tone="progress" dot>
            {t('timeline.awaiting')}
          </Tag>
        )}
      </div>
      <div className="mt-2 space-y-1 text-sm text-ink-soft">
        {offer.response === null && <p>{t('timeline.expires', { when: formatRelative(offer.expires_at) })}</p>}
        {offer.reason_code && <p>{t('timeline.declineReason', { reason: vocabLabel('RejectReason', offer.reason_code) })}</p>}
        {offer.note && <p className="italic">{t('timeline.note', { note: offer.note })}</p>}
        {offer.handover && (
          <p className="flex items-center gap-1.5">
            <Icon name="truck" className="size-4" />
            {t('timeline.handover', {
              mode: vocabLabel('HandoverMode', offer.handover.mode),
              at: formatDateTime(offer.handover.scheduled_for),
            })}
          </p>
        )}
      </div>
    </li>
  );
}

/** Recycling, labelled exactly as the API labels it: simulated, estimated, placeholder. */
export function RecyclingCard({ recycling }: { recycling: RecyclingOut }) {
  const s = recycling.settlement;
  const money = (v: string) => formatMoney(v, recycling.currency);
  return (
    <div className="rounded-control border border-line bg-surface p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Icon name="recycle" className="size-5 text-clay-500" />
        <p className="font-semibold">{recycling.collector_name}</p>
        {recycling.simulated && <Marker>{t('honesty.simulated')}</Marker>}
        {recycling.mass_is_estimate && <Marker>{t('honesty.estimatedMass')}</Marker>}
        {recycling.weights_are_placeholders && <Marker icon="alert">{t('honesty.placeholderWeights')}</Marker>}
      </div>
      <Facts
        items={[
          { label: t('recycling.distance'), value: t('common.km', { km: formatNumber(recycling.distance_km) }) },
          { label: t('recycling.rate'), value: t('recycling.perKg', { amount: money(recycling.rate_per_kg) }) },
          { label: t('recycling.assigned'), value: formatDateTime(recycling.assigned_at) },
          s && { label: t('recycling.mass'), value: t('recycling.massValue', { kg: formatNumber(s.estimated_mass_kg), per: formatNumber(s.weight_per_item_kg) }) },
          s && { label: t('recycling.gross'), value: money(s.gross_value) },
          s && { label: t('recycling.fee'), value: t('recycling.feeValue', { amount: money(s.platform_fee), pct: formatNumber(s.platform_fee_pct) }) },
          s && { label: t('recycling.credit'), value: <span className="font-semibold text-brand-700">{money(s.donor_credit)}</span> },
          !s && { label: t('recycling.settlement'), value: t('recycling.awaitingConfirmation') },
        ]}
      />
      {recycling.simulated && <p className="mt-3 text-xs text-ink-muted">{t('recycling.simulatedNote')}</p>}
    </div>
  );
}

export function Timeline({ timeline }: { timeline: TimelineOut }) {
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <Card className="lg:col-span-3">
        <CardTitle>{t('timeline.history')}</CardTitle>
        {timeline.events.length === 0 ? (
          <p className="text-sm text-ink-muted">{t('timeline.noEvents')}</p>
        ) : (
          <ol>
            {[...timeline.events].reverse().map((event, index, all) => (
              <EventRow key={`${event.at}-${index}`} event={event} last={index === all.length - 1} />
            ))}
          </ol>
        )}
      </Card>
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <CardTitle>{t('timeline.offers')}</CardTitle>
          {timeline.offers.length === 0 ? (
            <p className="text-sm text-ink-muted">{t('timeline.noOffers')}</p>
          ) : (
            <ul className="space-y-3">
              {[...timeline.offers].reverse().map((offer) => (
                <OfferRow key={offer.match_id} offer={offer} />
              ))}
            </ul>
          )}
        </Card>
        {timeline.recyclings.length > 0 && (
          <Card>
            <CardTitle>{t('timeline.recycling')}</CardTitle>
            <div className="space-y-3">
              {timeline.recyclings.map((r) => (
                <RecyclingCard key={`${r.collector_id}-${r.assigned_at}`} recycling={r} />
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
