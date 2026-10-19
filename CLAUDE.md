# ReLoop

Circular donation & redistribution platform. Donors with reusable household goods
(clothes, toys, books) are matched to verified recipient organisations. The point of the
project is what happens **after a rejection**: re-rank, escalate to the donor, and fall
back to paid recycling — so every donation ends in reuse or material recovery.

Full background: `docs/ReLoop_Project_Context.pdf`
Build brief and phase plan: `PROMPT.md`

**Stack:** FastAPI · PostgreSQL · SQLAlchemy 2.x + Alembic · Pydantic v2 · pytest ·
React 18 + Vite + Tailwind · Celery + Redis (from Phase 2) · Scikit-learn / TensorFlow
behind interfaces.

---

## How we work

Build **one phase at a time**. For each phase:

1. Short plan first — the files you'll create or change. Then build.
2. Unit tests for anything deterministic.
3. End with: what you built, exact commands to run it, and an acceptance test I can do
   by hand.
4. **STOP** and wait for "next phase".
5. Update this file with any new decision, command or env var.

Push back when a requirement is confused, over-engineered, or would paint us into a
corner. Say so before building it.

---

## Non-negotiables

1. **Every donation reaches a defined end state.** Exactly two terminal states —
   `COMPLETED` (reuse) and `RECYCLED` (recovery). No state can be entered but not left.
2. **The lifecycle is an explicit transition table**, not conditionals scattered across
   route handlers. A test asserts every non-terminal state has ≥1 outgoing edge and both
   terminal states have none.
3. **Rejections are data.** Never delete or overwrite a `Match` row.
4. **One source of truth for every constant.** Category weights, carbon factor, fee
   percentages, thresholds — defined once, imported everywhere. A test pins this.
5. **The score explains itself.** Ranking is decomposable into its factors and surfaced
   as reasons, never a bare number.
6. **A stub says it is a stub** — in the code, in the comments and in the README. No
   `TODO` presented as a shipped feature.
7. **Nothing fails silently.** An unroutable donation surfaces to an admin queue.
8. **Estimates are labelled as estimates.** Mass and carbon figures are modelled, not
   measured.
9. **Config over hardcoding.** Weights, caps, thresholds and fees live in configuration
   so they can be tuned and measured.
10. **Donor addresses are sensitive.** Approximate location during matching; precise
    address released only after acceptance, and logged when released.
11. **Scoring and lifecycle logic are pure functions**, decoupled from the database, so
    they are unit-testable and reusable in a simulation.
12. **The API is the only source of truth.** No business logic in the React layer.

---

## Environment

`.env.example` gains a variable **the moment code reads it, never before.** A speculative
env file goes stale within a week and then lies about what the project needs.

| Variable | Added in | Purpose |
|---|---|---|
| `DATABASE_URL` | Phase 0 | Postgres connection string |
| `SECRET_KEY` | Phase 0 | JWT signing |

---

## Commands

<!-- Fill in as they are established. -->

```
# run the API

# run tests

# create a migration

# apply migrations
```

---

## Decisions

Append as they are made. Reopen any of these with a better argument — but the reason
exists.

| Decision | Reason |
|---|---|
| FastAPI + PostgreSQL, not Django + MySQL | An earlier Django prototype exists; it is not being extended and is not a reference implementation |
| **No Docker Compose yet** | Postgres runs natively or on a managed tier. Add a compose file when a second machine or a deploy makes it worth it. **Never let code assume a container** — every connection detail comes from `.env` |
| **No Celery or Redis until Phase 2** | The only early scheduled job is the deadline sweep; a plain function with an admin trigger is testable and has fewer moving parts |
| Ranking weights assigned, not learned, at launch | No accept/reject history exists to learn from |
| Rejection boost behind a config flag | So its effect can be measured against the plain score, not assumed |
| Donor-mediated escalation after N rejections | Keeps a human in the loop where automation is least trustworthy |
| Payments and logistics simulated | The abstractions are real; the backends are mocked and labelled as such in the UI *and* the API response |
| Impact stored **per donation**, not only aggregated | A future CSR or carbon module needs per-item records; aggregates can be recomputed, per-item records cannot |
| Backend before frontend | A polished UI over a broken state machine is harder to debug than the reverse |

---

## Future modules — do not build, but do not block

`SOLD` as a **third terminal state** (thrift/resale), on-demand **instant pickup**
(fast geo-queries, websockets, dispatch separate from matching), volunteer network,
food category, CSR reporting, condition verification, multilingual, native apps.

**Test for the architecture:** could a module be added without editing the transition
table or the scoring function? If not, that is worth fixing now rather than during.
