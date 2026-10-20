import io

from PIL import Image

from app.constants import IMAGE_MAX_BYTES, IMAGES_PER_DONATION_MAX
from tests.api import helpers as h

GPS_IFD = 0x8825


def _upload(client, headers, donation_id, *files):
    return client.post(
        f"/donations/{donation_id}/images",
        headers=headers,
        files=[("files", f) for f in files],
    )


def _jpeg_with_gps() -> bytes:
    exif = Image.Exif()
    exif[GPS_IFD] = {1: "N", 2: (12.0, 58.0, 17.0), 3: "E", 4: (77.0, 35.0, 40.0)}
    return h.image_bytes("JPEG", exif=exif)


def test_upload_read_back_and_gps_is_gone(client, storage, db):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    resp = _upload(client, headers, donation["id"], ("photo.jpg", _jpeg_with_gps(), "image/jpeg"))
    assert resp.status_code == 201, resp.text
    [image] = resp.json()
    assert image["content_type"] == "image/jpeg"

    got = client.get(f"/donations/{donation['id']}/images/{image['id']}", headers=headers)
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/jpeg"
    assert "no-store" in got.headers["cache-control"]
    assert len(Image.open(io.BytesIO(got.content)).getexif()) == 0

    # Admin can read it too; the donation lists it.
    assert client.get(f"/donations/{donation['id']}/images/{image['id']}", headers=h.admin(client, db)).status_code == 200
    listed = client.get(f"/donations/{donation['id']}", headers=headers).json()["images"]
    assert [i["id"] for i in listed] == [image["id"]]


def test_claimed_content_type_is_ignored(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    resp = _upload(client, headers, donation["id"], ("evil.jpg", b"<script>alert(1)</script>", "image/jpeg"))
    assert resp.status_code == 422
    assert "evil.jpg" in resp.json()["detail"]


def test_oversized_upload_rejected(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    resp = _upload(client, headers, donation["id"], ("big.jpg", b"\xff" * (IMAGE_MAX_BYTES + 10), "image/jpeg"))
    assert resp.status_code == 422
    assert "larger than" in resp.json()["detail"]


def test_one_bad_file_means_nothing_is_stored(client, storage):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    resp = _upload(
        client,
        headers,
        donation["id"],
        ("good.png", h.image_bytes("PNG"), "image/png"),
        ("bad.gif", h.image_bytes("GIF"), "image/gif"),
    )
    assert resp.status_code == 422
    assert client.get(f"/donations/{donation['id']}", headers=headers).json()["images"] == []
    assert not storage.root.exists() or not any(storage.root.iterdir())


def test_image_count_is_capped(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    files = [(f"{i}.png", h.image_bytes("PNG"), "image/png") for i in range(IMAGES_PER_DONATION_MAX)]
    assert _upload(client, headers, donation["id"], *files).status_code == 201
    resp = _upload(client, headers, donation["id"], ("one-more.png", h.image_bytes("PNG"), "image/png"))
    assert resp.status_code == 409


def test_other_donor_cannot_see_upload_or_delete(client):
    owner, other = h.donor(client), h.donor(client)
    donation = h.create_donation(client, owner)
    [image] = _upload(client, owner, donation["id"], ("p.png", h.image_bytes("PNG"), "image/png")).json()
    path = f"/donations/{donation['id']}/images/{image['id']}"
    assert client.get(path, headers=other).status_code == 404
    assert client.delete(path, headers=other).status_code == 404
    assert _upload(client, other, donation["id"], ("p.png", h.image_bytes("PNG"), "image/png")).status_code == 404


def test_delete_image_removes_row_and_file(client, storage):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    [image] = _upload(client, headers, donation["id"], ("p.png", h.image_bytes("PNG"), "image/png")).json()
    assert len(list(storage.root.iterdir())) == 1

    path = f"/donations/{donation['id']}/images/{image['id']}"
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 404
    assert list(storage.root.iterdir()) == []


def test_images_frozen_after_cancel(client):
    headers = h.donor(client)
    donation = h.create_donation(client, headers)
    [image] = _upload(client, headers, donation["id"], ("p.png", h.image_bytes("PNG"), "image/png")).json()
    client.post(f"/donations/{donation['id']}/cancel", headers=headers)

    assert _upload(client, headers, donation["id"], ("q.png", h.image_bytes("PNG"), "image/png")).status_code == 409
    path = f"/donations/{donation['id']}/images/{image['id']}"
    assert client.delete(path, headers=headers).status_code == 409
    assert client.get(path, headers=headers).status_code == 200  # still readable
