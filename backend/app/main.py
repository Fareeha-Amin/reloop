"""FastAPI application. Run with: uvicorn app.main:app --reload (from backend/)."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.constants import SWEEP_INTERVAL
from app.routers import admin, auth, donations, notifications, offers, organizations
from app.services import sweeper
from app.services.errors import ServiceError
from app.services.geocoding import GeocodingUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs the deadline sweeper in-process every SWEEP_INTERVAL, unless SWEEPER_ENABLED
    is false. Shutdown waits for a sweep in progress to finish."""
    stop = asyncio.Event()
    task = None
    if get_settings().sweeper_enabled:
        task = asyncio.create_task(
            sweeper.run_periodically(SWEEP_INTERVAL.total_seconds(), sweeper.sweep_now, stop)
        )
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            await task


app = FastAPI(
    lifespan=lifespan,
    title="ReLoop API",
    version="0.3.0-phase3",
    description=(
        "The core loop: explainable matching, the full donation lifecycle, "
        "rejection handling, escalation, a recycling fallback and the deadline sweeper "
        f"(in-process every {SWEEP_INTERVAL.total_seconds() / 60:g} minutes; POST /admin/sweep "
        "runs it now). Phase 3 adds an in-app notification feed (polled; no push or email). "
        "**Stubs and simulations:** geocoding is a stub (coordinates are accepted as "
        "supplied); recycling settlements are **simulated** over **estimated** mass "
        "(per-category weights are placeholders), and an admin confirms recycling on the "
        "recycler's behalf. No money moves."
    ),
)


@app.exception_handler(ServiceError)
def handle_service_error(request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(GeocodingUnavailable)
def handle_geocoding_unavailable(request: Request, exc: GeocodingUnavailable) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(offers.router)
app.include_router(donations.router)
app.include_router(admin.router)
app.include_router(notifications.router)


def _mark_binary_strings(node) -> None:
    """FastAPI describes uploaded files with the OpenAPI 3.1 `contentMediaType`, but
    Swagger UI only draws a file picker for arrays of files when it also sees
    `format: binary`. Docs-only: validation does not use the OpenAPI document."""
    if isinstance(node, dict):
        if node.get("type") == "string" and node.get("contentMediaType") == "application/octet-stream":
            node.setdefault("format", "binary")
        for value in node.values():
            _mark_binary_strings(value)
    elif isinstance(node, list):
        for value in node:
            _mark_binary_strings(value)


_default_openapi = app.openapi


def _openapi_with_file_pickers() -> dict:
    schema = _default_openapi()  # built once, then cached by FastAPI
    _mark_binary_strings(schema)  # idempotent
    return schema


app.openapi = _openapi_with_file_pickers


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
