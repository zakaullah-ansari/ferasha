"""Security tests for the AI-engine callback surface.

The threat model is explicit: an attacker who knows an asset ID - which is
guessable from any page that references media - must not be able to mark that
asset APPROVED. Approval is what makes an image publicly servable, so a
forged callback is a direct route to publishing an unblurred face.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse

from apps.media_assets.models import AssetKind, MediaAsset, ModerationStatus

pytestmark = pytest.mark.django_db

SECRET = "insecure-shared-secret"


def sign(body: dict, *, secret: str = SECRET, timestamp: int | None = None,
         nonce: str | None = None) -> tuple[bytes, dict]:
    """Mirror of the worker's signing routine."""
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ts = str(timestamp if timestamp is not None else int(time.time()))
    nc = nonce or uuid.uuid4().hex
    message = b".".join([ts.encode(), nc.encode(), raw])
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return raw, {
        "HTTP_X_FERASHA_TIMESTAMP": ts,
        "HTTP_X_FERASHA_NONCE": nc,
        "HTTP_X_FERASHA_SIGNATURE": signature,
    }


@pytest.fixture
def uploader(db):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.create_user(
        email="vendor@ferasha.test",
        password="not-a-real-password",
        full_name="Vendor Uploader",
    )


@pytest.fixture
def asset(db, uploader):
    instance = MediaAsset.objects.create(
        kind=AssetKind.PRODUCT,
        uploaded_by=uploader,
        checksum="a" * 64,
        moderation_status=ModerationStatus.PENDING,
        byte_size=2048,
        width=800,
        height=1000,
    )
    instance.original.save("o.jpg", ContentFile(b"\xff\xd8\xff original"), save=True)
    return instance


@pytest.fixture(autouse=True)
def clear_nonces():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def url():
    return reverse("media_assets:callback")


def post(client: Client, url: str, body: dict, **kwargs):
    raw, headers = sign(body, **kwargs)
    return client.post(url, data=raw, content_type="application/json", **headers)


class TestSignatureEnforcement:
    def test_unsigned_callback_is_rejected(self, client, url, asset):
        response = client.post(
            url,
            data=json.dumps({"asset_id": str(asset.pk), "outcome": "approved",
                             "faces_detected": 1, "blur_verified": True}),
            content_type="application/json",
        )
        assert response.status_code == 401
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.PENDING

    def test_wrong_secret_is_rejected(self, client, url, asset):
        response = post(
            client, url,
            {"asset_id": str(asset.pk), "outcome": "approved",
             "faces_detected": 1, "blur_verified": True},
            secret="attacker-guessed-this-secret",
        )
        assert response.status_code == 401
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.PENDING

    def test_tampered_body_is_rejected(self, client, url, asset):
        """Sign a harmless payload, then swap in an approval."""
        honest = {"asset_id": str(asset.pk), "outcome": "needs_review"}
        _, headers = sign(honest)
        forged = json.dumps(
            {"asset_id": str(asset.pk), "outcome": "approved",
             "faces_detected": 1, "blur_verified": True},
            sort_keys=True, separators=(",", ":"),
        ).encode()

        response = client.post(url, data=forged,
                               content_type="application/json", **headers)
        assert response.status_code == 401
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.PENDING

    def test_replayed_callback_is_rejected(self, client, url, asset):
        """A captured valid request must not work a second time."""
        body = {"asset_id": str(asset.pk), "outcome": "needs_review"}
        raw, headers = sign(body)

        first = client.post(url, data=raw, content_type="application/json", **headers)
        assert first.status_code == 200

        second = client.post(url, data=raw, content_type="application/json", **headers)
        assert second.status_code == 401, "nonce replay was accepted"

    def test_stale_timestamp_is_rejected(self, client, url, asset):
        response = post(
            client, url, {"asset_id": str(asset.pk), "outcome": "needs_review"},
            timestamp=int(time.time()) - 4000,
        )
        assert response.status_code == 401

    def test_future_timestamp_is_rejected(self, client, url, asset):
        response = post(
            client, url, {"asset_id": str(asset.pk), "outcome": "needs_review"},
            timestamp=int(time.time()) + 4000,
        )
        assert response.status_code == 401


class TestOutcomeHandling:
    def test_approval_requires_a_derivative(self, client, url, asset):
        """Model-level defence: no derivative means no approval, ever."""
        response = post(
            client, url,
            {"asset_id": str(asset.pk), "checksum": asset.checksum,
             "outcome": "approved", "faces_detected": 1, "blur_verified": True},
        )
        assert response.status_code == 422
        asset.refresh_from_db()
        assert asset.moderation_status != ModerationStatus.APPROVED

    def test_approval_requires_blur_verified(self, client, url, asset):
        asset.derivative.save("d.jpg", ContentFile(b"\xff\xd8\xff blurred"), save=True)
        response = post(
            client, url,
            {"asset_id": str(asset.pk), "checksum": asset.checksum,
             "outcome": "approved", "faces_detected": 1, "blur_verified": False},
        )
        assert response.status_code == 422
        asset.refresh_from_db()
        assert asset.moderation_status != ModerationStatus.APPROVED

    def test_zero_faces_cannot_be_approved(self, client, url, asset):
        asset.derivative.save("d.jpg", ContentFile(b"\xff\xd8\xff blurred"), save=True)
        response = post(
            client, url,
            {"asset_id": str(asset.pk), "checksum": asset.checksum,
             "outcome": "approved", "faces_detected": 0, "blur_verified": True},
        )
        assert response.status_code == 422
        asset.refresh_from_db()
        assert asset.moderation_status != ModerationStatus.APPROVED

    def test_valid_approval_succeeds(self, client, url, asset):
        asset.derivative.save("d.jpg", ContentFile(b"\xff\xd8\xff blurred"), save=True)
        response = post(
            client, url,
            {"asset_id": str(asset.pk), "checksum": asset.checksum,
             "outcome": "approved", "faces_detected": 2, "blur_verified": True},
        )
        assert response.status_code == 200
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.APPROVED
        assert asset.blur_verified is True
        assert asset.faces_detected == 2

    def test_needs_review_outcome(self, client, url, asset):
        response = post(
            client, url,
            {"asset_id": str(asset.pk), "checksum": asset.checksum,
             "outcome": "needs_review", "detail": "no faces found"},
        )
        assert response.status_code == 200
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.NEEDS_REVIEW

    def test_checksum_mismatch_is_refused(self, client, url, asset):
        """The original changed after the worker read it."""
        response = post(
            client, url,
            {"asset_id": str(asset.pk), "checksum": "b" * 64,
             "outcome": "approved", "faces_detected": 1, "blur_verified": True},
        )
        assert response.status_code == 409
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.PENDING

    def test_unknown_outcome_is_refused(self, client, url, asset):
        response = post(
            client, url, {"asset_id": str(asset.pk), "outcome": "publish_it_anyway"},
        )
        assert response.status_code == 400

    def test_unknown_asset_returns_404(self, client, url):
        response = post(
            client, url, {"asset_id": str(uuid.uuid4()), "outcome": "needs_review"},
        )
        assert response.status_code == 404

    def test_settled_asset_is_not_reopened(self, client, url, asset):
        """A late duplicate must not flip an approved asset back."""
        asset.derivative.save("d.jpg", ContentFile(b"\xff\xd8\xff blurred"), save=True)
        asset.mark_approved(faces=1, blur_verified=True)

        response = post(
            client, url,
            {"asset_id": str(asset.pk), "checksum": asset.checksum,
             "outcome": "rejected", "detail": "late duplicate"},
        )
        assert response.status_code == 200
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.APPROVED


class TestCrossServiceCompatibility:
    def test_engine_signature_is_accepted_by_django(self, client, url, asset):
        """The two independent implementations must agree.

        Django and the AI engine each compute this HMAC in their own
        codebase, with their own dependencies. If either canonicalisation
        drifts, every callback breaks in production - so the engine's real
        signer is invoked here, in the engine's own interpreter, and the
        resulting headers are replayed against the live Django endpoint.

        A subprocess is used deliberately rather than importing the engine:
        the two services have incompatible dependency sets, and mutating
        sys.path mid-suite leaks into unrelated tests.
        """
        import json as _json
        import subprocess
        from pathlib import Path

        engine_root = Path(__file__).resolve().parents[4] / "ai-engine"
        interpreter = engine_root / ".venv" / "bin" / "python"
        if not interpreter.exists():
            pytest.skip("ai-engine virtualenv not built")

        body = {
            "asset_id": str(asset.pk),
            "checksum": asset.checksum,
            "outcome": "needs_review",
            "detail": "engine signed",
        }

        script = (
            "import json,sys\n"
            "from app.core.security import sign_callback, canonical_payload\n"
            "body = json.loads(sys.argv[1])\n"
            "sys.stdout.write(json.dumps({\n"
            "    'headers': sign_callback(body),\n"
            "    'raw': canonical_payload(body).decode(),\n"
            "}))\n"
        )

        completed = subprocess.run(
            [str(interpreter), "-c", script, _json.dumps(body)],
            cwd=str(engine_root),
            capture_output=True,
            text=True,
            timeout=120,
            env={
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": str(engine_root),
                "JWT_SIGNING_KEY": "x" * 40,
                "AI_ENGINE_SHARED_SECRET": SECRET,
            },
        )
        assert completed.returncode == 0, f"engine signer failed: {completed.stderr}"

        produced = _json.loads(completed.stdout)
        headers = produced["headers"]

        response = client.post(
            url,
            data=produced["raw"].encode(),
            content_type="application/json",
            HTTP_X_FERASHA_TIMESTAMP=headers["X-Ferasha-Timestamp"],
            HTTP_X_FERASHA_NONCE=headers["X-Ferasha-Nonce"],
            HTTP_X_FERASHA_SIGNATURE=headers["X-Ferasha-Signature"],
        )
        assert response.status_code == 200, (
            "the engine's signature was rejected by Django - the two HMAC "
            f"implementations have drifted apart: {response.content!r}"
        )
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.NEEDS_REVIEW
