"""Shared fixtures for the AI engine test suite."""

from __future__ import annotations

import io
import os

import numpy as np
import pytest
from PIL import Image

# Settings are validated at import time, so the environment must be populated
# before anything under app.* is imported.
os.environ.setdefault("JWT_SIGNING_KEY", "test-signing-key-that-is-definitely-32-bytes")
os.environ.setdefault("AI_ENGINE_SHARED_SECRET", "test-shared-secret-value")


@pytest.fixture(scope="session")
def loaded_detector():
    """The process-wide detector, loaded once for the whole session.

    Loading per test would add seconds per case and is also what the Phase 3
    exit criteria explicitly forbid in production.
    """
    from app.services.face_blur import detector

    detector.load()
    yield detector


def synthetic_face(width: int = 400, height: int = 500) -> np.ndarray:
    """A crude but reliably detectable face on a textured background.

    Verified to yield exactly one MediaPipe detection, which is itself
    evidence the deliberately low confidence threshold is doing its job. Use
    ``featureless_noise`` for the zero-detection path, and the photograph
    fixtures where real-world detection quality matters.
    """
    rng = np.random.default_rng(1947)
    canvas = rng.integers(90, 170, size=(height, width, 3), dtype=np.uint8)

    cx, cy = width // 2, height // 2
    yy, xx = np.ogrid[:height, :width]
    face = ((xx - cx) / (width * 0.22)) ** 2 + ((yy - cy) / (height * 0.28)) ** 2 <= 1
    canvas[face] = (222, 190, 160)

    # Eyes, nose, mouth - high-contrast detail the blur must destroy.
    for ex in (cx - width // 10, cx + width // 10):
        eye = ((xx - ex) / (width * 0.035)) ** 2 + ((yy - (cy - height // 12)) / (height * 0.022)) ** 2 <= 1
        canvas[eye] = (25, 25, 30)
    mouth = ((xx - cx) / (width * 0.09)) ** 2 + ((yy - (cy + height // 8)) / (height * 0.025)) ** 2 <= 1
    canvas[mouth] = (150, 60, 60)
    return canvas


def encode(pixels: np.ndarray, fmt: str = "JPEG", **kwargs) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(pixels, mode="RGB").save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


def featureless_noise(width: int = 400, height: int = 500) -> np.ndarray:
    """Textured noise containing no face. Verified to yield zero detections."""
    return np.random.default_rng(3).integers(
        0, 255, size=(height, width, 3), dtype=np.uint8
    )


@pytest.fixture
def synthetic_face_rgb() -> np.ndarray:
    return synthetic_face()


@pytest.fixture
def synthetic_face_jpeg(synthetic_face_rgb: np.ndarray) -> bytes:
    return encode(synthetic_face_rgb, quality=95)


@pytest.fixture(scope="session")
def photo_paths() -> list:
    """Real photographs, used to prove detection works on actual faces."""
    from pathlib import Path

    directory = Path(__file__).resolve().parents[2] / "image-search"
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix in {".jpg", ".jpeg", ".webp", ".png"})
