import pytest

from app.services.geocoding import GeocodingUnavailable, PassthroughGeocoder, get_geocoder
from app.services.storage import LocalImageStorage, StorageKeyInvalid


def test_storage_round_trip(tmp_path):
    storage = LocalImageStorage(tmp_path)
    key = storage.save(b"pixels", "jpg")
    assert key.endswith(".jpg")
    assert storage.read(key) == b"pixels"
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.read(key)


def test_storage_keys_are_random_and_unguessable(tmp_path):
    storage = LocalImageStorage(tmp_path)
    keys = {storage.save(b"x", "png") for _ in range(20)}
    assert len(keys) == 20
    assert all(len(k.split(".")[0]) >= 32 for k in keys)


@pytest.mark.parametrize("key", ["../../etc/passwd", "..\\secret.jpg", "a.jpg", "/abs/path.jpg", ""])
def test_storage_rejects_keys_that_could_escape_the_root(tmp_path, key):
    with pytest.raises(StorageKeyInvalid):
        LocalImageStorage(tmp_path).read(key)


def test_delete_missing_file_is_a_no_op(tmp_path):
    LocalImageStorage(tmp_path).delete("A" * 43 + ".jpg")


def test_geocoder_is_the_labelled_stub():
    geocoder = get_geocoder()
    assert isinstance(geocoder, PassthroughGeocoder)
    assert geocoder.is_stub is True


def test_passthrough_returns_coordinates_unchanged():
    loc = PassthroughGeocoder().resolve("12 MG Road", 12.9716, 77.5946)
    assert (loc.address_text, loc.latitude, loc.longitude) == ("12 MG Road", 12.9716, 77.5946)


def test_passthrough_refuses_to_invent_coordinates():
    with pytest.raises(GeocodingUnavailable, match="stub"):
        PassthroughGeocoder().resolve("12 MG Road", None, None)
