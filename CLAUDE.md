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

1. **Every donation reaches a defined end state.** Terminal states have no outgoing
   transitions. Outcome states are `COMPLETED` (reuse) and `RECYCLED` (recovery).
   `CANCELLED` is terminal but is a donor withdrawal, not an outcome. Every donation the
   donor does not withdraw ends in reuse or recovery. No state can be entered but not left.
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

| Variable       | Added in | Purpose                    |
| -------------- | -------- | -------------------------- |
| `DATABASE_URL` | Phase 0  | Postgres connection string |
| `SECRET_KEY`   | Phase 0  | JWT signing                |
| `TEST_DATABASE_URL` | Phase 1 | Separate pytest database. **Every table in it is dropped** at the start of a run; the tests refuse to start if it names the `DATABASE_URL` database. Unset → DB tests skipped (shown in the summary) |

---

## Commands

<!-- Fill in as they are established. -->

```
# all commands run from backend/ with the venv active (.venv\Scripts\Activate.ps1)

# install dependencies
pip install -r requirements.txt

# run the API (docs at http://127.0.0.1:8000/docs)
uvicorn app.main:app --reload

# run tests (DB tests need TEST_DATABASE_URL; skipped otherwise)
pytest

# check the database answers (SELECT 1 against DATABASE_URL)
python -m app.db_check

# create a migration (review it: StrEnumType renders as sa.String(length=32))
alembic revision --autogenerate -m "describe the change"

# apply migrations
alembic upgrade head

# create an admin (password is prompted; admins cannot self-register)
python -m app.cli create-admin --email admin@example.org --name "Platform Admin"

# create the test database (once, as a Postgres superuser; the reloop role lacks CREATEDB)
psql -U postgres -c "CREATE DATABASE reloop_test OWNER reloop;"
```

---

## Decisions

Append as they are made. Reopen any of these with a better argument — but the reason
exists.

| Decision                                                                             | Reason                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FastAPI + PostgreSQL, not Django + MySQL                                             | An earlier Django prototype exists; it is not being extended and is not a reference implementation                                                                                                     |
| **No Docker Compose yet**                                                            | Postgres runs natively or on a managed tier. Add a compose file when a second machine or a deploy makes it worth it. **Never let code assume a container** — every connection detail comes from `.env` |
| **No Celery or Redis until Phase 2**                                                 | The only early scheduled job is the deadline sweep; a plain function with an admin trigger is testable and has fewer moving parts                                                                      |
| Ranking weights assigned, not learned, at launch                                     | No accept/reject history exists to learn from                                                                                                                                                          |
| Rejection boost behind a config flag                                                 | So its effect can be measured against the plain score, not assumed                                                                                                                                     |
| Donor-mediated escalation after N rejections                                         | Keeps a human in the loop where automation is least trustworthy                                                                                                                                        |
| Payments and logistics simulated                                                     | The abstractions are real; the backends are mocked and labelled as such in the UI _and_ the API response                                                                                               |
| Impact stored **per donation**, not only aggregated                                  | A future CSR or carbon module needs per-item records; aggregates can be recomputed, per-item records cannot                                                                                            |
| Backend before frontend                                                              | A polished UI over a broken state machine is harder to debug than the reverse                                                                                                                          |
| Python 3.12, Node 22 LTS pinned in README                                            | 3.12 is what's installed and satisfies the 3.11+ floor; Node isn't used until Phase 3                                                                                                                  |
| psycopg 3 via SQLAlchemy (`postgresql+psycopg://`)                                   | The Phase 0 `SELECT 1` uses the same engine and driver the app will use, so it tests the real connection path                                                                                          |
| `backend/app/config.py` is the only place env vars are read                          | One source of truth for config (non-negotiable 4 and 9); `.env` lives at repo root                                                                                                                     |
| `requirements.txt` pins direct deps only, added in the phase that first imports them | Same rule as `.env.example`: no speculative dependencies                                                                                                                                               |
| Thrift store / `SOLD` dropped from planned modules                                   | Out of scope for now; PROMPT.md and the context doc still mention it and should be read as superseded on this point                                                                                    |
| Phase 1 creates only User, OrganizationProfile, CurrentNeed, Donation, DonationImage | Tables arrive with the code that uses them; Match, StatusEvent, Wallet, Payment etc. wait until lifecycle and matching semantics are designed (Phase 2+) |
| Synchronous SQLAlchemy 2.x sessions, not async | Simpler to reason about and test; nothing in Phase 1 is I/O-bound enough to need async |
| Vocabularies (role, category, condition, urgency, status, verification status) are VARCHAR(32), validated in code against `app/constants.py`; no native Postgres ENUMs | ENUM types make adding a value a migration chore. Validation happens at the API edge (Pydantic) and the model edge (`app.db.StrEnumType`) |
| No DB CHECK constraints repeating vocabulary values | A CHECK would be a second copy of the values (non-negotiable 4). Trade-off accepted: writes from outside the app are not validated. Numeric/range CHECKs (quantity ≥ 1, lat/lng range, window order) *are* in the DB, since they repeat no constant |
| `app/constants.py` is the one module for vocabularies and tunables; `app/config.py` only for env-specific values | A test (`tests/unit/test_constants.py`) fails if any vocabulary value appears as a string literal elsewhere in `app/`, or a constant is re-declared |
| Lifecycle is a pure module (`app/domain/lifecycle.py`): table keyed by (state, action) → state, with declared `TERMINAL_STATES`, `OUTCOME_STATES`, `EDITABLE_STATES`. Phase 1 has only LISTED --CANCEL--> CANCELLED | Actions (not target states) are what callers and a future StatusEvent record. Tests check the table against the declared sets, so they keep holding as states are added |
| CANCELLED is terminal but not an outcome; Phase 1 loop gap pinned by a strict xfail | "Every non-terminal state can reach an outcome" cannot hold until Phase 2 adds COMPLETED/RECYCLED. `strict=True` makes the test fail the run once it passes, forcing removal of the marker |
| Donations are never hard-deleted; editable only while LISTED (`lifecycle.EDITABLE_STATES`) | Withdrawal is a state, not a deletion. Route handlers ask the lifecycle module; they never compare statuses |
| `DonationOut` carries `editable` and `allowed_actions` from the lifecycle module | Clients render buttons from the API instead of re-implementing status rules (non-negotiable 12) |
| Geocoding behind a `Geocoder` interface; only implementation is `PassthroughGeocoder`, a labelled **stub**. Endpoints take lat/lng, range-validated. No maps API key | A real geocoder slots in without touching callers. Because the stub cannot look addresses up, an address change must come with new coordinates (else the pin would silently go stale) |
| Phase 1: a donation is readable only by its donor and admins; no acceptor-facing donation endpoints | Address privacy (non-negotiable 10) before matching exists. Admin access to the precise address is **not logged** in Phase 1; logged release comes with acceptance in Phase 2 |
| Donors have no home-address field; pickup location belongs to each donation | Stores less sensitive data |
| Images stored behind an `ImageStorage` interface (`LocalImageStorage` under `backend/uploads/`, git-ignored), random non-guessable keys, served only via an authorised endpoint | Object storage replaces it later without touching callers |
| Every uploaded image is decoded and re-encoded from raw pixels with Pillow (JPEG/PNG/WebP only, ≤ 5 MB, ≤ 6 per donation, all-or-nothing per request) | Proves it is an image regardless of claimed type, and strips EXIF — phone photos carry GPS that would leak the donor's location |
| Pillow's `DecompressionBombWarning` is a **rejection**, not a warning; `Image.MAX_IMAGE_PIXELS` aligned to `IMAGE_MAX_PIXELS` | The warning is escalated to an error, and an explicit pixel-count check rejects independently of warning filters (which are process-global and can be reset) |
| No verification-document uploads; an admin sets verification status via `PATCH /admin/organisations/{id}/verification`, recording who and when | Documents are reviewed off-platform for now; README lists uploads as deferred |
| Quantity, storage capacity and need quantity are all **counts of items**; no capacity decrement logic | One unit everywhere; mass is estimated from counts later and labelled as an estimate |
| One login per organisation (`user_id` unique on `organization_profiles`) | Acceptor registration creates the user and the organisation together; an org with several staff logins is a later, deliberate change |
| Organisations start PENDING; only an admin can change verification status. Name and registration ID are fixed after registration | A verified organisation cannot turn into a different one by editing its profile |
| Needs are deactivated, never deleted; at most one **active** need per (organisation, category), enforced by a partial unique index; a need's category must be one the org accepts | Need history feeds demand forecasting (Phase 5); one active need per category keeps the Phase 2 need-match factor unambiguous |
| Unverified organisations may maintain their needs list | Verification gates matching, not list upkeep |
| Admins cannot self-register; `python -m app.cli create-admin` (password prompted, never on the command line) | No privilege escalation through a public endpoint |
| JWT access (30 min) + refresh (7 days), stateless, **no revocation**; refresh issues a new access token only (refresh not extended). Tokens carry only user id + type; role read from DB per request | Works unchanged for a future mobile client. Limitation stated in README |
| Passwords hashed with Argon2 via pwdlib, not passlib; unknown-email logins spend the same hashing time | passlib is unmaintained; equal timing avoids revealing which emails are registered |
| UUID primary keys | IDs cannot be guessed or enumerated |
| Not-yours → 404 (same as missing); wrong role → 403; no/invalid token → 401 | Existence of another donor's donation is not revealed |
| Tests use a separate DB (`TEST_DATABASE_URL`); session start drops all tables and runs `alembic upgrade head`; each test runs in a rolled-back transaction (`join_transaction_mode="create_savepoint"`) | Tests exercise the real migrations; `tests/test_migrations.py` also checks upgrade-from-empty, downgrade/upgrade and models-vs-migrations diff |
| Test client uses `httpx2`, not `httpx` | Starlette 1.x deprecates `httpx` for `starlette.testclient` |

---

## Future modules — do not build, but do not block

On-demand **instant pickup**
(fast geo-queries, websockets, dispatch separate from matching), volunteer network,
food category, CSR reporting, condition verification, multilingual, native apps.

**Test for the architecture:** could a module be added without editing the transition
table or the scoring function? If not, that is worth fixing now rather than during.
