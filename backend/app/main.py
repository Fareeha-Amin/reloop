"""FastAPI application. Run with: uvicorn app.main:app --reload (from backend/)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import admin, auth, donations, organizations
from app.services.errors import ServiceError
from app.services.geocoding import GeocodingUnavailable

app = FastAPI(
    title="ReLoop API",
    version="0.1.0-phase1",
    description=(
        "Phase 1 — foundation: auth with roles, donation CRUD with images, organisation "
        "registration and needs list. **Geocoding is a stub**: coordinates are accepted "
        "as supplied, not looked up. Matching and the full lifecycle arrive in Phase 2."
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
app.include_router(donations.router)
app.include_router(admin.router)


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
