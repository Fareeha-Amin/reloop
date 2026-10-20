"""Server-side validation and sanitising of uploaded images. Pure: bytes in, bytes out.

Every accepted upload is decoded and re-encoded from raw pixels. That does three jobs:
  * proves the file really is an image of an allowed format (the client's Content-Type
    and filename are ignored);
  * strips ALL metadata, including EXIF GPS coordinates, which phone photos usually carry
    and which would otherwise leak the donor's location (non-negotiable 10);
  * applies the EXIF orientation first, so stripped photos are not shown sideways.

Decompression bombs are rejected, never merely warned about: anything over
IMAGE_MAX_PIXELS is refused by an explicit size check, and Pillow's
DecompressionBombWarning is escalated to an error as a second line of defence.
"""

import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.constants import (
    IMAGE_FORMATS,
    IMAGE_MAX_BYTES,
    IMAGE_MAX_PIXELS,
    JPEG_QUALITY,
    WEBP_QUALITY,
)

# Pillow warns above this many pixels and raises at twice it. Align it with our limit.
Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS


class ImageRejected(ValueError):
    pass


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    content_type: str
    extension: str
    width: int
    height: int


def process_upload(raw: bytes, max_pixels: int = IMAGE_MAX_PIXELS) -> ProcessedImage:
    if not raw:
        raise ImageRejected("File is empty.")
    if len(raw) > IMAGE_MAX_BYTES:
        raise ImageRejected(f"File is larger than {IMAGE_MAX_BYTES // (1024 * 1024)} MB.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(raw))
            fmt = image.format
            if fmt not in IMAGE_FORMATS:
                raise ImageRejected(
                    f"Unsupported image type. Allowed: {', '.join(sorted(IMAGE_FORMATS))}."
                )
            width, height = image.size
            # The authoritative check. Does not depend on warning filters, which are
            # process-global and can be changed by other code.
            if width * height > max_pixels:
                raise ImageRejected("Image dimensions are too large.")
            image.load()
            image = ImageOps.exif_transpose(image)
            data = _reencode_without_metadata(image, fmt)
    except ImageRejected:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageRejected("Image dimensions are too large.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ImageRejected("File is not a readable image.") from exc

    content_type, extension = IMAGE_FORMATS[fmt]
    return ProcessedImage(
        data=data,
        content_type=content_type,
        extension=extension,
        width=image.width,
        height=image.height,
    )


def _reencode_without_metadata(image: Image.Image, fmt: str) -> bytes:
    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    mode = "RGBA" if has_alpha and fmt != "JPEG" else "RGB"
    converted = image.convert(mode)
    # A brand-new image built from raw pixels carries no info dict, EXIF, XMP, ICC
    # profile or text chunks: there is nothing left for the encoder to copy across.
    clean = Image.frombytes(mode, converted.size, converted.tobytes())

    out = io.BytesIO()
    if fmt == "JPEG":
        clean.save(out, format="JPEG", quality=JPEG_QUALITY)
    elif fmt == "WEBP":
        clean.save(out, format="WEBP", quality=WEBP_QUALITY)
    else:
        clean.save(out, format="PNG", optimize=True)
    return out.getvalue()
