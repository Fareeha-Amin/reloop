/** Reads from the API, through TanStack Query. Polling keeps statuses fresh (no websockets). */

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { unwrap } from '../api/errors';
import type { Category, DonationStatus, VerificationStatus } from '../api/schema';
import { ADMIN_PAGE_SIZE, FEED_PAGE_SIZE, POLL_MS } from '../config';
import { client } from './api';

export const keys = {
  myDonations: ['donations'] as const,
  donation: (id: string) => ['donation', id] as const,
  timeline: (id: string) => ['timeline', id] as const,
  candidates: (id: string) => ['candidates', id] as const,
  notifications: ['notifications'] as const,
};

const path = (id: string) => ({ params: { path: { donation_id: id } } });

export function useMyDonations() {
  return useQuery({
    queryKey: keys.myDonations,
    queryFn: () => unwrap(client.GET('/donations', { params: { query: { limit: 100 } } })),
    refetchInterval: POLL_MS.list,
  });
}

export function useDonation(id: string) {
  return useQuery({
    queryKey: keys.donation(id),
    queryFn: () => unwrap(client.GET('/donations/{donation_id}', path(id))),
    refetchInterval: POLL_MS.donation,
  });
}

export function useTimeline(id: string) {
  return useQuery({
    queryKey: keys.timeline(id),
    queryFn: () => unwrap(client.GET('/donations/{donation_id}/timeline', path(id))),
    refetchInterval: POLL_MS.donation,
  });
}

/** A preview: the API stores nothing for it. Offering re-ranks. */
export function useCandidates(id: string) {
  return useQuery({
    queryKey: keys.candidates(id),
    queryFn: () => unwrap(client.GET('/donations/{donation_id}/candidates', path(id))),
  });
}

/** A preview: the API stores nothing for it. Booking re-quotes. */
export function usePickupQuote(id: string) {
  return useQuery({
    queryKey: ['pickup-quote', id],
    queryFn: () => unwrap(client.GET('/donations/{donation_id}/pickup-quote', path(id))),
  });
}

export function useWallet() {
  return useQuery({ queryKey: ['wallet'], queryFn: () => unwrap(client.GET('/wallet')) });
}

export function useNotifications(enabled: boolean) {
  return useQuery({
    queryKey: keys.notifications,
    queryFn: () => unwrap(client.GET('/notifications', { params: { query: { limit: FEED_PAGE_SIZE } } })),
    refetchInterval: POLL_MS.notifications,
    enabled,
  });
}

// --- Chat (donor and accepting organisation) -------------------------------------------------

export const chatKey = (donationId: string) => ['chats', donationId] as const;

/** Fetched only while the chat panel is open. */
export function useChats(donationId: string, enabled: boolean) {
  return useQuery({
    queryKey: chatKey(donationId),
    queryFn: () => unwrap(client.GET('/chats', { params: { query: { donation_id: donationId } } })),
    refetchInterval: POLL_MS.chat,
    enabled,
  });
}

// --- Public discovery map --------------------------------------------------------------------

export function useDiscovery(category: string | null) {
  return useQuery({
    queryKey: ['discovery', category ?? 'all'],
    queryFn: () =>
      unwrap(client.GET('/discovery/organisations', { params: { query: category ? { category: category as Category } : {} } })),
    placeholderData: keepPreviousData,
  });
}

// --- Acceptor ------------------------------------------------------------------------------

export function useMyOrganisation() {
  return useQuery({ queryKey: ['organisation'], queryFn: () => unwrap(client.GET('/organisations/me')) });
}

export function useNeeds() {
  return useQuery({ queryKey: ['needs'], queryFn: () => unwrap(client.GET('/organisations/me/needs')) });
}

export function useOffers() {
  return useQuery({
    queryKey: ['offers'],
    queryFn: () => unwrap(client.GET('/organisations/me/offers')),
    refetchInterval: POLL_MS.list,
  });
}

export function useOffer(matchId: string) {
  return useQuery({
    queryKey: ['offers', matchId],
    queryFn: () => unwrap(client.GET('/organisations/me/offers/{match_id}', { params: { path: { match_id: matchId } } })),
    refetchInterval: POLL_MS.donation,
  });
}

export function useHeldDonations() {
  return useQuery({
    queryKey: ['held'],
    queryFn: () => unwrap(client.GET('/organisations/me/donations')),
    refetchInterval: POLL_MS.list,
  });
}

export function useHeldDonation(id: string) {
  return useQuery({
    queryKey: ['held', id],
    queryFn: () => unwrap(client.GET('/organisations/me/donations/{donation_id}', path(id))),
    refetchInterval: POLL_MS.donation,
  });
}

// --- Admin -----------------------------------------------------------------------------------

export function useAwaitingAdmin() {
  return useQuery({
    queryKey: ['admin', 'awaiting'],
    queryFn: () => unwrap(client.GET('/admin/awaiting')),
    refetchInterval: POLL_MS.list,
  });
}

export function useAdminOrganisations(status: string | null) {
  return useQuery({
    queryKey: ['admin', 'organisations', status ?? 'all'],
    queryFn: () =>
      unwrap(
        client.GET('/admin/organisations', {
          params: { query: { limit: ADMIN_PAGE_SIZE, ...(status ? { verification_status: status as VerificationStatus } : {}) } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** Under ['admin', 'organisations'], so a verification change refreshes it too. */
export function useOrganisationCounts() {
  return useQuery({
    queryKey: ['admin', 'organisations', 'counts'],
    queryFn: () => unwrap(client.GET('/admin/organisations/counts')),
    refetchInterval: POLL_MS.list,
  });
}

export function useAdminOrganisation(id: string) {
  return useQuery({
    queryKey: ['admin', 'organisation', id],
    queryFn: () => unwrap(client.GET('/admin/organisations/{org_id}', { params: { path: { org_id: id } } })),
  });
}

export function useAdminDonations(status: string | null, page: number) {
  return useQuery({
    queryKey: ['admin', 'donations', status ?? 'all', page],
    queryFn: () =>
      unwrap(
        client.GET('/admin/donations', {
          params: {
            query: { limit: ADMIN_PAGE_SIZE, offset: page * ADMIN_PAGE_SIZE, ...(status ? { status: status as DonationStatus } : {}) },
          },
        }),
      ),
    placeholderData: keepPreviousData,
    refetchInterval: POLL_MS.list,
  });
}

/**
 * Every read of the admin detail is recorded in the address-access log, so it is NEVER
 * polled or refetched on focus: one read per visit, plus one after an admin action.
 */
export function useAdminDonation(id: string) {
  return useQuery({
    queryKey: ['admin', 'donation', id],
    queryFn: () => unwrap(client.GET('/admin/donations/{donation_id}', path(id))),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: false,
  });
}

export function useRecyclers() {
  return useQuery({ queryKey: ['admin', 'recyclers'], queryFn: () => unwrap(client.GET('/admin/recyclers')) });
}

export function useAdminCommission() {
  return useQuery({
    queryKey: ['admin', 'commission'],
    queryFn: () => unwrap(client.GET('/admin/commission', { params: { query: { limit: ADMIN_PAGE_SIZE } } })),
  });
}
