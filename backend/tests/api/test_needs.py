from tests.api import helpers as h


def _need(client, headers, category="CLOTHES", quantity=20, urgency="MEDIUM"):
    return client.post(
        "/organisations/me/needs",
        headers=headers,
        json={"category": category, "quantity_needed": quantity, "urgency": urgency},
    )


def test_create_and_list_needs(client):
    headers, _ = h.acceptor(client)
    resp = _need(client, headers, "CLOTHES", 20, "HIGH")
    assert resp.status_code == 201, resp.text
    need = resp.json()
    assert (need["category"], need["quantity_needed"], need["urgency"], need["is_active"]) == (
        "CLOTHES",
        20,
        "HIGH",
        True,
    )
    listed = client.get("/organisations/me/needs", headers=headers).json()
    assert [n["id"] for n in listed] == [need["id"]]


def test_need_category_must_be_accepted_by_the_organisation(client):
    headers, _ = h.acceptor(client, categories_accepted=["BOOKS"])
    assert _need(client, headers, "TOYS").status_code == 409


def test_only_one_active_need_per_category(client):
    headers, _ = h.acceptor(client)
    first = _need(client, headers, "CLOTHES").json()
    assert _need(client, headers, "CLOTHES").status_code == 409

    # Deactivate, then a new one is allowed; reactivating the old one is not.
    resp = client.patch(f"/organisations/me/needs/{first['id']}", headers=headers, json={"is_active": False})
    assert resp.status_code == 200
    assert _need(client, headers, "CLOTHES").status_code == 201
    resp = client.patch(f"/organisations/me/needs/{first['id']}", headers=headers, json={"is_active": True})
    assert resp.status_code == 409


def test_deactivated_needs_are_kept_not_deleted(client):
    headers, _ = h.acceptor(client)
    need = _need(client, headers).json()
    client.patch(f"/organisations/me/needs/{need['id']}", headers=headers, json={"is_active": False})

    everything = client.get("/organisations/me/needs", headers=headers).json()
    active = client.get("/organisations/me/needs?active_only=true", headers=headers).json()
    assert [n["id"] for n in everything] == [need["id"]]
    assert active == []
    # There is no delete route.
    assert client.delete(f"/organisations/me/needs/{need['id']}", headers=headers).status_code == 405


def test_update_quantity_and_urgency(client):
    headers, _ = h.acceptor(client)
    need = _need(client, headers).json()
    resp = client.patch(
        f"/organisations/me/needs/{need['id']}",
        headers=headers,
        json={"quantity_needed": 5, "urgency": "LOW"},
    )
    assert (resp.json()["quantity_needed"], resp.json()["urgency"]) == (5, "LOW")


def test_category_of_a_need_cannot_change(client):
    headers, _ = h.acceptor(client)
    need = _need(client, headers).json()
    resp = client.patch(f"/organisations/me/needs/{need['id']}", headers=headers, json={"category": "BOOKS"})
    assert resp.status_code == 422


def test_cannot_touch_another_organisations_need(client):
    headers_a, _ = h.acceptor(client)
    headers_b, _ = h.acceptor(client)
    need = _need(client, headers_a).json()
    resp = client.patch(f"/organisations/me/needs/{need['id']}", headers=headers_b, json={"quantity_needed": 1})
    assert resp.status_code == 404


def test_unverified_organisation_can_maintain_needs(client):
    headers, body = h.acceptor(client)
    assert body["organization"]["verification_status"] == "PENDING"
    assert _need(client, headers).status_code == 201
