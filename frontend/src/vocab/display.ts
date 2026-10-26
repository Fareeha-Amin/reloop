/**
 * THE display module for vocabulary values (non-negotiable 12).
 *
 * Status values (and the other API vocabularies' values) appear as literals only in
 * src/vocab/; tests/no-literals.test.ts enforces it. This file says how each value LOOKS:
 * a tone per status, offer response, urgency and verification status, with a neutral
 * fallback for any value the API adds before this file does. What each value MEANS, and
 * what may happen next, comes from the API (allowed_actions, editable, ...), never from
 * here. Labels live in the locale file under vocab.<Vocabulary>.<VALUE>.
 */

import type {
  BookingStatus,
  Category,
  CommissionSource,
  ComponentOut,
  DonationStatus,
  OfferResponse,
  Urgency,
  VerificationStatus,
} from '../api/schema';
import { formatNumber, formatPercent } from '../i18n/format';
import { has, t } from '../i18n';
import type { IconName } from '../ui/icons';

export type Tone =
  | 'neutral'
  | 'info'
  | 'progress'
  | 'attention'
  | 'active'
  | 'reuse'
  | 'recovery'
  | 'recovered'
  | 'danger'
  | 'muted';

const STATUS_TONES: Record<DonationStatus, Tone> = {
  LISTED: 'info',
  MATCHED: 'progress',
  RE_MATCHING: 'progress',
  ESCALATED: 'attention',
  ACCEPTED: 'active',
  PICKUP_SCHEDULED: 'active',
  IN_TRANSIT: 'active',
  COMPLETED: 'reuse',
  WASTE_REDIRECTED: 'recovery',
  RECYCLED: 'recovered',
  NEEDS_ADMIN: 'danger',
  CANCELLED: 'muted',
};

const OFFER_RESPONSE_TONES: Record<OfferResponse, Tone> = {
  ACCEPTED: 'active',
  REJECTED: 'danger',
  EXPIRED: 'attention',
  RETRACTED: 'muted',
};

const URGENCY_TONES: Record<Urgency, Tone> = {
  LOW: 'neutral',
  MEDIUM: 'attention',
  HIGH: 'danger',
};

const VERIFICATION_TONES: Record<VerificationStatus, Tone> = {
  PENDING: 'attention',
  VERIFIED: 'active',
  REJECTED: 'danger',
};

const BOOKING_STATUS_TONES: Record<BookingStatus, Tone> = {
  BOOKED: 'progress',
  PICKED_UP: 'active',
  DELIVERED: 'reuse',
  CANCELLED: 'muted',
};

const COMMISSION_SOURCE_TONES: Record<CommissionSource, Tone> = {
  LOGISTICS: 'active',
  RECYCLING: 'recovery',
};

const CATEGORY_ICONS: Record<Category, IconName> = {
  CLOTHES: 'shirt',
  TOYS: 'toy',
  BOOKS: 'book',
};

function pick<K extends string, V>(map: Record<K, V>, value: string, fallback: V): V {
  return (map as Record<string, V>)[value] ?? fallback;
}

export const statusTone = (status: string): Tone => pick(STATUS_TONES, status, 'neutral');
export const offerResponseTone = (response: string): Tone => pick(OFFER_RESPONSE_TONES, response, 'neutral');
export const urgencyTone = (urgency: string): Tone => pick(URGENCY_TONES, urgency, 'neutral');
export const verificationTone = (status: string): Tone => pick(VERIFICATION_TONES, status, 'neutral');
export const bookingStatusTone = (status: string): Tone => pick(BOOKING_STATUS_TONES, status, 'neutral');
export const commissionSourceTone = (source: string): Tone => pick(COMMISSION_SOURCE_TONES, source, 'neutral');
export const categoryIcon = (category: string): IconName => pick(CATEGORY_ICONS, category, 'box');

/** The API vocabularies with labels in the locale file (vocab.<name>.<VALUE>). */
export type VocabName =
  | 'Actor'
  | 'BookingStatus'
  | 'Category'
  | 'ChatClosure'
  | 'CommissionSource'
  | 'Condition'
  | 'DonationAction'
  | 'DonationStatus'
  | 'EscalationCause'
  | 'FilterReason'
  | 'HandoverMode'
  | 'NotificationKind'
  | 'OfferResponse'
  | 'OfferSource'
  | 'PaymentStatus'
  | 'RankingTrigger'
  | 'RejectReason'
  | 'Role'
  | 'ScoreFactor'
  | 'Urgency'
  | 'VerificationStatus'
  | 'WalletTxnType';

/** A value's label, or the raw value for one this app version has no label for. */
export function vocabLabel(name: VocabName, value: string): string {
  const key = `vocab.${name}.${value}`;
  return has(key) ? t(key) : value;
}

/**
 * One score component as a reason a donor can read, e.g. "2.1 km away". The API's
 * `raw` is the underlying fact; its meaning depends on the factor (schema: ComponentOut).
 */
export function factorReason(component: ComponentOut): string {
  const { factor, raw } = component;
  switch (factor) {
    case 'PROXIMITY':
      return t('score.reason.proximity', { km: formatNumber(raw ?? 0) });
    case 'NEED_MATCH':
      return raw === null ? t('score.reason.noNeed') : t('score.reason.need', { count: Number(raw) });
    case 'URGENCY':
      return raw === null
        ? t('score.reason.noUrgency')
        : t('score.reason.urgency', { urgency: vocabLabel('Urgency', String(raw)) });
    case 'CAPACITY_HEADROOM':
      return t('score.reason.capacity', { count: Number(raw ?? 0) });
    case 'ACCEPTANCE_RATE':
      return raw === null ? t('score.reason.noHistory') : t('score.reason.acceptance', { pct: formatPercent(raw) });
    default:
      return vocabLabel('ScoreFactor', factor);
  }
}
