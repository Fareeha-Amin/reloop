import type { AcceptedDonationOut, OfferOut } from '../api/schema';
import { paths } from '../app/paths';
import { formatDateTime, formatNumber, formatRelative } from '../i18n/format';
import { t } from '../i18n';
import { LinkCard } from '../ui/Card';
import { Icon } from '../ui/icons';
import { Tag } from '../ui/Tag';
import { vocabLabel } from '../vocab/display';
import { UnreadMessagesTag } from './chat';
import { CategoryBadge, donationTitle } from './donation';
import { StatusTag } from './StatusTag';

/** "About 2.5 km away": the acceptor sees only a rounded distance before accepting. */
export function approxDistance(km: number): string {
  return t('offer.about', { km: formatNumber(km) });
}

/** An open offer in the acceptor's inbox. */
export function OfferCard({ offer }: { offer: OfferOut }) {
  return (
    <LinkCard to={paths.offer(offer.match_id)}>
      <div className="flex items-start gap-4">
        <CategoryBadge category={offer.category} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="truncate font-sans text-base font-semibold">{donationTitle(offer)}</h3>
            <Tag tone="progress" icon="clock">
              {t('offer.expires', { when: formatRelative(offer.expires_at) })}
            </Tag>
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            {vocabLabel('Condition', offer.condition)} · {approxDistance(offer.distance_km)}
          </p>
          <p className="mt-0.5 text-sm text-ink-muted">
            {t('offer.window', { from: formatDateTime(offer.pickup_window_start), to: formatDateTime(offer.pickup_window_end) })}
          </p>
          {offer.is_priority && (
            <div className="mt-3">
              <Tag tone="attention" icon="flag">
                {t('donation.priority')}
              </Tag>
            </div>
          )}
        </div>
      </div>
    </LinkCard>
  );
}

/** A donation the organisation accepted. */
export function HeldCard({ held }: { held: AcceptedDonationOut }) {
  return (
    <LinkCard to={paths.heldDonation(held.donation_id)}>
      <div className="flex items-start gap-4">
        <CategoryBadge category={held.category} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="truncate font-sans text-base font-semibold">{donationTitle(held)}</h3>
            <StatusTag status={held.status} />
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            {vocabLabel('Condition', held.condition)} · {approxDistance(held.distance_km)}
          </p>
          {held.handover && (
            <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-soft">
              <Icon name="truck" className="size-4" />
              {t('timeline.handover', {
                mode: vocabLabel('HandoverMode', held.handover.mode),
                at: formatDateTime(held.handover.scheduled_for),
              })}
            </p>
          )}
          {(held.allowed_actions.length > 0 || (held.chat?.unread ?? 0) > 0) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {held.allowed_actions.length > 0 && (
                <Tag tone="attention" icon="alert">
                  {t('held.yourMove')}
                </Tag>
              )}
              <UnreadMessagesTag summary={held.chat} />
            </div>
          )}
        </div>
      </div>
    </LinkCard>
  );
}
