# 🔷 MASTER BUILD PROMPT — ReLoop

**(Full-stack generation — FastAPI + PostgreSQL + React)**

---

## 🎓 YOUR ROLE

You are a **lead full-stack engineer** building this product from scratch, with a
bias toward systems that are correct, inspectable and testable over systems that
merely demo well.

You own the architecture. I am the product owner, a final-year CS student, and I
will review every phase before you move to the next one. Push back on me when I am
wrong — if a requirement below is confused, over-engineered or would paint us into a
corner, say so before building it.

---

## 🧭 HOW WE WORK

Build in the phases below, **ONE PHASE AT A TIME**. For each phase:

1. First give a **short plan** — the files you'll create or change. Then build it.
2. **Write unit tests** for anything deterministic.
3. End with: **what you built**, the **exact commands to run it**, and an
   **acceptance test I can do by hand**.
4. Then **STOP** and wait for me to say **"next phase"**.
5. Update `CLAUDE.md` with any new decision, command or environment variable —
   **append to it, never rewrite it.** It is hand-maintained and carries decisions you
   did not make.

Do not run ahead. A reviewed Phase 1 beats an unreviewed Phase 5.

---

## 🧠 PROJECT

**ReLoop — Circular Donation & Redistribution Platform**

A location-aware platform connecting people who have reusable goods with
organisations that need them, built so that **no donation reaches a dead end**.

**Categories (MVP):** Clothes, Toys, Books. *(Food is explicitly out of scope for MVP —
it needs cold-chain and safety handling the platform does not model.)*

**Users:**
- 👤 **Donors** — individuals with surplus goods
- 🏢 **Acceptors** — NGOs, orphanages, schools, shelters, institutions
- 🛡️ **Admin** — platform operators

---

## 🏗️ TECH STACK

**Backend**
- FastAPI (Python 3.11+), async where it helps
- PostgreSQL 15+ with PostGIS *(optional but recommended for geo queries)*
- SQLAlchemy 2.x + Alembic migrations
- Pydantic v2 for schemas and validation
- JWT auth (access + refresh)
- Celery + Redis for background jobs and scheduled sweeps
- pytest

**Frontend**
- React 18 + Vite
- Tailwind CSS
- React Router
- Google Maps API (or Mapbox)
- Axios / TanStack Query

**Intelligence layer**
- Scikit-learn — ranking-weight calibration, acceptance-probability modelling
- TensorFlow — demand forecasting by category and region
- Design the ML as **pluggable services behind clean interfaces**, so the platform
  runs correctly with deterministic fallbacks before any model is trained

**Infra**
- `.env` driven config, no secrets in code
- Local Postgres and Redis however I'm already running them — a native install, a
  managed free tier, whatever. **Docker Compose is optional**: add a
  `docker-compose.yml` only when I ask, or when onboarding a second machine makes it
  worth it. Nothing in the code may assume a container — read every connection
  string from `.env`.

---

## 👥 ROLE-BASED ACCESS

Custom user model with a `role` field. Route-level dependencies enforce
Donor / Acceptor / Admin separately — not a single `is_staff` flag.

---

## 📦 CORE MODULES

### 1️⃣ Donor

- Register / login (JWT)
- Profile: name, phone, address (geocoded to lat/lng at signup), donation history, impact score
- **Create donation:**
  - Category, quantity, condition (New / Gently Used / Used)
  - Multiple image uploads
  - Pickup address, preferred time window
  - Optional note, optional **priority** flag
- After submission: system returns a **ranked list of suitable acceptors**.
  Donor can accept the top suggestion or choose another from a map view.
- Track every donation through its full lifecycle with a live status

### 2️⃣ Acceptor (NGO / Institution)

- Registration: organisation name, registration ID, verification documents,
  contact person, phone, email, geocoded address, pickup capability (Y/N),
  storage capacity, categories accepted
- **Needs list** — category, quantity needed, urgency level, active/inactive.
  This drives matching, so make it easy to keep current.
- Accept / reject incoming donation requests from a single queue
- Schedule pickups when self-handling
- Analytics: items received, impact generated, donor ratings
- Verified badge after admin approval (unverified orgs never enter matching)

### 3️⃣ Admin

Verify organisations, approve institutional accounts, view commission earnings and
platform-wide impact, flag abuse, suspend users, and — importantly — **see the queue
of donations that could not be routed anywhere**.

---

## 🗺️ MAP & DISCOVERY

Nearby acceptors on an interactive map, filterable by category accepted, distance and
urgency. Clicking an organisation shows its profile, current needs, pickup options,
ratings and distance from the donor.

---

## 🧮 MATCHING ENGINE

When a donation is created, score every **eligible** acceptor and return a ranked list.

**Hard filters first** (cheap, before scoring): verified, accepts this category,
has remaining capacity.

**Then score on:**
- Geographic proximity (haversine, or PostGIS distance)
- Match against the acceptor's current needs list
- Urgency of that need
- Remaining storage capacity
- Historical acceptance rate
- Rating

**Two multipliers that make this platform distinctive:**

1. **Priority boost** — donor-flagged urgent donations rank higher.
2. **Rejection boost** — *a donation's score rises each time it is declined*, so
   hard-to-place items gain visibility instead of sinking to the bottom of every
   queue. Capped so it cannot dominate the ranking.

The rejection boost is the interesting idea here. Treat it as a first-class feature,
make the magnitude and cap configurable, and expose a flag to disable it so its
effect can be measured.

**On weights:** start with sensible assigned values. Once accept/reject history
accumulates, calibrate them from observed outcomes — that is what the Scikit-learn
layer is for. Keep the score **inspectable**: a donor should be able to see *why*
an organisation was ranked first.

> 💡 **You have latitude here.** If a better formulation than a weighted sum fits
> the problem — learning-to-rank, bandit allocation, a fairness constraint to stop
> the same large NGO winning every match — propose it and explain the trade-off.

---

## 🔄 DONATION LIFECYCLE — THE CORE DIFFERENTIATOR

Most donation platforms stop at "listed". The whole point of ReLoop is what happens
**after** a recipient says no.

**States:**

```
LISTED → MATCHED → ACCEPTED → PICKUP_SCHEDULED → IN_TRANSIT → DELIVERED → COMPLETED
            ↓
       RE_MATCHING ⇄ MATCHED
            ↓
        ESCALATED
            ↓
    WASTE_REDIRECTED → RECYCLED
```

Plus `CANCELLED`.

**Rejection handling:**
- Record the rejection; add that organisation to the donation's exclusion list so it
  is never offered the same item twice
- Re-rank against remaining candidates (with the rejection boost applied)
- After a configurable number of rejections (default 3), **escalate to the donor** with
  three choices: re-match, upgrade to priority, or redirect to recycling
- A deadline sweeper (Celery beat) handles donations that simply time out

**Recycling fallback:**
- Select the nearest active waste-management partner that accepts the category
- Estimate mass from quantity × per-category weight
- Compute value from the partner's rate, split into a **donor credit** and a platform fee
- Credit the donor's wallet — donating is rewarded even when reuse fails

**Design requirement:** implement the lifecycle as an **explicit transition table**,
not scattered conditionals, and write a test asserting that every non-terminal state
has at least one outgoing transition. A donation that can enter a state it cannot
leave is the one bug that breaks the entire premise.

**If no recycler is reachable**, the donation must surface in the admin queue — never
fail silently.

---

## 🚚 LOGISTICS

Three paths, donor chooses:

1. **Platform-arranged pickup** — simulate third-party booking (Porter / Rapido / Uber
   style). Compute distance and estimated cost, create a booking record, take
   simulated payment, advance status: Scheduled → Picked Up → Delivered.
   Add an 8–12% platform fee, stored in a Commission table.
   Build a `LogisticsProvider` model (name, endpoint, commission %, status) so real
   APIs can slot in later without a rewrite.
2. **Acceptor self-scheduled pickup** — acceptor accepts, picks a slot, updates status.
3. **Donor drop-off** — marked Self Delivered.

Include an **AI pickup scheduler**: suggest an optimal slot from the donor's preferred
window, acceptor availability, and (mock) traffic/travel-time estimation.

---

## 💳 PAYMENTS (SIMULATED)

`Payment` model: user, donation, amount, logistics cost, platform commission,
status, simulated transaction ID. Razorpay-style mock checkout with auto-success.
Clearly a simulation — label it in the UI, don't dress it up as a live gateway.

---

## 📊 IMPACT & GAMIFICATION

Per donation, compute: approximate mass diverted from landfill, estimated carbon
offset, impact points. Store in an `ImpactMetrics` table.

Dashboards show total items donated, waste diverted, carbon saved, beneficiaries
reached, completion rate, and an impact-level badge (Bronze → Silver → Gold → Platinum).

Leaderboards for top donors, top contributing organisations, top cities.

⚠️ **Define per-category weights and the carbon factor in exactly ONE module** and
import everywhere. A previous build had books at 0.8 kg in one code path and 0.4 kg
in another, so the same donation produced different numbers depending on which path
ran. Add a test pinning this to a single source of truth.

These figures are **estimates** — label them as such in the UI.

---

## 🏢 CORPORATE / SCHOOL DRIVES

Special account type: bulk donation entry, scheduled donation drives, invite
employees or students to contribute to a drive, CSR impact dashboard, downloadable
PDF reports, public recognition badge.

---

## 🔔 NOTIFICATIONS

Firebase Cloud Messaging for push, plus email fallback. Notify on: match found,
accepted, rejected, pickup scheduled, in transit, delivered, escalation needing a
donor decision.

---

## 🗂️ DATA MODEL (core)

```
User                 custom, with role
OrganizationProfile  verification status, capacity, categories, pickup capability
CurrentNeed          per-organisation needs list with urgency
Donation             + status, exclusion list, rejection_count, priority flag, deadline
DonationImage
Match                one row per candidate offered — score, rank, response, timestamp
PickupRequest
LogisticsProvider
Payment
Commission
ImpactMetrics
WasteCollector       recycling partners, rates, accepted categories
DriveEvent
Review
Wallet / WalletTxn
```

⚠️ **Never delete a `Match` row, including rejections.** The accept/reject history is
what trains the acceptance model, calibrates the ranking weights, and feeds demand
forecasting. It is the most valuable data the platform produces.

---

## 🔐 SECURITY & VALIDATION

JWT with refresh, role-based route protection, image type and size validation,
rate limiting, an audit log of status transitions, and input sanitisation.

Treat donor addresses as **sensitive** — acceptor staff can see them. Think about who
sees what, and when.

---

## 🎨 UI

Modern, clean, sustainability theme — green tones and earth neutrals. Responsive.

**Pages:** landing, role selection, donor dashboard, acceptor dashboard, map view,
three-step donation creation flow, ranked acceptor selection, donation detail with
status timeline, admin panel, leaderboard, drive pages.

Status should be instantly readable — colour-coded tags across both dashboards.

---

## 🚀 BUILD PHASES

**Phase 0 — Skeleton** *(~15 minutes, no application code)*
`backend/` and `frontend/` package structure, `.gitignore`, README with pinned Python
and Node versions, `.env` + `.env.example` with just `DATABASE_URL` and `SECRET_KEY`,
pytest green on one trivial test, and Postgres answering a `SELECT 1` from Python.

**Already done by hand before the first session — do not create or overwrite these:**
the repo itself, `CLAUDE.md`, `PROMPT.md`, and `docs/`. Check what's present before
creating anything.

That's the whole phase. Don't provision maps keys, Firebase, Redis or the frontend
toolchain here — each arrives in the phase that first calls it, and the first thing
built against it is the call that proves it works. Likewise, `.env.example` gains a
variable the moment code reads it and not before: a speculative env file is stale within
a week and then lies about what the project needs.

**Phase 1 — Foundation**
Scaffold, models + migrations, auth with roles, donation CRUD, organisation
registration and needs list.

**Phase 2 — The core loop**
Matching engine with scoring, lifecycle state machine with the transition test,
rejection handling and re-matching, recycling fallback, deadline sweeper.

**Phase 3 — Experience**
React frontend, map discovery, dashboards, status tracking, notifications.

**Phase 4 — Logistics & money**
Three pickup paths, simulated payments, commission tracking, wallet.

**Phase 5 — Scale & intelligence**
Impact analytics, leaderboards, corporate drives, weight calibration from real
history, demand forecasting, admin tooling.

Get Phase 2 right before touching the frontend. The matching and lifecycle logic is
the product; everything else is presentation.

---

## 🧩 ENGINEERING STANDARDS

- Clean modular structure, one concern per module
- Scoring logic as **pure functions**, decoupled from the DB, so it is unit-testable
  and reusable in a simulation harness
- Tests for the scoring function and the state machine before any UI work
- Seed data: realistic Bengaluru coordinates for organisations and recyclers
- Config over hardcoding — weights, caps, thresholds, fee percentages all in config
- **If a component is a stub, say so in the code, the comments and the README.**
  No TODO dressed up as a shipped feature.

---

## 🔬 OPTIONAL BUT VALUABLE: SIMULATION HARNESS

A `sim/` package that runs synthetic donations and organisations through the **real**
scoring and lifecycle code (not a reimplementation) and reports: fraction
redistributed vs. recycled vs. abandoned, mean offers before acceptance, mean
distance travelled, load fairness across organisations, completion rate, response
time under concurrency.

Compare: random assignment / nearest-only / score without re-matching / full ReLoop /
full ReLoop with rejection boost.

This turns design claims into measured ones and is the fastest route to knowing
whether the rejection boost actually helps.

---

## 📈 FUTURE MODULES (architect for, don't build now)

ReLoop is a **core loop plus modules**. More are coming, and the test for the
architecture is simple: *could a module be added without editing the transition table
or the scoring function?* If not, that's worth fixing now rather than during.

Two are near-certain and shape decisions today:

**🏪 Thrift store** — items nobody needs for free but that have resale value get listed
for sale instead of recycled. This adds a **third terminal state** (`SOLD`), so build
the lifecycle to accept new terminal states without rework. It also needs listing
price, condition grade and inventory fields on `Donation`, and it reuses
`Payment` / `Commission` / `Wallet` — so keep those general rather than
logistics-specific.

**⚡ Instant pickup** — on-demand collection instead of a scheduled window, dispatching
the nearest available courier or volunteer live. This is the strongest argument for
**PostGIS** and for pushing status over websockets rather than polling. Keep *dispatch*
separate from *matching*: they look alike and are different problems.

Also planned: volunteer pickup network · food module with cold-chain handling (keep
category rules in config, not branches) · real logistics APIs · carbon-credit and CSR
reporting (which is why impact is stored **per donation**, not just aggregated) ·
image-based condition verification · multilingual Kannada/Hindi (externalise every
user-facing string from day one) · native mobile apps (no business logic in the React
layer — the API stays the only source of truth).

Append-only auditability is wanted; a `StatusEvent` table gives it without a blockchain.

---

## 💎 CREATIVE LATITUDE

This spec describes **what the platform should do**, not how you must build it.

You are expected to improve on it. If you see a better architecture, a stronger
matching formulation, a feature that would clearly strengthen the product, or a
simpler path to the same outcome — **propose it, explain the trade-off, and build the
better version.** Flag anything here that seems wrong or over-engineered.

What matters: the closed loop actually closes, the code is clean and tested, and
nothing claims to work that doesn't.

---

## 🎯 START HERE

Begin with **Phase 0 only**: `backend/` and `frontend/` structure, `.gitignore`, README,
`.env` + `.env.example`, pytest with one passing test, and a Postgres connection check.
`CLAUDE.md`, `PROMPT.md` and `docs/` already exist — leave them alone. Keep it to
fifteen minutes: no models, no endpoints, no UI, no services we don't call yet.

Follow **🧭 HOW WE WORK** above: short plan first, then build, then tests, then tell
me how to run it and how to verify it by hand — then stop.

Don't generate the whole platform in one pass. Build it in reviewable increments,
and tell me what you'd do differently as you go.
