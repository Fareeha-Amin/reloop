/**
 * The one translation helper. Every user-facing string lives in a locale file (only
 * en.json today) and is read through t(). Adding Kannada or Hindi means adding a locale
 * file and choosing it here; components do not change.
 *
 *   t('donation.title')                       a plain string
 *   t('donor.greeting', { name: 'Asha' })     "{name}" placeholders
 *   t('common.items', { count: 3 })           plural forms {"one": ..., "other": ...},
 *                                             chosen with Intl.PluralRules
 */

import en from './en.json';

type Messages = { [key: string]: string | Messages };
export type Params = Record<string, string | number>;

const messages = en as unknown as Messages;

/** BCP 47 locale for dates and numbers, declared by the locale file. */
export const LOCALE: string = (en as { _meta: { locale: string } })._meta.locale;

const plurals = new Intl.PluralRules(LOCALE);

function lookup(key: string): string | Messages | undefined {
  let node: string | Messages | undefined = messages;
  for (const part of key.split('.')) {
    if (node === undefined || typeof node === 'string') return undefined;
    node = node[part];
  }
  return node;
}

function interpolate(template: string, params?: Params): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    params[name] === undefined ? match : String(params[name]),
  );
}

/** Whether a key exists (for vocabulary values the API may add before this file does). */
export function has(key: string): boolean {
  return lookup(key) !== undefined;
}

export function t(key: string, params?: Params): string {
  let node = lookup(key);
  if (node !== undefined && typeof node !== 'string' && params?.count !== undefined) {
    const form = plurals.select(Number(params.count));
    node = node[form] ?? node.other;
  }
  if (typeof node !== 'string') {
    if (import.meta.env?.DEV) console.warn(`Missing translation: ${key}`);
    return key;
  }
  return interpolate(node, params);
}
