"""Configuration for the Ferasha AI engine.

Settings are read from the environment and validated at import time. A
misconfigured privacy service must fail to start rather than run with unsafe
defaults - every field that affects the privacy guarantee is either required
or defaults to the *stricter* value.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- service ----------------------------------------------------------
    service_name: str = "ferasha-ai-engine"
    debug: bool = False
    log_level: str = "INFO"

    # --- security ---------------------------------------------------------
    # Shared with Django (D1). The engine only *verifies* tokens; it never
    # issues them.
    jwt_signing_key: str = Field(..., alias="JWT_SIGNING_KEY")
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "ferasha"
    jwt_issuer: str = "ferasha-backend-core"

    # HMAC secret for worker -> Django callbacks.
    ai_engine_shared_secret: str = Field(..., alias="AI_ENGINE_SHARED_SECRET")

    #: Callbacks older than this are rejected as replays.
    callback_max_skew_seconds: int = 300

    # --- backend ----------------------------------------------------------
    backend_base_url: str = Field("http://localhost:8000", alias="BACKEND_BASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    media_queue: str = "ferasha:media:blur"
    media_dlq: str = "ferasha:media:blur:dead"

    # --- image guards -----------------------------------------------------
    #: Hard ceiling on decoded pixels. Guards against decompression bombs: a
    #: 20KB PNG can decode to gigabytes of RAM and take the worker down.
    max_pixels: int = 50_000_000
    max_upload_bytes: int = 25 * 1024 * 1024
    max_dimension: int = 8192
    allowed_formats: tuple[str, ...] = ("JPEG", "PNG", "WEBP")

    # --- detection --------------------------------------------------------
    #: Deliberately low. A false positive blurs a handbag clasp; a false
    #: negative publishes someone's face. The asymmetry is the whole point.
    detection_confidence: float = 0.25

    #: Fraction of the face box added on each side before blurring. A tight
    #: crop leaves hairline, jaw and ears identifiable.
    face_margin: float = 0.35

    # --- irreversibility --------------------------------------------------
    #: Primary criterion. Mean absolute Laplacian energy inside the ellipse
    #: must fall below this. An unmodified face measures in the hundreds; a
    #: destroyed one collapses to roughly 1. Measured empirically against real
    #: portrait photography, then set with a wide safety margin.
    max_residual_detail: float = 3.0
    #: Secondary guard, applied only when the source region had real detail to
    #: begin with. JPEG quantisation noise puts a floor under this ratio, so it
    #: is unreliable as a primary test - see services/face_blur.py.
    max_highfreq_ratio: float = 0.45
    #: Below this pre-blur energy a region is already flat, and the ratio test
    #: would be meaningless.
    flat_region_energy: float = 4.0
    #: Blur escalation attempts before the asset is rejected outright.
    max_blur_escalations: int = 4

    # --- worker -----------------------------------------------------------
    max_attempts: int = 5
    retry_base_seconds: float = 2.0

    @field_validator("jwt_signing_key")
    @classmethod
    def _key_long_enough(cls, value: str) -> str:
        # Mirrors the Phase 0 check in Django: a short HS256 key is brute
        # forceable, and both services must agree on the same strong key.
        if len(value.encode("utf-8")) < 32:
            raise ValueError("JWT_SIGNING_KEY must be at least 32 bytes for HS256.")
        return value

    @field_validator("ai_engine_shared_secret")
    @classmethod
    def _secret_long_enough(cls, value: str) -> str:
        if len(value.encode("utf-8")) < 16:
            raise ValueError("AI_ENGINE_SHARED_SECRET must be at least 16 bytes.")
        return value

    @field_validator("detection_confidence")
    @classmethod
    def _confidence_sane(cls, value: float) -> float:
        if not 0.0 < value < 1.0:
            raise ValueError("detection_confidence must be between 0 and 1.")
        if value > 0.6:
            # Not a hard failure, but this inverts the safety trade-off and
            # should never happen silently.
            raise ValueError(
                "detection_confidence above 0.6 risks missing faces. "
                "The engine biases towards over-detection by design."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
