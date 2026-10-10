"""Configuration and deployment-wiring invariants.

These tests exist because a misconfiguration here does not fail loudly in
development - it crash-loops a container in staging, or silently disables a
privacy guarantee. Each one encodes a mistake already made at least once.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

REQUIRED = {
    "JWT_SIGNING_KEY": "x" * 40,
    "AI_ENGINE_SHARED_SECRET": "y" * 20,
}


class TestSecretValidation:
    def test_short_signing_key_is_refused(self):
        """A short HS256 key is brute-forceable and must not boot."""
        with pytest.raises(ValueError):
            Settings(JWT_SIGNING_KEY="too-short", AI_ENGINE_SHARED_SECRET="y" * 20)

    def test_short_shared_secret_is_refused(self):
        with pytest.raises(ValueError):
            Settings(JWT_SIGNING_KEY="x" * 40, AI_ENGINE_SHARED_SECRET="short")

    def test_valid_secrets_are_accepted(self):
        settings = Settings(**REQUIRED)
        assert settings.jwt_signing_key == "x" * 40

    def test_detection_confidence_cannot_be_raised_carelessly(self):
        """A high threshold silently stops detecting veiled and profile faces.

        Missing a face is the failure mode with real-world consequences, so
        the ceiling is enforced in code rather than left to a reviewer.
        """
        with pytest.raises(ValueError):
            Settings(**REQUIRED, detection_confidence=0.9)

    def test_nonsensical_confidence_is_refused(self):
        with pytest.raises(ValueError):
            Settings(**REQUIRED, detection_confidence=0.0)
        with pytest.raises(ValueError):
            Settings(**REQUIRED, detection_confidence=1.5)

    def test_default_confidence_is_deliberately_low(self):
        assert Settings(**REQUIRED).detection_confidence <= 0.3


class TestComposeWiring:
    """The compose file must actually be able to start these services."""

    @pytest.fixture(scope="class")
    def compose(self):
        if not COMPOSE_FILE.exists():
            pytest.skip("docker-compose.yml not present")
        return yaml.safe_load(COMPOSE_FILE.read_text())

    @staticmethod
    def _default(expression: str) -> str:
        """Resolve ``${VAR:-default}`` to its default."""
        match = re.fullmatch(r"\$\{[A-Z_]+:-(.*)\}", str(expression).strip())
        return match.group(1) if match else str(expression)

    @pytest.mark.parametrize("service", ["ai-engine", "ai-worker"])
    def test_required_env_is_supplied(self, compose, service):
        env = compose["services"][service].get("environment", {})
        for key in REQUIRED:
            assert key in env, (
                f"{service} is missing {key}; Settings validation runs at import "
                f"time, so the container would crash-loop on boot"
            )

    @pytest.mark.parametrize("service", ["ai-engine", "ai-worker"])
    def test_default_secrets_satisfy_their_validators(self, compose, service):
        """`docker compose up` with no .env must still boot.

        A default shorter than the validator's minimum turns the first-run
        experience into an unexplained crash loop.
        """
        env = compose["services"][service]["environment"]
        Settings(
            JWT_SIGNING_KEY=self._default(env["JWT_SIGNING_KEY"]),
            AI_ENGINE_SHARED_SECRET=self._default(env["AI_ENGINE_SHARED_SECRET"]),
        )

    @pytest.mark.parametrize("service", ["ai-engine", "ai-worker"])
    def test_backend_url_uses_the_name_config_reads(self, compose, service):
        """The alias is BACKEND_BASE_URL.

        Supplying BACKEND_CORE_URL instead is not an error - the setting
        quietly falls back to localhost, and every callback from the worker
        fails inside the container network.
        """
        env = compose["services"][service]["environment"]
        assert "BACKEND_BASE_URL" in env
        assert "BACKEND_CORE_URL" not in env

    def test_worker_and_engine_share_one_secret(self, compose):
        """A mismatch makes every callback fail signature verification."""
        engine = compose["services"]["ai-engine"]["environment"]
        worker = compose["services"]["ai-worker"]["environment"]
        assert (
            engine["AI_ENGINE_SHARED_SECRET"] == worker["AI_ENGINE_SHARED_SECRET"]
        )

    def test_backend_shares_the_same_secret_as_the_worker(self, compose):
        """Django verifies what the worker signs; one secret, three services."""
        backend = compose["services"]["backend-core"]["environment"]
        worker = compose["services"]["ai-worker"]["environment"]
        assert backend["AI_ENGINE_SHARED_SECRET"] == worker["AI_ENGINE_SHARED_SECRET"]


class TestEnvExample:
    def test_documented_defaults_are_valid(self):
        """Copying .env.example must produce a bootable configuration."""
        if not ENV_EXAMPLE.exists():
            pytest.skip(".env.example not present")

        values: dict[str, str] = {}
        for line in ENV_EXAMPLE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()

        for key in REQUIRED:
            assert key in values, f"{key} is undocumented in .env.example"

        Settings(
            JWT_SIGNING_KEY=values["JWT_SIGNING_KEY"],
            AI_ENGINE_SHARED_SECRET=values["AI_ENGINE_SHARED_SECRET"],
        )
