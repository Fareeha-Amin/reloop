/**
 * Every user-facing string lives in src/i18n/en.json and is read through t().
 *
 * - Every value of every API vocabulary has a label (vocab.<Vocabulary>.<VALUE>), so a
 *   value the backend adds fails here until it is named.
 * - Every lifecycle action has a notification sentence, every condition a hint, every
 *   verification status an explanation for the organisation.
 * - Every key spelled out in the code (t('...') and `...Key: '...'` properties) exists.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

import en from '../src/i18n/en.json';

const SRC = join(__dirname, '..', 'src');

type Messages = { [key: string]: string | Messages };
const messages = en as unknown as Messages;

function lookup(key: string): string | Messages | undefined {
  let node: string | Messages | undefined = messages;
  for (const part of key.split('.')) {
    if (node === undefined || typeof node === 'string') return undefined;
    node = node[part];
  }
  return node;
}

const openapi = JSON.parse(readFileSync(join(SRC, 'api', 'openapi.json'), 'utf8')) as {
  components: { schemas: Record<string, { enum?: string[] }> };
};
const VOCABULARIES = Object.entries(openapi.components.schemas).filter(([, s]) => Array.isArray(s.enum)) as Array<
  [string, { enum: string[] }]
>;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) && !path.endsWith(join('api', 'schema.ts')) ? [path] : [];
  });
}

/** Keys written literally in the code: t('key', ...) and has('key'), and *Key: 'key' properties. */
function staticKeys(): Array<{ key: string; where: string }> {
  const keys: Array<{ key: string; where: string }> = [];
  for (const path of sourceFiles(SRC)) {
    const file = ts.createSourceFile(path, readFileSync(path, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const visit = (node: ts.Node) => {
      if (
        ts.isCallExpression(node) &&
        ts.isIdentifier(node.expression) &&
        (node.expression.text === 't' || node.expression.text === 'has') &&
        node.arguments[0] &&
        ts.isStringLiteral(node.arguments[0])
      ) {
        keys.push({ key: node.arguments[0].text, where: path });
      }
      if (ts.isPropertyAssignment(node) && ts.isIdentifier(node.name) && /Key$/.test(node.name.text) && ts.isStringLiteral(node.initializer)) {
        keys.push({ key: node.initializer.text, where: path });
      }
      ts.forEachChild(node, visit);
    };
    visit(file);
  }
  return keys;
}

describe('locale file', () => {
  it('labels every value of every API vocabulary', () => {
    expect(VOCABULARIES.length).toBeGreaterThan(10);
    const missing = VOCABULARIES.flatMap(([name, schema]) =>
      schema.enum.filter((value) => typeof lookup(`vocab.${name}.${value}`) !== 'string').map((value) => `vocab.${name}.${value}`),
    );
    expect(missing).toEqual([]);
  });

  it('has a notification sentence for every lifecycle action', () => {
    const actions = VOCABULARIES.find(([name]) => name === 'DonationAction')![1].enum;
    expect(actions.filter((a) => typeof lookup(`notify.${a}`) !== 'string')).toEqual([]);
  });

  it('has a sentence for every kind of notification', () => {
    const kinds = VOCABULARIES.find(([name]) => name === 'NotificationKind')![1].enum;
    expect(kinds.length).toBeGreaterThan(1);
    expect(kinds.filter((k) => typeof lookup(`notify.kind.${k}`) !== 'string')).toEqual([]);
  });

  it('has a hint for every condition', () => {
    const conditions = VOCABULARIES.find(([name]) => name === 'Condition')![1].enum;
    expect(conditions.filter((c) => typeof lookup(`newDonation.conditionHelp.${c}`) !== 'string')).toEqual([]);
  });

  it('contains every key the code uses', () => {
    const keys = staticKeys();
    expect(keys.length).toBeGreaterThan(100);
    const missing = keys.filter(({ key }) => lookup(key) === undefined).map(({ key, where }) => `${key} (${where})`);
    expect(missing).toEqual([]);
  });

  it('explains every verification status to the organisation', () => {
    const statuses = VOCABULARIES.find(([name]) => name === 'VerificationStatus')![1].enum;
    expect(statuses.filter((s) => typeof lookup(`acceptor.verification.${s}`) !== 'string')).toEqual([]);
  });

  it('declares its locale', () => {
    expect(() => new Intl.PluralRules(en._meta.locale)).not.toThrow();
  });
});
