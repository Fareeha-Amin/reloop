import { describe, expect, it } from 'vitest';

import type { OrganizationOut } from '../src/api/schema';
import { formFromOrganisation, hasChanges, profileChanges } from '../src/app/profileForm';

const org = {
  id: 'org-1',
  name: 'Sunrise Home',
  registration_id: 'KA-1',
  contact_person: 'Meera Iyer',
  phone: '+91 80 2222 3333',
  address_text: '12 MG Road, Bengaluru',
  latitude: 12.9716,
  longitude: 77.5946,
  pickup_capable: true,
  storage_capacity: 200,
  categories_accepted: ['CLOTHES', 'BOOKS'],
  verification_status: 'VERIFIED',
  verification_note: null,
  verification_updated_at: null,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
} as OrganizationOut;

describe('organisation profile changes', () => {
  it('sends nothing when nothing changed', () => {
    const changes = profileChanges(org, formFromOrganisation(org));
    expect(changes).toEqual({});
    expect(hasChanges(changes)).toBe(false);
  });

  it('never sends the name or registration ID', () => {
    const form = { ...formFromOrganisation(org), contact_person: 'Ravi' };
    expect(Object.keys(profileChanges(org, form))).toEqual(['contact_person']);
  });

  it('sends only the fields that changed, capacity as a number', () => {
    const form = { ...formFromOrganisation(org), storage_capacity: '50', pickup_capable: false };
    expect(profileChanges(org, form)).toEqual({ storage_capacity: 50, pickup_capable: false });
  });

  it('ignores surrounding whitespace the API would strip anyway', () => {
    const form = { ...formFromOrganisation(org), phone: ` ${org.phone} `, storage_capacity: ' 200 ' };
    expect(profileChanges(org, form)).toEqual({});
  });

  it('compares categories as a set', () => {
    expect(profileChanges(org, { ...formFromOrganisation(org), categories_accepted: ['BOOKS', 'CLOTHES'] })).toEqual({});
    expect(profileChanges(org, { ...formFromOrganisation(org), categories_accepted: ['BOOKS', 'TOYS'] })).toEqual({
      categories_accepted: ['BOOKS', 'TOYS'],
    });
  });

  it('sends coordinates with an address change, even if the pin did not move', () => {
    const form = { ...formFromOrganisation(org), address_text: '14 MG Road' };
    expect(profileChanges(org, form)).toEqual({ address_text: '14 MG Road', latitude: org.latitude, longitude: org.longitude });
  });

  it('sends coordinates alone when only the pin moved', () => {
    const form = { ...formFromOrganisation(org), pin: { lat: 12.98, lng: 77.6 } };
    expect(profileChanges(org, form)).toEqual({ latitude: 12.98, longitude: 77.6 });
  });
});
