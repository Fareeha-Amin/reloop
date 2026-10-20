# ReLoop

Circular donation & redistribution platform: donors are matched to verified recipient
organisations, and a rejection triggers re-ranking, escalation and, as a last resort, paid
recycling, so every donation ends in reuse or material recovery.

Background: [docs/ReLoop_Project_Context.pdf](docs/ReLoop_Project_Context.pdf) ·
Build brief: [PROMPT.md](PROMPT.md) · Decision log: [CLAUDE.md](CLAUDE.md)

## Status: Phase 1 (foundation)

**What exists**

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
- Donation CRUD. Donors can edit while `LISTED` and cancel (the donation is kept as
  `CANCELLED`, never deleted). A donation is readable only by its donor and by admins.
- Donation image upload, read and delete. Images are validated server-side and
  re-encoded, which strips EXIF (including GPS) and other metadata.
- A pure lifecycle module with an explicit transition table. Phase 1 has one edge:
  `LISTED → CANCELLED`.
- Alembic migrations, plus tests covering unit logic, the API, role enforcement and
  migrations.

**What does not exist yet.** No matching or ranking, no Match / StatusEvent / Wallet /
Payment tables, no outcome states (`COMPLETED`, `RECYCLED`), no recycling fallback, no
frontend. Anything not listed under "What exists" is not built.

### Known gap: the loop is not closed yet

In Phase 1 a donation that the donor does not cancel stays `LISTED`. The outcome
states arrive with matching in Phase 2. The test
`test_every_non_terminal_state_can_reach_an_outcome` is a strict xfail that records this
gap. Once Phase 2 closes the loop the test starts failing the run, and the marker must
be removed.

### Stubs

| Component | Status |
|---|---|
| **Geocoding** (`app/services/geocoding.py`) | **STUB.** `PassthroughGeocoder` returns the coordinates the client sends, unchanged and unverified. No address lookup takes place, and there is no maps API key. Endpoints therefore require `latitude`/`longitude`, and changing an address requires new coordinates. |
| **Image storage** (`app/services/storage.py`) | Local disk under `backend/uploads/` (git-ignored), behind an `ImageStorage` interface so object storage can replace it. Files are served only through an authorised endpoint. |

### Deferred (not built, by decision)

- **Verification-document uploads.** An admin verifies an organisation through
  `PATCH /admin/organisations/{id}/verification`. Documents are reviewed outside the
  platform for now.
- Rate limiting on donation creation and login.
- Explicit consent capture before storing an address (DPDP), and a retention policy.
- Logging of precise-address release. Admins can see a donation's precise pickup
  address in Phase 1, and that access is not logged. Logged release to acceptors
  arrives with acceptance in Phase 2.
- Capacity bookkeeping. `storage_capacity` is recorded but nothing decrements it.

### Known limitations

- **JWTs are stateless and cannot be revoked.** There is no server-side session and no
  deny-list. An access token stays valid for its 30 minutes and a refresh token for its
  7 days, even after a password change. Refreshing issues a new access token only; it
  does not extend the refresh token, so a session ends when its refresh token expires.
- **Tokens contain only the user id.** The role is read from the database on every
  request, so a role change takes effect immediately.

### Units

`Donation.quantity`, `OrganizationProfile.storage_capacity` and
`CurrentNeed.quantity_needed` are all **counts of items** (e.g. 12 shirts), never
kilograms or bags.

## Pinned versions

| Tool | Version |
|---|---|
| Python | **3.12** |
| Node | **22 LTS** (not used until Phase 3) |
| PostgreSQL | **15+** (developed against 17) |

## Layout

```
backend/
  app/
    constants.py      every vocabulary and tunable, defined once
    config.py         environment variables, read once
    domain/           pure logic (lifecycle transition table)
    models/           SQLAlchemy models
    schemas/          Pydantic request/response models
    security/         passwords, JWTs, role dependencies
    services/         database operations, geocoding stub, storage, image processing
    routers/          HTTP endpoints
    cli.py            operator commands (create-admin)
  alembic/            migrations
  tests/              unit/, api/, test_migrations.py
frontend/   React app (Phase 3); empty for now
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

# 4. Schema and first admin
alembic upgrade head
python -m app.cli create-admin --email admin@example.org --name "Platform Admin"

# 5. Run
uvicorn app.main:app --reload       # http://127.0.0.1:8000/docs
pytest                              # DB tests are skipped if TEST_DATABASE_URL is unset
```

On macOS/Linux, use `python3.12 -m venv .venv && source .venv/bin/activate`.

Postgres can be a native install or a managed tier (Neon, Supabase). Every connection
detail comes from `.env`. Nothing assumes a container.
