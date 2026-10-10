"""Safe image decoding, EXIF stripping and format validation.

This module is the hostile-input boundary. Vendor imagery arrives from
manufacturers and scraped online sources, so it is treated as untrusted:

* **Format is sniffed from magic bytes**, never from the filename. An
  attacker controls the extension; they do not control the header.
* **Decompression bombs are rejected before decode.** Pillow reports image
  dimensions from the header, so the pixel budget is checked while the file
  is still compressed on disk.
* **EXIF is stripped unconditionally.** Vendor photographs routinely carry
  GPS coordinates identifying a home workshop. That is a privacy leak
  independent of the faces in the frame, and blurring does nothing about it.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Pillow's own bomb guard. We set our own stricter budget too, but leaving
# this at the default None would disable Pillow's warning entirely.
Image.MAX_IMAGE_PIXELS = 100_000_000


class ImageRejected(Exception):
    """The upload is malformed, oversized, or an unsupported format.

    Always a client-side problem. The worker converts this into a terminal
    rejection rather than a retry - retrying a malformed file forever just
    fills the queue.
    """


@dataclass(frozen=True)
class DecodedImage:
    """A decoded, EXIF-stripped, orientation-corrected RGB image."""

    pixels: np.ndarray  # (H, W, 3), uint8, RGB
    width: int
    height: int
    source_format: str

    @property
    def shape(self) -> tuple[int, int]:
        return self.height, self.width


def sniff_format(data: bytes) -> str | None:
    """Identify the format from magic bytes.

    Returns the Pillow format name, or None when unrecognised.
    """
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "GIF"
    if data[:2] in (b"II", b"MM"):
        return "TIFF"
    return None


def decode_image(data: bytes) -> DecodedImage:
    """Validate and decode ``data`` into an RGB array.

    Raises:
        ImageRejected: on any malformed, oversized or unsupported input.
    """
    settings = get_settings()

    if not data:
        raise ImageRejected("Empty file.")

    if len(data) > settings.max_upload_bytes:
        raise ImageRejected(
            f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)}MB limit."
        )

    sniffed = sniff_format(data)
    if sniffed is None:
        raise ImageRejected("Unrecognised image format.")
    if sniffed not in settings.allowed_formats:
        raise ImageRejected(
            f"{sniffed} is not an accepted format "
            f"({', '.join(settings.allowed_formats)} only)."
        )

    # Inspect the header before committing memory to a decode.
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe_format = probe.format
            width, height = probe.size
    except UnidentifiedImageError as exc:
        raise ImageRejected("File could not be parsed as an image.") from exc
    except Exception as exc:  # noqa: BLE001 - Pillow raises a wide variety here
        raise ImageRejected(f"Malformed image: {exc}") from exc

    if probe_format != sniffed:
        # The magic bytes and Pillow disagree - a polyglot or a crafted file.
        raise ImageRejected("Image header is inconsistent with its content.")

    if width <= 0 or height <= 0:
        raise ImageRejected("Image reports non-positive dimensions.")

    if width * height > settings.max_pixels:
        raise ImageRejected(
            f"Image is {width}x{height} ({width * height:,} pixels), "
            f"above the {settings.max_pixels:,} pixel budget."
        )

    if max(width, height) > settings.max_dimension:
        raise ImageRejected(
            f"Largest dimension {max(width, height)}px exceeds "
            f"{settings.max_dimension}px."
        )

    # Now safe to decode.
    try:
        with Image.open(io.BytesIO(data)) as image:
            # Apply EXIF orientation, then drop EXIF entirely. Order matters:
            # stripping first would leave a sideways image.
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")
            pixels = np.asarray(image, dtype=np.uint8)
    except Exception as exc:  # noqa: BLE001
        raise ImageRejected(f"Image could not be decoded: {exc}") from exc

    if pixels.ndim != 3 or pixels.shape[2] != 3:
        raise ImageRejected("Decoded image is not three-channel RGB.")

    return DecodedImage(
        pixels=pixels,
        width=pixels.shape[1],
        height=pixels.shape[0],
        source_format=sniffed,
    )


def encode_jpeg(pixels: np.ndarray, quality: int = 88) -> bytes:
    """Encode RGB pixels to JPEG with no metadata whatsoever.

    Pillow writes no EXIF unless asked, so constructing a fresh Image from a
    bare array guarantees the derivative carries none of the original's
    metadata - no GPS, no camera serial, no timestamps.
    """
    if pixels.dtype != np.uint8:
        pixels = np.clip(pixels, 0, 255).astype(np.uint8)

    image = Image.fromarray(pixels, mode="RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def has_metadata(data: bytes) -> bool:
    """True if the encoded image carries EXIF or XMP. Used by tests."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            if getattr(image, "_getexif", lambda: None)():
                return True
            if image.info.get("exif"):
                return True
            return bool(image.info.get("XML:com.adobe.xmp") or image.info.get("xmp"))
    except Exception:  # noqa: BLE001
        return False
