/**
 * Non-negotiable 12: no business logic in React.
 *
 * Every value of every API vocabulary (statuses, actions, categories, roles, urgencies,
 * ...) may appear as a string literal only under src/vocab/, and donation statuses only
 * in src/vocab/display.ts, the one display module. Everywhere else, code renders what the
 * API says (allowed_actions, editable, ...) and looks values up through src/vocab.
 *
 * The values come from the committed OpenAPI schema, so a value the backend adds is
 * guarded here at once. The generated src/api/schema.ts is exempt.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const ROOT = join(__dirname, '..');
const SRC = join(ROOT, 'src');
const GENERATED = join('src', 'api', 'schema.ts');
const VOCAB_DIR = join('src', 'vocab') + sep;
const DISPLAY_MODULE = join('src', 'vocab', 'display.ts');

type Schema = { enum?: string[] };
const openapi = JSON.parse(readFileSync(join(SRC, 'api', 'openapi.json'), 'utf8')) as {
  components: { schemas: Record<string, Schema> };
};
const VOCABULARIES: Record<string, string[]> = Object.fromEntries(
  Object.entries(openapi.components.schemas)
    .filter(([, schema]) => Array.isArray(schema.enum))
    .map(([name, schema]) => [name, schema.enum!]),
);
const ALL_VALUES = new Set(Object.values(VOCABULARIES).flat());
const STATUS_VALUES = new Set(VOCABULARIES.DonationStatus);

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

/** Every string a file spells out: literals, template text and JSX text. */
function literals(path: string): Array<{ value: string; line: number }> {
  const text = readFileSync(path, 'utf8');
  const file = ts.createSourceFile(path, text, ts.ScriptTarget.Latest, true, path.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const found: Array<{ value: string; line: number }> = [];
  const visit = (node: ts.Node) => {
    let value: string | null = null;
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) value = node.text;
    else if (ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node)) value = node.text;
    else if (ts.isJsxText(node)) value = node.text.trim();
    if (value !== null) {
      // Exact values, and values standing alone inside longer text (e.g. JSX text).
      const tokens = new Set([value, ...value.split(/[^A-Z_]+/)]);
      for (const token of tokens) {
        if (token) found.push({ value: token, line: file.getLineAndCharacterOfPosition(node.getStart()).line + 1 });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

const FILES = sourceFiles(SRC)
  .map((path) => relative(ROOT, path))
  .filter((path) => path !== GENERATED);

describe('no vocabulary literals outside src/vocab', () => {
  it('reads the vocabularies from the OpenAPI schema', () => {
    expect(Object.keys(VOCABULARIES)).toEqual(expect.arrayContaining(['DonationStatus', 'DonationAction', 'Category', 'Role']));
    expect(STATUS_VALUES.size).toBeGreaterThan(5);
  });

  it('finds source files to check', () => {
    expect(FILES.length).toBeGreaterThan(10);
    expect(FILES).toContain(DISPLAY_MODULE);
  });

  it('keeps every vocabulary value inside src/vocab', () => {
    const offenders = FILES.filter((path) => !path.startsWith(VOCAB_DIR)).flatMap((path) =>
      literals(join(ROOT, path))
        .filter(({ value }) => ALL_VALUES.has(value))
        .map(({ value, line }) => `${path}:${line} ${JSON.stringify(value)}`),
    );
    expect(offenders, 'Use src/vocab (and the API’s allowed_actions) instead of:').toEqual([]);
  });

  it('keeps donation status values in the display module only', () => {
    const offenders = FILES.filter((path) => path !== DISPLAY_MODULE).flatMap((path) =>
      literals(join(ROOT, path))
        .filter(({ value }) => STATUS_VALUES.has(value) && !otherVocabularyHas(value))
        .map(({ value, line }) => `${path}:${line} ${JSON.stringify(value)}`),
    );
    expect(offenders, 'Status values belong in src/vocab/display.ts only:').toEqual([]);
  });

  it('catches a literal (self-test)', () => {
    const probe = join(ROOT, 'tests', 'fixtures', 'literal-probe.tsx');
    const values = literals(probe).map((l) => l.value);
    expect(values).toEqual(expect.arrayContaining(['COMPLETED', 'CANCEL', 'BOOKS']));
  });
});

/** A status value that is also another vocabulary's value (ACCEPTED is an offer response too). */
function otherVocabularyHas(value: string): boolean {
  return Object.entries(VOCABULARIES).some(([name, values]) => name !== 'DonationStatus' && values.includes(value));
}
