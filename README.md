# ReLoop

Circular donation & redistribution platform: donors are matched to verified recipient
organisations, and a rejection triggers re-ranking, escalation and, as a last resort, paid
recycling, so every donation ends in reuse or material recovery.

Background: [docs/ReLoop_Project_Context.pdf](docs/ReLoop_Project_Context.pdf) ·
Build brief: [PROMPT.md](PROMPT.md) · Decision log: [CLAUDE.md](CLAUDE.md)

## Status: Phase 4 (logistics & money), plus impact metrics, a recycling choice and a handover-path fix

**What's new since Phase 4**

- **Impact metrics (estimated).** Every donation that reaches `COMPLETED` or
  `RECYCLED` gets one append-only `ImpactRecord` (`impact_records`, migration `0006`,
  backfilled for every donation already finished), written in the same transaction as
  the lifecycle move. It counts items diverted and an estimated mass
  (`quantity × CATEGORY_WEIGHT_KG`); a completed (reused) donation also gets an
  estimated carbon **avoided** (`CARBON_FACTOR_KG_PER_ITEM`, a new, **unsourced
  placeholder** constant — never called "offset"). Reuse and recycling are kept apart
  throughout: a recycled donation adds to recycled items and mass, never to reused
  items, and carries no carbon figure. `GET /impact/me` (donor) and `GET
  /impact/organisation` (acceptor, reuse only — recycling is never credited to an
  organisation) return the totals, every figure labelled `estimated` and
  `placeholders`. Shown as a card on the donor and organisation dashboards.
- **Fix: the donor chooses the handover path, so the two sides never see competing
  paths.** The original bug was that `DonationOut.allowed_actions` is filtered by actor
  (`SCHEDULE_PICKUP` is the organisation's action, so it could never appear for the
  donor) — not by `pickup_capable` as it looked. The fix went through two shapes: an
  informational list naming all three paths was tried first, then replaced by this one,
  where the donor picks a path up front. One new donor edge,
  `(ACCEPTED, CHOOSE_ACCEPTOR_COLLECTION, ACCEPTED, DONOR)` — a **self-loop, not a new
  state**: the choice is recorded as data (a `StatusEvent` on the acceptance, read back
  by `app.services.matching.acceptor_pickup_chosen`), the same way a decline or an
  escalation cause already is. `SCHEDULE_PICKUP` (the organisation's action) is gated
  on that choice being recorded; `CHOOSE_DROPOFF`, `BOOK_PICKUP` and a repeat
  `CHOOSE_ACCEPTOR_COLLECTION` are gated on it *not* being recorded, so at most one
  path is ever live. Before any choice, the donor's three options are exactly
  `allowed_actions`, rendered as buttons — no separate list. Once
  `CHOOSE_ACCEPTOR_COLLECTION` is recorded, `DonationOut.handover_options` names that
  one chosen-but-unscheduled path, and `AcceptedDonationOut.awaiting_donor_handover_choice`
  tells the organisation it is waiting on the donor (true only when that organisation
  collects and nothing is chosen yet).
- **A donor choice to recycle instead of donating.** `POST /donations/recycle`
  (`RecycleDonationCreate`: category, quantity, condition *optional*, pickup point and
  window — no note, no priority) creates the donation already in `WASTE_REDIRECTED`,
  in the same transaction (one new lifecycle edge, `LISTED --REDIRECT_TO_RECYCLING-->
  WASTE_REDIRECTED`, actor **DONOR**, reason `DONOR_CHOICE`). It is never offered to
  an organisation; with no active recycler for the category it reaches the admin
  queue (`NO_RECYCLER`), exactly as an escalated donor's redirect does. This is a
  **separate entry point** (**Send to recycling** beside **New donation** on the
  donor dashboard), not an action on an existing listing: a `LISTED` donation's own
  page still offers only edit and cancel. `Donation.condition` is now nullable, since
  a donation sent straight to recycling may have none.

**What exists (Phase 4)**

- **A third handover path: platform-arranged pickup.** Alongside the acceptor
  collecting and the donor dropping off, the donor can book a **simulated** courier
  from `ACCEPTED` (`BOOK_PICKUP`, the one new lifecycle action; actor donor). The
  donor picks a provider and a future time on its own page
  (`/donor/donations/{id}/book-pickup`, which fetches `GET
  .../pickup-quote` and posts `POST .../book-pickup`). The donor still marks the
  goods handed over and the acceptor still confirms receipt — the booking has its own
  progress (`BOOKED → PICKED_UP → DELIVERED`, or `CANCELLED`) alongside, not instead
  of, the donation's lifecycle.
- **A simulated, auto-succeeding checkout.** Cost is `base_fee + per_km_rate ×
  distance` for a `LogisticsProvider` (fictional, seeded, pricing on the record, same
  pattern as a recycler). The donor's wallet balance can cover part or all of it; the
  rest is a simulated Razorpay-style `Payment` that always succeeds. The wallet is
  optional — a donor with no balance pays the full cost.
- **Nothing is left paid but undelivered.** If a booked donation stalls out of
  `ACCEPTED`/`PICKUP_SCHEDULED`/`IN_TRANSIT` without completing (the sweeper's
  `STALL`, the only such exit — a unit test asserts this from the transition table),
  the booking is cancelled, its payment refunded, any wallet amount spent credited
  back, and its commission entry reversed by a second, negated row — all in the same
  transaction as the stall.
- **A donor wallet** (`GET /wallet`): an append-only ledger (`wallet_txns`); the
  balance is `SUM(amount)`, never stored. Credited when a recycling is confirmed
  (`donor_credit`, including every recycling confirmed before this phase — backfilled
  by migration `0005`), debited (in full or in part) by a platform-pickup booking,
  credited back if that booking is cancelled before delivery. No withdrawals.
- **A commission ledger for admins** (`GET /admin/commission`, a tab in the admin
  panel): logistics fees and recycling fees (`LOGISTICS_PLATFORM_FEE_PCT` and
  `RECYCLING_PLATFORM_FEE_PCT` are independent constants, both currently 10%). Pure
  insert-only; a reversal is a second row with the negated amount, so the total is
  always net of any undelivered bookings.
- **Backend additions:** `logistics_providers`, `bookings`, `payments`,
  `commissions`, `wallet_txns` (migration `0005`; no changes to any existing table —
  `HandoverMode` gains `PLATFORM_PICKUP` and `DonationAction` gains `BOOK_PICKUP`, both
  vocabulary additions, not schema changes). `GET /donations/{id}/pickup-quote`,
  `POST /donations/{id}/book-pickup`, `GET /wallet`, `GET /admin/commission`. A
  donation's `timeline` gains `bookings`.

**What exists (Phase 3, part 3)**

- **Chat between a donor and the organisation that accepted their donation.** A
  **Messages** button on the donor's donation page and the organisation's
  held-donation page, shown only when the API reports a thread for the viewer
  (`chat` on the donation). It carries an unread count; clicking it opens the
  conversation in a side panel (full screen on a phone), which marks the messages
  read. Dashboard lists show a *N new messages* tag on the donation. After an admin
  requeue, earlier read-only threads are reachable inside the panel. Unread counts
  are kept **on the server** per user (`chat_reads`, migration `0004`; `POST
  /chats/{id}/read`), so they follow you across devices. The open panel is polled
  every 10 seconds (`POLL_MS.chat`); a notification about a message opens the panel. Both sides can write
  from acceptance onward, including after the donation is completed. The thread
  becomes read-only only if the organisation stops holding the donation without
  completing it (a stall to the admin queue, then a requeue, cancellation or
  recycling). After an admin requeue another organisation may accept: it gets a new
  thread, the donor keeps the old one read-only, and the first organisation loses
  access to it. Messages are append-only. The organisation never sees the donor's
  name: donor messages are labelled "Donor". **Admins cannot read chats** (by
  decision, in this phase): no endpoint and no transcript on the admin donation page.
- **Organisation profile editing** at `/acceptor/profile`: contact person, phone,
  storage capacity, categories accepted, pickup capability and location (map pin and
  address). Name and registration ID are shown locked. Only changed fields are sent to
  `PATCH /organisations/me`, and matching reads the profile live.
- **Admins hear about new organisations.** Every registration appears in the admin's
  notification feed with its current verification status. The **Organisations** tab
  shows how many await verification, and each filter chip shows its count
  (`GET /admin/organisations/counts`).
- **Notifications are read one at a time.** Opening an item marks only that item as
  read; **Mark all as read** marks everything up to the newest item. Opening a chat
  thread marks its message notifications as read. Read state is kept per user in the
  browser (see Stubs and simulations).
- **Organisation registration is two steps** (your organisation, then location and a
  review), like the donation flow. The green side panel now explains the platform in
  general terms (list, match, re-route, reuse or recover) instead of making
  promises to donors, and stays in view beside the form.
- **Backend additions:** `GET /chats?donation_id=`, `POST /chats/{thread_id}/messages`,
  the `chat_messages` table (migration `0003`), `GET /admin/organisations/counts`.
  `GET /notifications` items now carry a `kind` (`DONATION_EVENT`,
  `ORGANISATION_REGISTERED`, `CHAT_MESSAGE`) and a unique `key`. The bare `id` is gone.

**What exists (Phase 3)**

- **A React frontend** (`frontend/`) for all three roles, in light and dark themes (a
  header toggle; the system setting by default).
  - **Everyone:** a landing page about the cause, registration (organisations drop a
    map pin for their location), login, and a public **discovery map** of verified
    organisations and their live needs, filterable by category.
  - **Donors:** a dashboard, a three-step donation flow (what → where & when → photos
    & review), the ranked list of organisations with each score broken into readable
    reasons, and the donation page (actions, the organisation holding it, a timeline of
    status events, offers and recycling).
  - **Organisations:** a dashboard with the offer inbox (most urgent first), the
    donations being received, the needs list (add, edit, mark as met, reopen) and the
    verification status. An offer page shows only a rounded distance; accepting it
    opens the donation with its released address, where the pickup is scheduled and
    receipt confirmed.
  - **Admins:** a panel with everything waiting on an admin (the admin queue and
    recycling to confirm, each with its allowed actions), organisations (filter,
    verify or reject with a note), all donations (status filter, paged, without
    addresses), recyclers, and a button that runs the deadline sweep. The donation
    record shows the precise address, the full timeline with reasons, and every stored
    ranking run with its score breakdowns. It never refreshes by itself, because each
    load is recorded as an address access.
  - In-app notifications for every role.
- **The UI decides nothing.** Buttons are drawn from the API's `allowed_actions`.
  Vocabulary values (statuses, actions, categories, …) appear only in
  `frontend/src/vocab/`, which a test enforces. API types are generated from the
  backend's OpenAPI schema.
- **Honest labels.** Whatever the API marks as simulated, estimated, placeholder or
  approximate is labelled the same way on screen.
- **Backend additions:**
  - `GET /notifications`: a per-user feed derived from the audit log, with no new
    table.
  - `holder` on a donation: the organisation holding it, with its address and phone,
    shown to the donor while it holds the donation.
  - `GET /discovery/organisations` (public, no login): verified organisations and
    their active needs, at positions rounded to `DISCOVERY_COORD_DECIMALS` (2 decimal
    places: within about 0.8 km). No address, phone, contact person or registration ID.
  - `GET /admin/awaiting`: every donation in a state that waits on an admin
    (`lifecycle.states_awaiting(ADMIN)`: the admin queue and recycling to confirm).
    `GET /admin/queue` is unchanged.
  - Ranking runs' `slate` is now typed (`CandidateOut`, the same shape as the donor's
    preview), and recyclers carry their `currency`.

**What exists (Phase 2)**

- **Explainable matching.** Hard filters (verified, accepts the category, not already
  offered this donation, within the search radius, enough remaining capacity), then a
  weighted sum of five factors: proximity, declared need, urgency, capacity headroom
  and a smoothed acceptance rate. Every score is broken into structured components
  (factor, raw value, value, weight, contribution). The weights are **assigned, not
  learned**: there is no accept/reject history yet. Donor rating is not a factor
  until reviews exist.
- **The full lifecycle** in one transition table (`app/domain/lifecycle.py`), with the
  actor allowed for each edge declared beside it. Two outcomes, `COMPLETED` (reuse)
  and `RECYCLED` (material recovery). `CANCELLED` is a withdrawal. `NEEDS_ADMIN` is
  the admin queue: a real state with admin exits. No deadline ends a donation
  automatically.
- **Offers.** The donor makes the first offer, to the top candidate or to any
  eligible one. There is at most one open offer at a time. After a rejection or
  expiry, the system re-offers to the next candidate in the same transaction.
- **Rejection boost**, behind `REJECTION_BOOST_ENABLED`. Each decline (a rejection or
  an expiry) widens the search radius and raises the donation in acceptors' inboxes.
  It never alters candidate scores. After 3 declines since the last escalation, the
  donation **escalates** to the donor: re-match, upgrade to priority, recycle or
  cancel. Re-match and upgrade are offered only while candidates remain.
- **The pickup window is advisory.** Acceptors see it, but nothing enforces it and it
  never escalates anything. A donation the donor never offers escalates after
  `LISTED_STALL` (7 days), with cause `NOT_OFFERED`.
- **Handover.** The acceptor schedules a pickup, or the donor chooses drop-off; the
  time only has to be in the future. The donor marks the goods handed over, and the
  acceptor confirms receipt.
- **Recycling fallback.** Only the donor (at escalation) or an admin (with a reason)
  can send a donation to recycling. The donation goes to the nearest active recycler
  that accepts the category. If there is none, it goes to the admin queue.
- **Deadline sweeper**, `sweep(now)`. It runs inside the API process every 15 minutes
  (`SWEEP_INTERVAL`; off with `SWEEPER_ENABLED=false`). `POST /admin/sweep` and
  `python -m app.cli sweep` run it on demand. It expires unanswered offers, escalates
  donations never offered, and sends silent donors and stalled handovers to the admin
  queue.
- **Audit.** An append-only `status_events` row is written for every transition, in
  the same transaction, under the donation's row lock. Every ranking run that led to
  a decision is stored with its full slate and config version.
- **Address privacy.** Before acceptance an acceptor sees only a distance rounded to
  0.5 km, never the address or coordinates. The precise address is released to the
  accepting organisation, and the release is recorded. It stays visible only while
  that organisation holds the donation. Admin reads of the address are recorded too,
  and the admin list is redacted.
- Bengaluru seed data (`python -m app.cli seed`, idempotent).

**From Phase 1**

- FastAPI service with OpenAPI docs at `/docs`.
- JWT auth (access + refresh) with three roles, Donor, Acceptor and Admin, enforced by
  route-level dependencies.
- Donor and acceptor self-registration. An acceptor registers its login and its
  organisation profile (including categories accepted) together. Organisations start
  `PENDING`.
- Admin accounts, created only from the CLI. An admin endpoint sets an organisation's
  verification status and records which admin changed it and when.
- Organisation needs list: create, update, deactivate. Needs are never deleted, and an
  organisation can have at most one active need per category.
- Donation CRUD. Donors can edit while `LISTED` (the donation is kept, never deleted).
- Donation image upload, read and delete. Images are validated server-side and
  re-encoded, which strips EXIF (including GPS) and other metadata.
- Alembic migrations, plus tests covering unit logic, the API, role enforcement and
  migrations.

**What does not exist yet.** Reviews, push and email notifications, corporate drives,
impact analytics and leaderboards, demand forecasting, weight calibration from real
history. Anything not listed above is not built.

### Stubs and simulations

| Component | Status |
|---|---|
| **Geocoding** (`app/services/geocoding.py`) | **STUB.** `PassthroughGeocoder` returns the coordinates the client sends, unchanged and unverified. No address lookup takes place, and there is no maps API key. Endpoints therefore require `latitude`/`longitude`, and changing an address requires new coordinates. |
| **Image storage** (`app/services/storage.py`) | Local disk under `backend/uploads/` (git-ignored), behind an `ImageStorage` interface so object storage can replace it. Files are served only through an authorised endpoint. |
| **Recycling settlement** (`app/domain/recycling.py`) | **SIMULATED.** Mass is **estimated** as quantity × a per-category weight. The settlement (gross value, donor credit, platform fee) credits the donor's wallet and the commission ledger; no real money moves. Labelled `simulated` / `mass_is_estimate` in every API response. |
| **Per-category weights** (`CATEGORY_WEIGHT_KG`) | **PLACEHOLDERS** (clothes 0.5 kg, toys 0.3 kg, books 0.4 kg per item) pending a cited source. Responses carry `weights_are_placeholders: true`. |
| **Per-category carbon factors** (`CARBON_FACTOR_KG_PER_ITEM`) | **PLACEHOLDERS, not sourced** (clothes 5.0 kg CO2e, toys 2.0 kg, books 1.5 kg, avoided per item reused). Credited to reuse only, never to recycling. `GET /impact/me` and `GET /impact/organisation` carry `placeholders: true` and `estimated: true`. |
| **Recycler confirmation** | **SIMULATED.** There is no recycler login. An admin confirms recycling on the recycler's behalf, with a recorded reason. |
| **Platform-arranged pickup** (`app/services/logistics.py`, `app/domain/logistics.py`) | **SIMULATED.** `LogisticsProvider` rows are fictional (seeded, like `WasteCollector`); there is no real courier API. Cost is distance-based, labelled `simulated` in every response. |
| **Checkout** (`app/models/logistics.py: Payment`) | **SIMULATED.** A Razorpay-style mock that always succeeds, with a simulated transaction id. No payment gateway is called, and no real money moves. |
| **Distances** | Haversine in Python over every organisation that accepts the category. No PostGIS. Fine at seed scale; revisit when the instant-pickup module needs fast geo-queries. |
| **Map tiles** (frontend) | OpenStreetMap's public tile servers, no API key. Their usage policy suits development and demos, not production traffic: a deployment needs a tile provider. Locations are the pins people drop; nothing is geocoded. |
| **Discovery map positions** | **APPROXIMATE.** Rounded to 2 decimal places of a degree before they leave the API (`positions_are_approximate`, `position_error_km`), and drawn as shaded areas, not pins. Matching uses the precise positions. |
| **Notifications** | In-app only, polled (`POLL_MS` in `frontend/src/config.ts`). **Push (Firebase Cloud Messaging) and email are deferred**, not built. The feed is derived on each request from status events, organisation registrations and chat messages; there is no notifications table. Read state is kept **in each browser's localStorage**, per user (the keys read one by one, at most `READ_KEYS_MAX`, plus a "mark all as read" time), so it does not follow you to another device or another browser. |
| **Chat** | Polled every 10 s (`POLL_MS.chat`), not pushed: no websockets. Messages appear in the other party's notification feed (without their text). |

### Deferred (not built, by decision)

- **Verification-document uploads.** An admin verifies an organisation through
  `PATCH /admin/organisations/{id}/verification`. Documents are reviewed outside the
  platform for now.
- Rate limiting on donation creation, login and accept/reject.
- Explicit consent capture before storing an address (DPDP), and a retention policy.
- Rescheduling a handover, and recycler or logistics-provider management endpoints
  (both come from the seed or the database; no admin UI to add or edit one).
- A pickup-slot *suggestion*: the donor picks any future time, the same as drop-off.
  By decision, dropped before building — see CLAUDE.md.
- Wallet withdrawals. Wallet credit can only be spent on a platform pickup.
- Weight calibration from the stored ranking runs (Phase 5), and a fairness constraint
  if one organisation turns out to win every match.

### Known limitations (Phase 2)

- **An acceptor that accepts and then goes silent** is not penalised. Its acceptance
  still counts in its acceptance rate, and the donation reaches the admin queue only
  after `STALL_TIMEOUTS[ACCEPTED]` (72 h). There is no acceptor "withdraw" action, by
  decision: a reneging acceptor goes STALL → NEEDS_ADMIN → admin re-queue.
- **Write-once and append-only rules are enforced by the ORM**, not by database
  triggers. A write made outside the app, or a bulk SQL `UPDATE`, would bypass them. A
  test fails if app code imports SQLAlchemy's bulk `update`/`delete`.
- The sweeper runs only while the API runs. It skips donations locked by a concurrent
  request and picks them up on its next run. With several API processes each runs its
  own loop. That is safe (row locks, with every decision re-made under the lock), just
  redundant.

### Known limitations

- **JWTs are stateless and cannot be revoked.** There is no server-side session and no
  deny-list. An access token stays valid for its 30 minutes and a refresh token for its
  7 days, even after a password change. Refreshing issues a new access token only; it
  does not extend the refresh token, so a session ends when its refresh token expires.
- **Tokens contain only the user id.** The role is read from the database on every
  request, so a role change takes effect immediately.
- **Where the browser keeps tokens (XSS trade-off).** The access token is kept in memory
  only. The refresh token is in `localStorage`, so a session survives a page reload.
  Any script that runs on the app's origin (an XSS bug, a compromised dependency) could
  read the refresh token and use it until it expires, up to 7 days, because refresh tokens
  cannot be revoked. An `HttpOnly` cookie would close that gap, at the cost of CSRF
  handling and a cookie flow that a future mobile client would not share.
- **Server error messages are in English.** The UI's own text comes from the locale
  file, but messages from the API are shown as sent.
- **Donors have no profile page.** Organisations edit theirs at `/acceptor/profile`.
- **Organisations see the donor's address, not their name or phone.** The API releases
  the pickup address on acceptance. Anything more is up to the donor, in the chat.
- **Chat has no moderation, rate limiting or deletion.** Admins cannot read chats in
  this phase, so abuse in a thread cannot be reviewed on the platform. Messages are
  append-only: no edits, and no deletion on request (the DPDP retention question is
  still open, as for addresses).
- **A requeued organisation loses its thread.** Once another organisation accepts the
  donation, the first one can no longer read what it wrote there; the donor still can.
- **Notification read state is per browser.** After this update every existing
  notification shows as unread once (the old "newest id seen" marker is discarded);
  **Mark all as read** clears them. A notification committed slightly later than a
  newer one may count as read after "mark all".
- **The admin organisation list shows the first 25** for each filter, without paging.
- **No provider list in the admin panel.** `LogisticsProvider` rows come from the
  seed only; they show up wherever a pickup quote already lists them, not in their
  own admin tab (same decision as recyclers).
- **Dark mode needs a 2024-or-later browser** (Chrome 123, Safari 17.5, Firefox 120):
  the colour tokens use CSS `light-dark()`. Older browsers get the light theme.

### Units

`Donation.quantity`, `OrganizationProfile.storage_capacity` and
`CurrentNeed.quantity_needed` are all **counts of items** (e.g. 12 shirts), never
kilograms or bags.

## Pinned versions

| Tool | Version |
|---|---|
| Python | **3.12** |
| Node | **24 LTS** (developed on 24.22.1) |
| React / Vite / Tailwind | 19.3 / 8.3 / 4.3 (exact versions in `frontend/package.json`) |
| TypeScript | **5.9** (openapi-typescript does not support 7 yet) |
| PostgreSQL | **15+** (developed against 17) |

## Layout

```
backend/
  app/
    constants.py      every vocabulary and tunable, defined once
    config.py         environment variables, read once
    domain/           pure logic, no database: lifecycle table, scoring, policy
                      (boosts, guards, sweeper rules), recycling maths, geo
    models/           SQLAlchemy models
    schemas/          Pydantic request/response models
    security/         passwords, JWTs, role dependencies
    services/         database operations: transitions (the one place status changes),
                      matching, actions, offers, recycling, sweeper, seed, ...
    routers/          HTTP endpoints
    cli.py            operator commands (create-admin, seed, sweep)
  alembic/            migrations
  tests/              unit/, api/, test_migrations.py
frontend/
  src/
    api/              openapi.json (exported from the backend), schema.ts (generated),
                      the client, token refresh, error parsing
    vocab/            the only place API vocabulary values appear: tones, labels,
                      action → endpoint map, role → home page, notification
                      sentences and links
    i18n/             en.json (every user-facing string) and the t() helper
    styles/theme.css  design tokens: the one place to restyle
    ui/               shared, token-only components (buttons, cards, tags, forms, ...)
    components/       ReLoop components (timeline, action bar, maps, needs, ...)
    pages/            routes, built from ui/ and components/: auth/, donor/,
                      acceptor/, admin/, the landing page and the discovery map
  tests/              Vitest: API client, token refresh, no-literals guard, locale,
                      notification read state, profile form changes
docs/       project context document
```

## Setup (Windows / PowerShell)

```powershell
# 1. Environment
Copy-Item .env.example .env        # then edit DATABASE_URL, SECRET_KEY, TEST_DATABASE_URL

# 2. Databases (once, as a Postgres superuser): the app DB and a separate test DB
psql -U postgres -c "CREATE DATABASE reloop_test OWNER reloop;"

# 3. Python env
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Schema, first admin, seed data
alembic upgrade head
python -m app.cli create-admin --email admin@example.org --name "Platform Admin"
python -m app.cli seed              # Bengaluru organisations, recyclers, a demo donor

# 5. Run
uvicorn app.main:app --reload       # http://127.0.0.1:8000/docs
pytest                              # DB tests are skipped if TEST_DATABASE_URL is unset

# 6. Deadlines: the sweeper runs inside the API every 15 minutes (SWEEPER_ENABLED).
#    To run it now (safe to repeat):
python -m app.cli sweep
```

```powershell
# 7. Frontend (second terminal; Node 24 LTS). The backend must be running on port 8000.
cd frontend
npm install
npm run dev                         # http://localhost:5173 (calls the API through /api)
npm test                            # API client, token refresh, no-literals guard, locale,
                                    # read state, profile form

# After changing the API: re-export the schema and regenerate the client types
cd backend; python -m app.cli export-openapi
cd ../frontend; npm run gen:api
```

`pytest` sets `SWEEPER_ENABLED=false` for itself, so tests never sweep the real database.

On macOS/Linux, use `python3.12 -m venv .venv && source .venv/bin/activate`.

Postgres can be a native install or a managed tier (Neon, Supabase). Every connection
detail comes from `.env`. Nothing assumes a container.

## Acceptance test (Phase 2)

Run it through `/docs` after `seed`, logging in with **Authorize** (the username is the
email). Seed organisations log in as `seed.<slug>@example.org` with the seed password.
`tests/api/test_acceptance_script.py` automates these same steps.

**Who gets each offer is not fixed.** Ranking depends on every verified organisation in
the database, not only the seed ones, and on each one's accept/reject history. A
database that kept Phase 1's `/docs` example organisation ("Sunrise Home", MG Road,
with a HIGH clothes need) offers it second. Earlier runs also lower the acceptance rate
of organisations that declined. So the steps never name an organisation. Each time,
**find the holder**:

1. As the donor, call `GET /donations/{id}/timeline`. The holder is the offer whose
   `response` is `null`.
2. As admin, call `GET /admin/organisations/{organization_id}`. `account_email` is
   its login. You need that account's password: the seed password for seed
   organisations, otherwise whatever it was registered with.

Each offer goes to rank 1 of the ranking run it was made from. `GET
/admin/donations/{id}` shows those runs, with every score broken into its factors and
the radius in effect. That admin read is itself recorded as an address access.

**A. Rejected until it escalates, then COMPLETED**
1. As `demo.donor@example.org`, `POST /donations` with the pre-filled example (clothes,
   Indiranagar) → `LISTED`, allowed `[CANCEL, OFFER]`.
2. `GET /donations/{id}/candidates`. Expect a ranked slate, each candidate with five
   components, `radius_km` 15, and `filtered_out` counts.
3. `POST /donations/{id}/offer` with no body → `MATCHED`.
4. Three times: find the holder, log in as it, and `GET /organisations/me/offers`. The
   offer shows a distance rounded to 0.5 km and no address or coordinates. Then
   `POST /organisations/me/offers/{match_id}/reject` with
   `{"reason_code": "NO_CAPACITY"}`. After each of the first two, the donation is
   `MATCHED` again with a new holder. The search radius grows 15 → 18.75 → 22.5 km, so
   an organisation further out can appear. After the third it is `ESCALATED` with
   `escalation_cause` `THRESHOLD_REACHED` and allowed
   `[CANCEL, REDIRECT_TO_RECYCLING, REMATCH, UPGRADE_PRIORITY]`.
5. As the donor, `POST /donations/{id}/rematch` → `MATCHED`, with a fourth holder.
6. Find the holder and accept: `POST /organisations/me/offers/{match_id}/accept` →
   `ACCEPTED`, `address_released: true`, with the pickup address.
7. If the accept response's `allowed_actions` is `[SCHEDULE_PICKUP]`, the
   organisation collects: `POST /organisations/me/donations/{id}/schedule-pickup`.
   If it is `[]`, the organisation does not collect, so the donor uses
   `POST /donations/{id}/choose-dropoff`. Either way the body is
   `{"scheduled_for": <any future time>}` → `PICKUP_SCHEDULED`.
8. As the donor, `POST /donations/{id}/mark-handed-over` → `IN_TRANSIT`.
9. As the holder, `POST /organisations/me/donations/{id}/confirm-receipt` →
   `COMPLETED`, with `address_released: false`.

**B. No candidates → recycling → RECYCLED**
1. As the donor, `POST /donations` with `"pickup_latitude": 13.0977,
   "pickup_longitude": 77.3910` (Nelamangala: the nearest verified organisation is about
   22 km away, beyond the 15 km radius).
2. `POST /donations/{id}/offer` → `ESCALATED`, cause `NO_CANDIDATES`, allowed
   `[CANCEL, REDIRECT_TO_RECYCLING]`.
3. `POST /donations/{id}/redirect-to-recycling` → `WASTE_REDIRECTED`.
4. As admin, `POST /admin/donations/{id}/confirm-recycled` with `{}` → 422. Then with
   `{"reason": "Recycler confirmed"}` → `RECYCLED`.
5. As the donor, `GET /donations/{id}/timeline`. `recyclings[0]` names the nearest
   active CLOTHES recycler (with the seed data, GreenCycle Textile Recovery, 15.9 km).
   The settlement for 12 items at 0.5 kg and INR 12/kg is 6.000 kg, gross 72.00, fee
   7.20 and donor credit 64.80, with `simulated`, `mass_is_estimate` and
   `weights_are_placeholders` all `true`.

**C. Toys → no recycler → NEEDS_ADMIN**
1. As B, but with `"category": "TOYS"`: offer → `ESCALATED`, then
   redirect-to-recycling → `NEEDS_ADMIN`.
2. As admin, `GET /admin/queue`. The item for this donation shows `via: NO_RECYCLER`,
   `allowed_actions: [CANCEL]` and no address. Other items may be in the queue.
3. `POST /admin/donations/{id}/requeue` and `.../redirect-to-recycling` (each with a
   reason) → 409. `POST /admin/donations/{id}/cancel` with a reason → `CANCELLED`.

## Acceptance test (Phase 3, in the browser)

The same three paths, through the UI. Start the API (`uvicorn app.main:app --reload`)
and the frontend (`npm run dev`), run `seed` once, and use three browser windows (or
one normal and two private windows), since each holds one login: the donor
`demo.donor@example.org`, the admin, and whichever organisation is offered the
donation. Seed organisations log in as `seed.<slug>@example.org` with the seed
password.

**Finding the holder, in the UI:** on the donor's donation page the line under the
title says who the offer is waiting for. As admin, open the **Organisations** tab, find
that organisation, and its page shows the **Login email**.

**Before you start:** open `/map` while logged out. Verified organisations appear as
shaded circles with their needs, marked **Approximate**; the category chips filter
them. No address or phone appears anywhere on the page.

**A. Rejected until it escalates, then COMPLETED**
1. As the donor: **New donation** → Clothes, Gently used, 12 → **Use my location** or
   drop a pin in Indiranagar, type an address → **List and find matches**. The ranked
   list opens, each card with a match score and **Why this ranking**.
2. **Offer** on the first card. The donation page shows *Offered* and *Waiting for … to
   answer*.
3. Three times: log in as the holder. Its dashboard lists the offer under **Offers
   waiting for you**; open it. The page shows *About N km away* (**Approximate**) and no
   address. **Decline** → pick a reason → **Decline**. You return to the dashboard.
   After the third decline the donor's page says **Your decision is needed** and offers
   **Re-match**, **Send to recycling**, **Upgrade to priority** and **Cancel donation**.
4. As the donor, **Re-match** → confirm. A fourth organisation holds the offer.
5. As that organisation, open the offer → **Accept** → confirm. You land on the
   donation with **The donor's pickup point** (address and map, *Released to you*).
6. If the page offers **Schedule pickup**, the organisation collects: choose a time.
   If it offers nothing, the organisation does not collect: as the donor, **I'll drop
   it off** and choose a time. The donor's page now shows **Who's receiving it** with
   the organisation's address and phone.
7. As the donor, **I've handed it over**. As the organisation, **Confirm receipt**: the
   page says *You no longer hold this donation* and hides the address. The donor sees
   **Completed · reused**.
8. As admin, open the donation (from **Donations**, or a notification). The notice says
   the view was recorded; **Ranking runs** lists four runs, each offer made to rank 1.

**B. No candidates → recycling → RECYCLED**
1. As the donor, list clothes with the pin at Nelamangala: zoom the map out and drop it
   on the town, about 26 km north-west of the centre (the nearest verified organisation
   is beyond the 15 km radius).
2. The ranked list says **No organisation in range right now** → **Continue**. The
   donation page offers only **Send to recycling** and **Cancel donation**.
3. **Send to recycling** → confirm → *Going to recycling*.
4. As admin, **Waiting on you** lists it under *Going to recycling* with one button,
   **Confirm recycled**. It stays disabled until a reason is typed; confirm.
5. As the donor, the page shows *Recycled* and a recycling card (GreenCycle Textile
   Recovery, 15.9 km): 6 kg, ₹72.00, fee ₹7.20, your credit ₹64.80, marked
   **Simulated**, **Estimated mass** and **Placeholder weights**.

**C. Toys → no recycler → NEEDS_ADMIN**
1. As B, but Toys: **Send to recycling** → *Admin review*.
2. As admin, **Waiting on you** lists it under *Admin review*, arrived *No recycler in
   range*, with only **Cancel donation** (no re-queue and no recycling, because there
   is nothing to re-queue to and no recycler). Cancel with a reason → *Cancelled*.

**Organisations and verification**
1. Register a new organisation at `/register`. Its dashboard says it is pending; add a
   need with **Add a need**.
2. As admin, **Organisations** → *Pending verification* → open it → **Status:
   Verified**, add a note → **Save verification**. The organisation's dashboard now
   says it is verified and shows the note, and it appears on `/map`.
3. **Run the sweep now** reports what it checked and changed (usually nothing).

## Acceptance test (Phase 3, part 3, in the browser)

Apply the new migrations first (`alembic upgrade head` from `backend/`: they add the
`chat_messages` and `chat_reads` tables and change nothing else), then restart the API and the frontend.
The setup is the same as above: seed data, three browser windows (donor, admin,
organisation).

**A, with chat: an exchange before and after completion.** Run path A above up to
step 5 (the organisation accepts). Then:
1. Before acceptance there is no **Messages** button anywhere. After the organisation
   accepts, a **Messages** button appears on its donation page. Click it: a panel
   opens (full screen on a phone) saying *No messages yet*. Type a message → send
   (Enter also sends; Shift+Enter makes a new line). It appears on the right, labelled
   **You**. Close the panel with the × or Escape.
2. In the donor's window, within about 30 seconds, the **My donations** list shows a
   *1 new message* tag on that donation, the donation page's **Messages** button has a
   count, and the bell shows an item. Click the button: the panel shows the message
   labelled with the organisation's name, and the count, tag and notification clear.
   Reply. The organisation sees the reply labelled **Donor**, never the donor's name.
3. Finish path A (steps 6–7): schedule the handover, **I've handed it over**,
   **Confirm receipt**. The donor sees **Completed · reused**.
4. After completion, send another message from each side. Both go through: the thread
   stays open after completion.
5. As admin, open the donation record: there is **no** conversation on it (admins
   cannot read chats).

*(Optional, the closed case.)* Accept another donation as an organisation and leave it
in *Accepted*. As admin, nothing can be done until it stalls (72 h); the API tests cover
this (`tests/api/test_chat.py`): after a stall the thread shows **This conversation is
closed** and the message box is gone.

## Acceptance test (Phase 4, in the browser)

Apply migration `0005` first (`alembic upgrade head` from `backend/`: it adds
`logistics_providers`, `bookings`, `payments`, `commissions`, `wallet_txns`, and
backfills wallet and commission rows for any recycling already confirmed). Re-run
`seed` to get the three fictional logistics providers (idempotent).

**A completed donation paid partly with wallet credit from an earlier recycling.**
1. Run acceptance test B (recycling → `RECYCLED`) above with the demo donor, so the
   wallet has a credit. As the donor, open **Wallet** (the card on the dashboard, or
   `/donor/wallet`): the balance matches the recycling's *Your credit*, and the
   ledger shows one **Recycling credit** entry.
2. List and offer a new clothes donation, get it accepted (as in test A, steps 1–5).
   On the accepted donation's page, click **Book platform pickup**.
3. The page shows the distance and a cost per courier. Pick one, leave the time at
   its default (any future time — the pickup window is only a preference), and set
   **Use from your wallet** to less than the full cost. The summary below splits the
   cost into *From your wallet* and *By simulated checkout* exactly. **Book and pay**.
4. The donation page shows *Handover scheduled* with a **Platform pickup** booking
   card in the timeline (status *Booked*, the cost split, a simulated transaction
   id). **Wallet** shows the balance reduced by exactly the wallet amount used.
5. As the donor, **I've handed it over** — the booking card now says *Picked up*. As
   the organisation, **Confirm receipt** — the donor sees **Completed · reused** and
   the booking card says *Delivered*.
6. As admin, open **Commission**: the total includes this booking's fee (10% of its
   cost) and the earlier recycling's fee.

**The refund path: a stalled booking.**
1. Repeat steps 1–3 above (book a platform pickup, with some wallet amount), but
   never click **I've handed it over**.
2. As admin, **Run the sweep now** (after the handover grace period has passed — in
   a hurry, `python -m app.cli sweep` against a donation whose `scheduled_for` you
   backdated, or wait). The donation moves to **Admin review**.
3. As the donor, the booking card now says *Cancelled* with a reason, the payment
   shows *Refunded* with a refund transaction id, and **Wallet** shows the wallet
   amount credited back — its balance is exactly what it was before the booking.
4. As admin, **Commission** shows the booking's fee reversed: the total is back to
   what it was before the booking (the earlier recycling's fee only).
5. **Re-queue** or **Cancel** the donation from the admin queue: either way, the
   booking and payment stay exactly as settled in step 3.

**A profile edit that changes matching.**
1. As the donor, **New donation** → Toys, 5, pin in Indiranagar → **List and find
   matches**. Note the list: *Koramangala Community Shelter* is not on it (it does not
   accept toys).
2. Log in as `seed.koramangala-shelter@example.org`. **Profile** (in the navigation, or
   **Edit** on the dashboard's profile card). Name and registration ID show a lock. Tick
   **Toys** → **Save changes** → *Saved*.
3. As the donor, reload the ranked list: *Koramangala Community Shelter* now appears,
   with its score broken into reasons.
4. As the organisation, set **Storage capacity** to 0 → **Save changes**. Reload the
   donor's list: it is gone again (not enough storage). Try to untick **Clothes**: the
   API refuses with *Active needs exist for CLOTHES…*, shown on the page.
5. Put the profile back (capacity 200, untick Toys) and save: seed rows are never
   updated by `seed`, so the edit would otherwise stay.
6. Move the map pin and change the address, then **Discard changes**: the form returns
   to the saved values.

**A new organisation shows up for the admin.**
1. Logged out, register a new organisation at `/register`.
2. As admin (refresh, or wait up to 30 s): the bell has an unread item *“<name>
   registered as an organisation”*. The **Organisations** tab has a clay-coloured count
   (organisations awaiting verification; the seed data alone has two), and the tab
   opens with *N organisations awaiting verification* and a count on each filter chip.
3. Click the notification: it opens that organisation's admin page. Verify it. Back on
   **Notifications**, the item now shows the **Verified** tag, and the tab count has
   dropped by one.

**Reading one notification at a time.**
1. As the donor with several unread notifications, open **Notifications**. The page
   says *N unread*; nothing is marked read just by opening it.
2. Click one item. It opens its page. Go back: only that item lost its bold text and
   dot, and the count is one lower. The bell agrees.
3. **Mark all as read**: every item is read and the button is disabled. Trigger a new
   event (for example, an organisation sends a chat message): only the new item is
   unread.
4. Reload the page: read state is kept. In a different browser it is not (by design,
   it's stored in the browser).

## Acceptance test (impact metrics, the handover-path fix, and recycling choice)

Apply migration `0006` first (`alembic upgrade head` from `backend/`: it adds
`impact_records`, backfills it for every donation already `COMPLETED` or `RECYCLED`,
and makes `donations.condition` nullable).

**The donor chooses a handover path before the organisation sees any scheduling action.**
1. As the donor, list a clothes donation and offer it to a **pickup-capable**
   organisation (the seed's organisations are pickup-capable by default). Accept it as
   that organisation.
2. As the organisation, open the held donation. There is **no Schedule pickup
   button** — an info panel says **Waiting for the donor to choose**.
3. As the donor, open the donation. The action bar has three buttons: **They collect
   it**, **I'll drop it off**, **Book platform pickup**. Click **They collect it** and
   confirm.
4. The donor's donation page now shows no handover buttons at all, and a card names
   the chosen path: *Organisation collects*, marked **They arrange it**. Reload: the
   same three buttons do not come back.
5. As the organisation, reload its held-donation page: the waiting panel is gone and
   **Schedule pickup** now appears. Schedule it; the flow continues exactly as before
   (mark handed over, confirm receipt).
6. Repeat from step 1, but this time as the donor click **I'll drop it off** directly,
   without choosing **They collect it** first: it still works, moving straight to
   *Pickup scheduled*, same as before this fix.
7. Repeat once more with **Book platform pickup**: also still works unchanged.
8. Repeat with an organisation whose **We can collect donations** is off (uncheck it
   via `PATCH /organisations/me` or the seed data): the donor's action bar has no
   **They collect it** button at all, and the organisation's held-donation page shows
   no waiting panel either (it was never going to get a schedule action).

**Send a donation straight to recycling.**
1. As the donor, on the dashboard click **Send to recycling** (beside **New
   donation**). Fill category, quantity, condition (try leaving it blank — it's
   optional), pickup point and window.
2. The confirmation step states the item will not be offered to any organisation and
   that it goes to the admin queue if no recycler accepts the category. **Send to
   recycling**.
3. The donation page shows status **Recycling** (or **Admin review**, if no recycler
   accepts clothes within range) immediately — it was never `LISTED` as far as the UI
   shows, and its allowed actions are empty.
4. Open an ordinary `LISTED` donation (from **New donation**): its page offers only
   **Cancel** (and edit, while listed) — no "send to recycling" option there.
5. As admin, **Confirm recycled** on the redirected donation (if it reached a
   recycler). The donor's **Impact** card (below) now counts it as recycled mass, not
   reused items.

**Impact cards.**
1. Complete a donation (test A in the Phase 2 acceptance test, or the reuse flow
   above) end to end to **Completed**. As the donor, the dashboard's **Your impact**
   card shows *Items reused* and *Carbon avoided* up by this donation's quantity and
   its category's (placeholder) factors — both marked **Estimated mass** and
   **Placeholder weights**.
2. As the accepting organisation, its dashboard's **Your impact** card shows the same
   reused items and carbon (no recycled figures: recycling is never credited to an
   organisation).
3. Send a donation to recycling and confirm it (as above). The donor's card shows
   *Items recycled* and *Mass recycled* up by its quantity — *Items reused* and
   *Carbon avoided* are unchanged by it.
4. Cancel a `LISTED` donation: neither card changes.
