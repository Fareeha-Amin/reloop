# ReLoop

Circular donation & redistribution platform: donors are matched to verified recipient
organisations, and a rejection triggers re-ranking, escalation and, as a last resort, paid
recycling, so every donation ends in reuse or material recovery.

Background: [docs/ReLoop_Project_Context.pdf](docs/ReLoop_Project_Context.pdf) ·
Build brief: [PROMPT.md](PROMPT.md) · Decision log: [CLAUDE.md](CLAUDE.md)

## Status: Phase 0 (skeleton)

**What exists:** repo structure, config loading, a database connectivity check, pytest.
**What does not exist yet:** no API, no models, no matching, no lifecycle, no frontend.
Anything not listed under "What exists" is not built.

## Pinned versions

| Tool | Version |
|---|---|
| Python | **3.12** |
| Node | **22 LTS** (not used until Phase 3) |
| PostgreSQL | **15+** (developed against 17) |

## Layout

```
backend/    FastAPI service (Phase 1+); today: config + DB check + tests
frontend/   React app (Phase 3); empty for now
docs/       project context document
```

## Setup (Windows / PowerShell)

```powershell
# 1. Environment
Copy-Item .env.example .env        # then edit DATABASE_URL and SECRET_KEY

# 2. Python env
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Verify
pytest                              # unit tests, no database needed
python -m app.db_check              # SELECT 1 against DATABASE_URL
```

On macOS/Linux, use `python3.12 -m venv .venv && source .venv/bin/activate`.

Postgres can be a native install or a managed tier (Neon, Supabase). Every connection
detail comes from `.env`. Nothing assumes a container.
