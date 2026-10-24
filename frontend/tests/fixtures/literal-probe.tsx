// Fixture for tests/no-literals.test.ts: each kind of literal the guard must see.
// Not compiled (excluded in tsconfig.node.json) and not under src/.
export const status = 'COMPLETED';
export const action = (id: string) => `${id}:CANCEL`;
export const view = <span>BOOKS</span>;
