/** Reads from the API, through TanStack Query. Polling keeps statuses fresh (no websockets). */

import { useQuery } from '@tanstack/react-query';

import { unwrap } from '../api/errors';
import { FEED_PAGE_SIZE, POLL_MS } from '../config';
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

export function useNotifications(enabled: boolean) {
  return useQuery({
    queryKey: keys.notifications,
    queryFn: () => unwrap(client.GET('/notifications', { params: { query: { limit: FEED_PAGE_SIZE } } })),
    refetchInterval: POLL_MS.notifications,
    enabled,
  });
}
