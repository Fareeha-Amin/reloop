"""Pydantic v2 request/response schemas. Input schemas forbid unknown fields, so an
attempt to set something read-only (status, name after registration, ...) is a 422
rather than being silently ignored."""
