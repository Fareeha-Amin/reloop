/**
 * Roles, for routing only: which home page and which notification links a user gets.
 * Permissions are enforced by the API; a page shown to the wrong role just gets 403s.
 */

import type { Role } from '../api/schema';
import { paths } from '../app/paths';
import type { IconName } from '../ui/icons';

export interface NavItem {
  to: string;
  labelKey: string;
  icon: IconName;
  /** Match the path exactly (not its sub-pages) when highlighting. */
  end?: boolean;
}

const NAV: Record<Role, NavItem[]> = {
  DONOR: [
    { to: paths.donor, labelKey: 'nav.myDonations', icon: 'heart', end: true },
    { to: paths.newDonation, labelKey: 'nav.newDonation', icon: 'plus' },
    { to: paths.map, labelKey: 'nav.map', icon: 'map' },
  ],
  ACCEPTOR: [
    { to: paths.acceptor, labelKey: 'nav.acceptorHome', icon: 'building', end: true },
    { to: paths.map, labelKey: 'nav.map', icon: 'map' },
  ],
  ADMIN: [
    { to: paths.admin, labelKey: 'nav.adminHome', icon: 'flag', end: true },
    { to: paths.map, labelKey: 'nav.map', icon: 'map' },
  ],
};

export function navFor(role: string): NavItem[] {
  return (NAV as Record<string, NavItem[]>)[role] ?? [];
}

export const ROLE = {
  donor: 'DONOR',
  acceptor: 'ACCEPTOR',
  admin: 'ADMIN',
} as const satisfies Record<string, Role>;

const HOMES: Record<Role, string> = {
  DONOR: paths.donor,
  ACCEPTOR: paths.acceptor,
  ADMIN: paths.admin,
};

export function homeFor(role: string): string {
  return (HOMES as Record<string, string>)[role] ?? paths.home;
}

/** Where a notification about a donation takes this user. */
export function notificationLink(role: string, donationId: string): string {
  switch (role) {
    case 'DONOR':
      return paths.donation(donationId);
    case 'ADMIN':
      return paths.adminDonation(donationId);
    default:
      return homeFor(role);
  }
}
