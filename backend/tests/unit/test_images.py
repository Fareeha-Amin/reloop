import io
import warnings

import pytest
from PIL import Image

from app.constants import IMAGE_MAX_BYTES
from app.services import images
from app.services.images import ImageRejected, process_upload

GPS_IFD = 0x8825


def make_image(fmt="JPEG", size=(40, 30), mode="RGB", **save_kwargs) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, "red" if mode != "RGBA" else (255, 0, 0, 128)).save(
        buf, format=fmt, **save_kwargs
    )
    return buf.getvalue()


def exif_with_gps() -> Image.Exif:
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # Make
    exif[0x0112] = 1  # Orientation
    exif[GPS_IFD] = {1: "N", 2: (12.0, 58.0, 17.0), 3: "E", 4: (77.0, 35.0, 40.0)}
    return exif


@pytest.mark.parametrize(
    ("fmt", "content_type", "extension"),
    [("JPEG", "image/jpeg", "jpg"), ("PNG", "image/png", "png"), ("WEBP", "image/webp", "webp")],
)
def test_allowed_formats_are_accepted(fmt, content_type, extension):
    result = process_upload(make_image(fmt))
    assert (result.content_type, result.extension) == (content_type, extension)
    assert (result.width, result.height) == (40, 30)
    assert Image.open(io.BytesIO(result.data)).format == fmt


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP", "PNG"])
def test_exif_including_gps_is_stripped(fmt):
    raw = make_image(fmt, exif=exif_with_gps())
    assert Image.open(io.BytesIO(raw)).getexif().get(GPS_IFD) is not None  # precondition

    out = Image.open(io.BytesIO(process_upload(raw).data))
    assert len(out.getexif()) == 0
    assert "exif" not in out.info


def test_png_text_chunks_are_stripped():
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_text("Comment", "home address: 45 Indiranagar")
    out = Image.open(io.BytesIO(process_upload(make_image("PNG", pnginfo=info)).data))
    assert "Comment" not in out.info


def test_exif_orientation_is_applied_before_stripping():
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° clockwise on display
    result = process_upload(make_image("JPEG", size=(40, 30), exif=exif))
    assert (result.width, result.height) == (30, 40)


def test_transparency_is_kept_for_png():
    out = Image.open(io.BytesIO(process_upload(make_image("PNG", mode="RGBA")).data))
    assert out.mode == "RGBA"


@pytest.mark.parametrize("fmt", ["GIF", "BMP", "TIFF"])
def test_other_image_formats_are_rejected(fmt):
    with pytest.raises(ImageRejected, match="Unsupported"):
        process_upload(make_image(fmt))


def test_non_image_is_rejected_regardless_of_claimed_type():
    with pytest.raises(ImageRejected, match="not a readable image"):
        process_upload(b"%PDF-1.7 definitely not a photo")


def test_truncated_image_is_rejected():
    with pytest.raises(ImageRejected):
        process_upload(make_image("PNG", size=(200, 200))[:120])


def test_empty_file_is_rejected():
    with pytest.raises(ImageRejected, match="empty"):
        process_upload(b"")


def test_oversized_file_is_rejected():
    with pytest.raises(ImageRejected, match="larger than"):
        process_upload(b"\xff" * (IMAGE_MAX_BYTES + 1))


def test_too_many_pixels_is_rejected():
    with pytest.raises(ImageRejected, match="too large"):
        process_upload(make_image("PNG", size=(20, 20)), max_pixels=399)


def test_decompression_bomb_warning_is_a_rejection(monkeypatch):
    # 15x15 = 225 px: over Pillow's warning threshold (200) but under its error
    # threshold (400). Pillow would only warn; we must reject.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 200)
    with pytest.raises(ImageRejected, match="too large"):
        process_upload(make_image("PNG", size=(15, 15)), max_pixels=10_000)


def test_decompression_bomb_rejected_even_if_warnings_are_globally_ignored(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 200)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ImageRejected, match="too large"):
            process_upload(make_image("PNG", size=(15, 15)), max_pixels=200)


def test_decompression_bomb_error_is_a_rejection(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(ImageRejected, match="too large"):
        process_upload(make_image("PNG", size=(20, 20)), max_pixels=10_000)


def test_pillow_threshold_is_aligned_with_our_limit():
    assert Image.MAX_IMAGE_PIXELS == images.IMAGE_MAX_PIXELS
