/**
 * How to perform each lifecycle action from a page. This is transport, not rules:
 * WHICH actions a viewer may take is decided by the API (allowed_actions) and rendered
 * as-is by components/ActionBar. This file only knows, for an action the API offers,
 * which endpoint to call and what input that endpoint takes.
 *
 * The same action can be reached from different places (a donor's CANCEL and an admin's
 * CANCEL are different endpoints), so specs are grouped by surface:
 *   donor  - a donor's own donation (id: donation id)
 *   offer  - an acceptor's open offer (id: match id)
 *   held   - a donation the acceptor holds (id: donation id)
 *   admin  - an admin on any donation (id: donation id)
 */

import type { AcceptedDonationOut, DonationAction, RejectReason } from '../api/schema';
import { unwrap } from '../api/errors';
import { client } from '../app/api';
import { paths } from '../app/paths';

export type Surface = 'donor' | 'offer' | 'held' | 'admin';

/** What the user is asked for before the call. */
export type ActionInput =
  | 'confirm' // a yes/no confirmation
  | 'datetime' // a future handover time
  | 'reason' // an admin's recorded reason
  | 'reject' // a reject reason code and optional note
  | 'navigate'; // no call: the action continues on another page

export type Emphasis = 'primary' | 'secondary' | 'danger';

export interface ActionPayload {
  scheduledFor?: string;
  reason?: string;
  reasonCode?: RejectReason;
  note?: string;
}

export interface ActionSpec {
  input: ActionInput;
  emphasis: Emphasis;
  labelKey: string;
  /** Explains what will happen, shown in the confirmation dialog. */
  confirmKey?: string;
  run?: (id: string, payload: ActionPayload) => Promise<unknown>;
  to?: (id: string) => string;
  /** The page to show once the call succeeds, if not the current one. */
  next?: (id: string, result: unknown) => string;
}

const donation = (id: string) => ({ params: { path: { donation_id: id } } });
const match = (id: string) => ({ params: { path: { match_id: id } } });

const SPECS: Record<Surface, Partial<Record<DonationAction, ActionSpec>>> = {
  donor: {
    OFFER: {
      input: 'navigate',
      emphasis: 'primary',
      labelKey: 'actions.offer.label',
      to: paths.candidates,
    },
    REMATCH: {
      input: 'confirm',
      emphasis: 'primary',
      labelKey: 'actions.rematch.label',
      confirmKey: 'actions.rematch.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/rematch', donation(id))),
    },
    UPGRADE_PRIORITY: {
      input: 'confirm',
      emphasis: 'secondary',
      labelKey: 'actions.upgradePriority.label',
      confirmKey: 'actions.upgradePriority.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/upgrade-priority', donation(id))),
    },
    REDIRECT_TO_RECYCLING: {
      input: 'confirm',
      emphasis: 'secondary',
      labelKey: 'actions.recycle.label',
      confirmKey: 'actions.recycle.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/redirect-to-recycling', donation(id))),
    },
    DELIVER_TO_RECYCLER: {
      input: 'confirm',
      emphasis: 'primary',
      labelKey: 'actions.deliverToRecycler.label',
      confirmKey: 'actions.deliverToRecycler.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/deliver-to-recycler', donation(id))),
    },
    MARK_RECYCLER_HANDED_OVER: {
      input: 'confirm',
      emphasis: 'primary',
      labelKey: 'actions.recyclerHandedOver.label',
      confirmKey: 'actions.recyclerHandedOver.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/mark-recycler-handed-over', donation(id))),
    },
    BOOK_RECYCLER_PICKUP: {
      input: 'navigate',
      emphasis: 'secondary',
      labelKey: 'actions.bookRecyclerPickup.label',
      to: paths.bookRecyclerPickup,
    },
    CHOOSE_ACCEPTOR_COLLECTION: {
      input: 'confirm',
      emphasis: 'secondary',
      labelKey: 'actions.chooseAcceptorCollection.label',
      confirmKey: 'actions.chooseAcceptorCollection.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/choose-acceptor-collection', donation(id))),
    },
    CHOOSE_DROPOFF: {
      input: 'datetime',
      emphasis: 'secondary',
      labelKey: 'actions.dropoff.label',
      confirmKey: 'actions.dropoff.confirm',
      run: (id, p) =>
        unwrap(
          client.POST('/donations/{donation_id}/choose-dropoff', {
            ...donation(id),
            body: { scheduled_for: p.scheduledFor ?? '' },
          }),
        ),
    },
    MARK_HANDED_OVER: {
      input: 'confirm',
      emphasis: 'primary',
      labelKey: 'actions.handedOver.label',
      confirmKey: 'actions.handedOver.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/mark-handed-over', donation(id))),
    },
    BOOK_PICKUP: {
      input: 'navigate',
      emphasis: 'secondary',
      labelKey: 'actions.bookPickup.label',
      to: paths.bookPickup,
    },
    CANCEL: {
      input: 'confirm',
      emphasis: 'danger',
      labelKey: 'actions.cancel.label',
      confirmKey: 'actions.cancel.confirm',
      run: (id) => unwrap(client.POST('/donations/{donation_id}/cancel', donation(id))),
    },
  },
  offer: {
    ACCEPT: {
      input: 'confirm',
      emphasis: 'primary',
      labelKey: 'actions.accept.label',
      confirmKey: 'actions.accept.confirm',
      run: (id) => unwrap(client.POST('/organisations/me/offers/{match_id}/accept', match(id))),
      next: (_, result) => paths.heldDonation((result as AcceptedDonationOut).donation_id),
    },
    REJECT: {
      input: 'reject',
      emphasis: 'danger',
      labelKey: 'actions.reject.label',
      confirmKey: 'actions.reject.confirm',
      run: (id, p) =>
        unwrap(
          client.POST('/organisations/me/offers/{match_id}/reject', {
            ...match(id),
            body: { reason_code: p.reasonCode ?? 'OTHER', note: p.note || null },
          }),
        ),
      next: () => paths.acceptor,
    },
  },
  held: {
    SCHEDULE_PICKUP: {
      input: 'datetime',
      emphasis: 'primary',
      labelKey: 'actions.schedulePickup.label',
      confirmKey: 'actions.schedulePickup.confirm',
      run: (id, p) =>
        unwrap(
          client.POST('/organisations/me/donations/{donation_id}/schedule-pickup', {
            ...donation(id),
            body: { scheduled_for: p.scheduledFor ?? '' },
          }),
        ),
    },
    CONFIRM_RECEIPT: {
      input: 'confirm',
      emphasis: 'primary',
      labelKey: 'actions.confirmReceipt.label',
      confirmKey: 'actions.confirmReceipt.confirm',
      run: (id) => unwrap(client.POST('/organisations/me/donations/{donation_id}/confirm-receipt', donation(id))),
    },
  },
  admin: {
    REQUEUE: {
      input: 'reason',
      emphasis: 'primary',
      labelKey: 'actions.requeue.label',
      confirmKey: 'actions.requeue.confirm',
      run: (id, p) =>
        unwrap(client.POST('/admin/donations/{donation_id}/requeue', { ...donation(id), body: { reason: p.reason ?? '' } })),
    },
    REDIRECT_TO_RECYCLING: {
      input: 'reason',
      emphasis: 'secondary',
      labelKey: 'actions.recycle.label',
      confirmKey: 'actions.adminRecycle.confirm',
      run: (id, p) =>
        unwrap(
          client.POST('/admin/donations/{donation_id}/redirect-to-recycling', {
            ...donation(id),
            body: { reason: p.reason ?? '' },
          }),
        ),
    },
    CONFIRM_RECYCLED: {
      input: 'reason',
      emphasis: 'primary',
      labelKey: 'actions.confirmRecycled.label',
      confirmKey: 'actions.confirmRecycled.confirm',
      run: (id, p) =>
        unwrap(
          client.POST('/admin/donations/{donation_id}/confirm-recycled', {
            ...donation(id),
            body: { reason: p.reason ?? '' },
          }),
        ),
    },
    CANCEL: {
      input: 'reason',
      emphasis: 'danger',
      labelKey: 'actions.cancel.label',
      confirmKey: 'actions.adminCancel.confirm',
      run: (id, p) =>
        unwrap(client.POST('/admin/donations/{donation_id}/cancel', { ...donation(id), body: { reason: p.reason ?? '' } })),
    },
  },
};

/**
 * The donor's first offer is made from the ranked list, to a chosen organisation (or the
 * top one), so it has its own call. Whether it is possible is still the API's answer.
 */
export function offerAllowed(allowed: readonly string[]): boolean {
  return allowed.includes('OFFER');
}

export function offerTo(donationId: string, organizationId: string | null) {
  return unwrap(
    client.POST('/donations/{donation_id}/offer', {
      ...donation(donationId),
      body: organizationId ? { organization_id: organizationId } : null,
    }),
  );
}

/**
 * Platform pickup is booked from its own page (fetches the quote, books on submit),
 * not from the generic ActionBar dialog, so it has its own call like offerTo.
 */
export function bookPickup(donationId: string, providerId: string, scheduledFor: string, walletAmount: string) {
  return unwrap(
    client.POST('/donations/{donation_id}/book-pickup', {
      ...donation(donationId),
      body: { provider_id: providerId, scheduled_for: scheduledFor, wallet_amount: walletAmount },
    }),
  );
}

/** As bookPickup, but to the recycler a WASTE_REDIRECTED donation was assigned to. */
export function bookRecyclerPickup(donationId: string, providerId: string, scheduledFor: string, walletAmount: string) {
  return unwrap(
    client.POST('/donations/{donation_id}/book-recycler-pickup', {
      ...donation(donationId),
      body: { provider_id: providerId, scheduled_for: scheduledFor, wallet_amount: walletAmount },
    }),
  );
}

const EMPHASIS_ORDER: Record<Emphasis, number> = { primary: 0, secondary: 1, danger: 2 };

/**
 * The specs for the actions the API allows, primary first and destructive last. An
 * action this app version cannot perform is left out (and logged), never guessed at.
 */
export function specsFor(surface: Surface, allowed: readonly string[]): Array<[string, ActionSpec]> {
  const specs = SPECS[surface] as Record<string, ActionSpec | undefined>;
  const known: Array<[string, ActionSpec]> = [];
  for (const action of allowed) {
    const spec = specs[action];
    if (spec) known.push([action, spec]);
    else console.warn(`No ${surface} handler for action ${action}; not shown.`);
  }
  return known.sort((a, b) => EMPHASIS_ORDER[a[1].emphasis] - EMPHASIS_ORDER[b[1].emphasis]);
}
