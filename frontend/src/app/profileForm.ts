/**
 * The organisation profile form: what the user changed, as the body of
 * PATCH /organisations/me. Only changed fields are sent; the API validates them and owns
 * every rule (e.g. a category with an active need cannot be removed). Name and
 * registration ID are not editable and never sent.
 */

import type { OrganizationOut, OrganizationUpdate } from '../api/schema';

export interface Point {
  lat: number;
  lng: number;
}

export interface ProfileForm {
  contact_person: string;
  phone: string;
  /** As typed. */
  storage_capacity: string;
  categories_accepted: string[];
  pickup_capable: boolean;
  address_text: string;
  pin: Point;
}

export function formFromOrganisation(org: OrganizationOut): ProfileForm {
  return {
    contact_person: org.contact_person,
    phone: org.phone,
    storage_capacity: String(org.storage_capacity),
    categories_accepted: [...org.categories_accepted],
    pickup_capable: org.pickup_capable,
    address_text: org.address_text,
    pin: { lat: org.latitude, lng: org.longitude },
  };
}

const sameSet = (a: readonly string[], b: readonly string[]) => a.length === b.length && a.every((v) => b.includes(v));

/**
 * The changed fields. The API needs new coordinates with any address change (its geocoder
 * is a stub, so an old pin would silently mismatch), so a changed address or a moved pin
 * sends both coordinates.
 */
export function profileChanges(org: OrganizationOut, form: ProfileForm): OrganizationUpdate {
  const changes: OrganizationUpdate = {};
  if (form.contact_person.trim() !== org.contact_person) changes.contact_person = form.contact_person;
  if (form.phone.trim() !== org.phone) changes.phone = form.phone;
  if (form.storage_capacity.trim() !== String(org.storage_capacity)) changes.storage_capacity = Number(form.storage_capacity);
  if (!sameSet(form.categories_accepted, org.categories_accepted)) {
    changes.categories_accepted = form.categories_accepted as OrganizationUpdate['categories_accepted'];
  }
  if (form.pickup_capable !== org.pickup_capable) changes.pickup_capable = form.pickup_capable;

  const addressChanged = form.address_text.trim() !== org.address_text;
  const pinMoved = form.pin.lat !== org.latitude || form.pin.lng !== org.longitude;
  if (addressChanged) changes.address_text = form.address_text;
  if (addressChanged || pinMoved) {
    changes.latitude = form.pin.lat;
    changes.longitude = form.pin.lng;
  }
  return changes;
}

export function hasChanges(changes: OrganizationUpdate): boolean {
  return Object.keys(changes).length > 0;
}
