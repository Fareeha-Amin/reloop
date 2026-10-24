# ReLoop

Circular donation & redistribution platform: donors are matched to verified recipient
organisations, and a rejection triggers re-ranking, escalation and, as a last resort, paid
recycling, so every donation ends in reuse or material recovery.

Background: [docs/ReLoop_Project_Context.pdf](docs/ReLoop_Project_Context.pdf) ·
Build brief: [PROMPT.md](PROMPT.md) · Decision log: [CLAUDE.md](CLAUDE.md)

## Status: Phase 3 (the React frontend)

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

**What does not exist yet.** Platform-arranged logistics, payments, wallets (the
recycling settlement is recorded but credits nothing), reviews, push and email
notifications. Anything not listed above is not built.

### Stubs and simulations

| Component | Status |
|---|---|
| **Geocoding** (`app/services/geocoding.py`) | **STUB.** `PassthroughGeocoder` returns the coordinates the client sends, unchanged and unverified. No address lookup takes place, and there is no maps API key. Endpoints therefore require `latitude`/`longitude`, and changing an address requires new coordinates. |
| **Image storage** (`app/services/storage.py`) | Local disk under `backend/uploads/` (git-ignored), behind an `ImageStorage` interface so object storage can replace it. Files are served only through an authorised endpoint. |
| **Recycling settlement** (`app/domain/recycling.py`) | **SIMULATED.** Mass is **estimated** as quantity × a per-category weight. The settlement (gross value, donor credit, platform fee) is recorded, but **no money moves**: Phase 4 wallets will credit from these records. Labelled `simulated` / `mass_is_estimate` in every API response. |
| **Per-category weights** (`CATEGORY_WEIGHT_KG`) | **PLACEHOLDERS** (clothes 0.5 kg, toys 0.3 kg, books 0.4 kg per item) pending a cited source. Responses carry `weights_are_placeholders: true`. |
| **Recycler confirmation** | **SIMULATED.** There is no recycler login. An admin confirms recycling on the recycler's behalf, with a recorded reason. |
| **Distances** | Haversine in Python over every organisation that accepts the category. No PostGIS. Fine at seed scale; revisit when the instant-pickup module needs fast geo-queries. |
| **Map tiles** (frontend) | OpenStreetMap's public tile servers, no API key. Their usage policy suits development and demos, not production traffic: a deployment needs a tile provider. Locations are the pins people drop; nothing is geocoded. |
| **Discovery map positions** | **APPROXIMATE.** Rounded to 2 decimal places of a degree before they leave the API (`positions_are_approximate`, `position_error_km`), and drawn as shaded areas, not pins. Matching uses the precise positions. |
| **Notifications** | In-app only, polled (`POLL_MS` in `frontend/src/config.ts`). **Push (Firebase Cloud Messaging) and email are deferred**, not built. Read/unread state is kept in each browser, so it does not follow you to another device. |

### Deferred (not built, by decision)

- **Verification-document uploads.** An admin verifies an organisation through
  `PATCH /admin/organisations/{id}/verification`. Documents are reviewed outside the
  platform for now.
- Rate limiting on donation creation, login and accept/reject.
- Explicit consent capture before storing an address (DPDP), and a retention policy.
- Rescheduling a handover, and recycler management endpoints (recyclers come from the
  seed or the database).
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
- **No profile editing in the UI.** Organisations can change their profile through
  `PATCH /organisations/me`, but the dashboard only shows it. Donors have no profile
  page.
- **Organisations see the donor's address, not their phone.** The API releases the
  pickup address on acceptance; contact beyond that happens at the handover.
- **The admin organisation list shows the first 25** for each filter, without paging.
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
                      action → endpoint map, role → home page
    i18n/             en.json (every user-facing string) and the t() helper
    styles/theme.css  design tokens: the one place to restyle
    ui/               shared, token-only components (buttons, cards, tags, forms, ...)
    components/       ReLoop components (timeline, action bar, maps, needs, ...)
    pages/            routes, built from ui/ and components/: auth/, donor/,
                      acceptor/, admin/, the landing page and the discovery map
  tests/              Vitest: API client, token refresh, no-literals guard, locale
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
npm test                            # API client, token refresh, no-literals guard, locale

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
