"""Route-level role enforcement: every protected route, called by every role.

The expected status for a forbidden role is 403 (the role check runs before the body is
looked at). Allowed roles get anything except 401/403 — the business result is tested
elsewhere.
"""

import uuid

import pytest

from tests.api import helpers as h

ANY_ID = str(uuid.uuid4())

# (method, path, allowed roles)
ROUTES = [
    ("GET", "/auth/me", {"DONOR", "ACCEPTOR", "ADMIN"}),
    ("GET", "/organisations/me", {"ACCEPTOR"}),
    ("PATCH", "/organisations/me", {"ACCEPTOR"}),
    ("GET", "/organisations/me/needs", {"ACCEPTOR"}),
    ("POST", "/organisations/me/needs", {"ACCEPTOR"}),
    ("PATCH", f"/organisations/me/needs/{ANY_ID}", {"ACCEPTOR"}),
    ("POST", "/donations", {"DONOR"}),
    ("GET", "/donations", {"DONOR"}),
    ("GET", f"/donations/{ANY_ID}", {"DONOR", "ADMIN"}),
    ("PATCH", f"/donations/{ANY_ID}", {"DONOR"}),
    ("POST", f"/donations/{ANY_ID}/cancel", {"DONOR"}),
    ("POST", f"/donations/{ANY_ID}/images", {"DONOR"}),
    ("GET", f"/donations/{ANY_ID}/images/{ANY_ID}", {"DONOR", "ADMIN"}),
    ("DELETE", f"/donations/{ANY_ID}/images/{ANY_ID}", {"DONOR"}),
    ("GET", "/admin/organisations", {"ADMIN"}),
    ("GET", f"/admin/organisations/{ANY_ID}", {"ADMIN"}),
    ("PATCH", f"/admin/organisations/{ANY_ID}/verification", {"ADMIN"}),
    ("GET", "/admin/donations", {"ADMIN"}),
]


@pytest.fixture
def role_headers(client, db):
    acceptor_headers, _ = h.acceptor(client)
    return {
        "DONOR": h.donor(client),
        "ACCEPTOR": acceptor_headers,
        "ADMIN": h.admin(client, db),
    }


@pytest.mark.parametrize(("method", "path", "allowed"), ROUTES, ids=[f"{m} {p}" for m, p, _ in ROUTES])
def test_role_matrix(client, role_headers, method, path, allowed):
    for role, headers in role_headers.items():
        resp = client.request(method, path, headers=headers, json={})
        if role in allowed:
            assert resp.status_code not in (401, 403), f"{role} wrongly refused: {resp.text}"
        else:
            assert resp.status_code == 403, f"{role} should be forbidden, got {resp.status_code}"


@pytest.mark.parametrize(("method", "path", "allowed"), ROUTES, ids=[f"{m} {p}" for m, p, _ in ROUTES])
def test_every_protected_route_requires_a_token(client, method, path, allowed):
    assert client.request(method, path, json={}).status_code == 401
