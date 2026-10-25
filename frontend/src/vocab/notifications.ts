/**
 * How a notification reads, where it leads and how it looks, per NotificationKind. What is
 * in the feed, and for whom, is the API's answer; this only renders it.
 */

import type { Actor, NotificationKind, NotificationOut } from '../api/schema';
import { paths, withChatOpen } from '../app/paths';
import { has, t } from '../i18n';
import { statusTone, verificationTone, vocabLabel, type Tone } from './display';
import { homeFor, ROLE } from './roles';

const KIND = {
  donationEvent: 'DONATION_EVENT',
  organisationRegistered: 'ORGANISATION_REGISTERED',
  chatMessage: 'CHAT_MESSAGE',
} as const satisfies Record<string, NotificationKind>;

const ORGANISATION_SIDE: Actor = 'ACCEPTOR';

function itemTitle(n: NotificationOut): string {
  return n.quantity !== null && n.quantity !== undefined && n.category
    ? t('donation.title', { count: n.quantity, category: vocabLabel('Category', n.category) })
    : '';
}

/** One item as a sentence: notify.<ACTION> for lifecycle events, notify.kind.<KIND> otherwise. */
export function notificationText(n: NotificationOut): string {
  const org = n.organization_name ?? t('notifications.anOrganisation');
  const params = {
    item: itemTitle(n),
    org,
    from: n.from_state ? vocabLabel('DonationStatus', n.from_state) : '',
    to: n.to_state ? vocabLabel('DonationStatus', n.to_state) : '',
    sender: n.actor === ORGANISATION_SIDE ? org : t('chat.theDonor'),
  };
  if (n.kind === KIND.donationEvent && n.action) {
    const key = `notify.${n.action}`;
    return has(key) ? t(key, params) : t('notify.generic', params);
  }
  const key = `notify.kind.${n.kind}`;
  return has(key) ? t(key, params) : t('notify.unknown');
}

/** Where an item takes this user. */
export function notificationLink(role: string, n: NotificationOut): string {
  if (n.kind === KIND.organisationRegistered && n.organization_id) return paths.adminOrganisation(n.organization_id);
  if (!n.donation_id) return homeFor(role);
  // A message opens the donation with its chat panel open.
  const chat = n.kind === KIND.chatMessage;
  switch (role) {
    case ROLE.donor:
      return chat ? withChatOpen(paths.donation(n.donation_id)) : paths.donation(n.donation_id);
    case ROLE.admin:
      return paths.adminDonation(n.donation_id);
    case ROLE.acceptor:
      // A message is about a donation the organisation accepted; events may concern
      // offers it no longer has, so they open the dashboard.
      return chat ? withChatOpen(paths.heldDonation(n.donation_id)) : homeFor(role);
    default:
      return homeFor(role);
  }
}

export function notificationTone(n: NotificationOut): Tone {
  if (n.kind === KIND.organisationRegistered) return verificationTone(n.verification_status ?? '');
  if (n.kind === KIND.chatMessage) return 'info';
  return statusTone(n.to_state ?? '');
}
