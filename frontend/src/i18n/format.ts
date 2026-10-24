/** Locale-aware formatting of dates, numbers and money. */

import { LOCALE } from './index';

const dateTime = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium', timeStyle: 'short' });
const dateOnly = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium' });
const relative = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' });
const oneDecimal = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 });
const percent = new Intl.NumberFormat(LOCALE, { style: 'percent', maximumFractionDigits: 0 });

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso));
}

export function formatDate(iso: string): string {
  return dateOnly.format(new Date(iso));
}

const UNITS: Array<[Intl.RelativeTimeFormatUnit, number]> = [
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
];

/** "3 hours ago", "in 2 days". */
export function formatRelative(iso: string, now: number = Date.now()): string {
  const seconds = (new Date(iso).getTime() - now) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit);
  }
  return relative.format(Math.round(seconds), 'second');
}

export function formatNumber(value: number | string): string {
  return oneDecimal.format(Number(value));
}

/** A share in [0, 1] as a percentage. */
export function formatPercent(share: number | string): string {
  return percent.format(Number(share));
}

export function formatMoney(amount: number | string, currency: string): string {
  return new Intl.NumberFormat(LOCALE, { style: 'currency', currency }).format(Number(amount));
}
