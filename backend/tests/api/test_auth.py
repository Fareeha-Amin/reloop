from tests.api import helpers as h


def test_register_donor_and_login(client):
    resp = client.post(
        "/auth/register/donor",
        json={"email": "Asha@Example.org", "password": h.PASSWORD, "full_name": "Asha", "phone": "+91 98450 00000"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["role"] == "DONOR"
    assert body["email"] == "asha@example.org"
    assert "password" not in str(body)

    tokens = h.login(client, "ASHA@example.org")  # email is case-insensitive
    me = client.get("/auth/me", headers=h.auth(tokens))
    assert me.status_code == 200
    assert me.json()["email"] == "asha@example.org"


def test_duplicate_email_conflicts_case_insensitively(client):
    payload = {"email": "dup@example.org", "password": h.PASSWORD, "full_name": "A", "phone": "+91 98450 00000"}
    assert client.post("/auth/register/donor", json=payload).status_code == 201
    payload["email"] = "DUP@example.org"
    assert client.post("/auth/register/donor", json=payload).status_code == 409


def test_wrong_password_and_unknown_email_look_the_same(client):
    client.post(
        "/auth/register/donor",
        json={"email": "known@example.org", "password": h.PASSWORD, "full_name": "K", "phone": "+91 98450 00000"},
    )
    known = client.post("/auth/login", data={"username": "known@example.org", "password": "wrong-password"})
    unknown = client.post("/auth/login", data={"username": "nobody@example.org", "password": "wrong-password"})
    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()


def test_short_password_rejected(client):
    resp = client.post(
        "/auth/register/donor",
        json={"email": "s@example.org", "password": "short", "full_name": "S", "phone": "+91 98450 00000"},
    )
    assert resp.status_code == 422


def test_role_cannot_be_chosen_at_registration(client):
    resp = client.post(
        "/auth/register/donor",
        json={
            "email": "sneaky@example.org",
            "password": h.PASSWORD,
            "full_name": "S",
            "phone": "+91 98450 00000",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 422


def test_there_is_no_admin_registration_endpoint(client):
    assert client.post("/auth/register/admin", json={}).status_code == 404


def test_refresh_issues_a_working_access_token(client):
    email = "refresh@example.org"
    client.post(
        "/auth/register/donor",
        json={"email": email, "password": h.PASSWORD, "full_name": "R", "phone": "+91 98450 00000"},
    )
    tokens = h.login(client, email)
    resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert "refresh_token" not in resp.json()
    assert client.get("/auth/me", headers=h.auth(resp.json())).status_code == 200


def test_access_token_cannot_be_used_to_refresh(client):
    email = "swap@example.org"
    client.post(
        "/auth/register/donor",
        json={"email": email, "password": h.PASSWORD, "full_name": "S", "phone": "+91 98450 00000"},
    )
    tokens = h.login(client, email)
    assert client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401
    # ...and a refresh token cannot be used as an access token.
    headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_missing_or_garbage_token_is_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401
