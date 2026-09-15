"""Hostile-input handling: format sniffing, bombs, EXIF.

Vendor imagery is untrusted input. Every test here represents a file that a
careless or malicious supplier could realistically put in front of the worker.
"""

from __future__ import annotations

import io

import numpy as np
import piexif  # type: ignore[import-not-found]
import pytest
from PIL import Image

from app.services.image_ops import (
    ImageRejected,
    decode_image,
    encode_jpeg,
    has_metadata,
    sniff_format,
)
from tests.conftest import encode


class TestFormatSniffing:
    def test_detects_real_formats(self, synthetic_face_rgb):
        assert sniff_format(encode(synthetic_face_rgb, "JPEG")) == "JPEG"
        assert sniff_format(encode(synthetic_face_rgb, "PNG")) == "PNG"
        assert sniff_format(encode(synthetic_face_rgb, "WEBP")) == "WEBP"

    def test_extension_is_never_trusted(self, synthetic_face_rgb):
        """A PNG named .jpg is still a PNG.

        The worker only ever sees bytes, so the guarantee is that content
        decides. This test documents that intent.
        """
        data = encode(synthetic_face_rgb, "PNG")
        assert sniff_format(data) == "PNG"

    def test_rejects_unknown_magic(self):
        assert sniff_format(b"\x00\x01\x02\x03" * 8) is None
        assert sniff_format(b"") is None
        assert sniff_format(b"#!/bin/sh\necho pwned\n") is None

    def test_rejects_svg_and_scripts(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        with pytest.raises(ImageRejected):
            decode_image(svg)


class TestDecodeGuards:
    def test_rejects_empty(self):
        with pytest.raises(ImageRejected, match="Empty"):
            decode_image(b"")

    def test_rejects_truncated_jpeg(self, synthetic_face_jpeg):
        with pytest.raises(ImageRejected):
            decode_image(synthetic_face_jpeg[:64])

    def test_rejects_unsupported_format(self, synthetic_face_rgb):
        gif = encode(synthetic_face_rgb.astype(np.uint8), "GIF")
        with pytest.raises(ImageRejected, match="not an accepted format"):
            decode_image(gif)

    def test_rejects_oversized_file(self, monkeypatch, synthetic_face_jpeg):
        from app.core import config

        settings = config.get_settings()
        monkeypatch.setattr(settings, "max_upload_bytes", 128)
        with pytest.raises(ImageRejected, match="exceeds"):
            decode_image(synthetic_face_jpeg)

    def test_rejects_decompression_bomb_before_decoding(self, monkeypatch):
        """A tiny file that decodes to an enormous canvas must be refused.

        The check reads dimensions from the header, so memory is never
        committed. A 16000x16000 PNG of flat colour compresses to a few KB but
        decodes to ~768MB.
        """
        from app.core import config

        bomb = Image.new("RGB", (16000, 16000), (255, 255, 255))
        buffer = io.BytesIO()
        bomb.save(buffer, format="PNG", compress_level=9)
        data = buffer.getvalue()

        settings = config.get_settings()
        monkeypatch.setattr(settings, "max_upload_bytes", 50 * 1024 * 1024)
        assert len(data) < 5 * 1024 * 1024, "fixture should be small on disk"

        with pytest.raises(ImageRejected, match="pixel budget|exceeds"):
            decode_image(data)

    def test_rejects_excessive_dimension(self, monkeypatch):
        from app.core import config

        settings = config.get_settings()
        monkeypatch.setattr(settings, "max_dimension", 100)
        monkeypatch.setattr(settings, "max_pixels", 10_000_000)
        tall = np.zeros((400, 50, 3), dtype=np.uint8)
        with pytest.raises(ImageRejected, match="exceeds"):
            decode_image(encode(tall))

    def test_accepts_valid_image(self, synthetic_face_jpeg):
        decoded = decode_image(synthetic_face_jpeg)
        assert decoded.width == 400
        assert decoded.height == 500
        assert decoded.source_format == "JPEG"
        assert decoded.pixels.shape == (500, 400, 3)
        assert decoded.pixels.dtype == np.uint8


class TestExifHandling:
    def _jpeg_with_gps(self, pixels: np.ndarray) -> bytes:
        """A JPEG carrying GPS coordinates, as vendor phone photos do."""
        exif = {
            "0th": {piexif.ImageIFD.Make: b"TestCam", piexif.ImageIFD.Model: b"Vendor Phone"},
            "GPS": {
                piexif.GPSIFD.GPSLatitudeRef: b"N",
                piexif.GPSIFD.GPSLatitude: ((19, 1), (4, 1), (0, 1)),   # Mumbai
                piexif.GPSIFD.GPSLongitudeRef: b"E",
                piexif.GPSIFD.GPSLongitude: ((72, 1), (52, 1), (0, 1)),
            },
            "Exif": {},
            "1st": {},
            "thumbnail": None,
        }
        buffer = io.BytesIO()
        Image.fromarray(pixels, mode="RGB").save(
            buffer, format="JPEG", exif=piexif.dump(exif), quality=90
        )
        return buffer.getvalue()

    def test_fixture_actually_has_gps(self, synthetic_face_rgb):
        """Guard the test itself - a fixture without EXIF proves nothing."""
        assert has_metadata(self._jpeg_with_gps(synthetic_face_rgb))

    def test_gps_is_stripped_from_derivative(self, synthetic_face_rgb):
        source = self._jpeg_with_gps(synthetic_face_rgb)
        decoded = decode_image(source)
        derivative = encode_jpeg(decoded.pixels)

        assert not has_metadata(derivative), "GPS survived into the published derivative"

        parsed = piexif.load(derivative)
        assert not parsed.get("GPS"), "GPS IFD present in derivative"

    def test_orientation_is_applied_then_dropped(self, synthetic_face_rgb):
        """EXIF rotation must be baked into pixels before the tag is removed."""
        exif = {"0th": {piexif.ImageIFD.Orientation: 6}, "Exif": {}, "GPS": {}, "1st": {},
                "thumbnail": None}
        buffer = io.BytesIO()
        Image.fromarray(synthetic_face_rgb, mode="RGB").save(
            buffer, format="JPEG", exif=piexif.dump(exif), quality=90
        )
        decoded = decode_image(buffer.getvalue())
        # Orientation 6 is a 90 degree rotation, so the axes swap.
        assert (decoded.width, decoded.height) == (500, 400)


class TestEncoding:
    def test_encode_produces_clean_jpeg(self, synthetic_face_rgb):
        data = encode_jpeg(synthetic_face_rgb)
        assert sniff_format(data) == "JPEG"
        assert not has_metadata(data)

    def test_encode_clamps_out_of_range(self):
        noisy = np.full((40, 40, 3), 300, dtype=np.int32)
        data = encode_jpeg(noisy)  # type: ignore[arg-type]
        assert sniff_format(data) == "JPEG"
