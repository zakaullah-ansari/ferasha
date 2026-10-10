"""HTTP surface of the AI engine.

The engine holds a face-blurring capability and, transitively, access to
unblurred originals. Its routes are back-office only; an authenticated
customer must not be able to reach them.
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from tests.conftest import encode, featureless_noise


@pytest.fixture(scope="module")
def client(request):
    with TestClient(create_app()) as test_client:
        yield test_client


def token(
    *,
    role: str = "staff",
    is_back_office: bool = True,
    token_type: str = "access",
    **overrides,
) -> str:
    settings = get_settings()
    payload = {
        "sub": "42",
        "user_id": "42",
        "email": "staff@ferasha.test",
        "role": role,
        "is_back_office": is_back_office,
        "token_type": token_type,
        "aud": settings.jwt_audience,
        "exp": int(time.time()) + 600,
        "iat": int(time.time()),
    }
    payload.update(overrides)
    return jwt.encode(payload, settings.jwt_signing_key, algorithm=settings.jwt_algorithm)


def auth(**kwargs) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(**kwargs)}"}


@pytest.fixture
def portrait(photo_paths):
    if not photo_paths:
        pytest.skip("photograph fixtures unavailable")
    return photo_paths[0].read_bytes()


class TestHealth:
    def test_health_is_unauthenticated(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_ready_reports_model_state(self, client):
        """TestClient runs the lifespan, so models are loaded here."""
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["checks"]["face_models"] == "loaded"


class TestAuthentication:
    def test_anonymous_is_refused(self, client, portrait):
        response = client.post(
            "/api/v1/media/analyse", files={"file": ("p.jpg", portrait, "image/jpeg")}
        )
        assert response.status_code in {401, 403}

    def test_garbage_token_is_refused(self, client, portrait):
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401

    def test_token_signed_with_wrong_key_is_refused(self, client, portrait):
        forged = jwt.encode(
            {"sub": "42", "role": "staff", "token_type": "access",
             "is_back_office": True, "aud": get_settings().jwt_audience,
             "iat": int(time.time()), "exp": int(time.time()) + 600},
            "an-attacker-chosen-signing-key-value",
            algorithm="HS256",
        )
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert response.status_code == 401

    def test_expired_token_is_refused(self, client, portrait):
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers=auth(exp=int(time.time()) - 60),
        )
        assert response.status_code == 401

    def test_refresh_token_cannot_be_used_as_access(self, client, portrait):
        """Refresh tokens are long-lived; accepting one widens the blast radius."""
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers=auth(token_type="refresh"),
        )
        assert response.status_code == 401

    def test_customer_role_is_refused(self, client, portrait):
        """A logged-in shopper must not reach the privacy tooling."""
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers=auth(role="customer", is_back_office=False),
        )
        assert response.status_code == 403

    def test_staff_is_allowed(self, client, portrait):
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers=auth(role="staff"),
        )
        assert response.status_code == 200


class TestAnalyse:
    def test_reports_detections_without_returning_pixels(self, client, portrait):
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers=auth(),
        )
        body = response.json()
        assert body["faces_detected"] >= 1
        assert "image" not in body and "data" not in body

    def test_malformed_upload_is_rejected_cleanly(self, client):
        response = client.post(
            "/api/v1/media/analyse",
            files={"file": ("x.jpg", b"definitely not an image", "image/jpeg")},
            headers=auth(),
        )
        # 400: the client sent bytes that are not a decodable image.
        assert response.status_code == 400
        assert response.json()["detail"]


class TestBlur:
    def test_returns_image_for_a_verified_blur(self, client, portrait):
        response = client.post(
            "/api/v1/media/blur",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers=auth(),
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content.startswith(b"\xff\xd8\xff")

    def test_no_detection_returns_409_and_no_image(self, client):
        """The endpoint must refuse rather than hand back the original.

        Returning the unmodified image on "no faces found" would be the
        single easiest way to leak an unblurred face.
        """
        noise = encode(featureless_noise(), quality=95)
        response = client.post(
            "/api/v1/media/blur",
            files={"file": ("n.jpg", noise, "image/jpeg")},
            headers=auth(),
        )
        assert response.status_code == 409
        assert "image" not in response.headers.get("content-type", "")
        assert not response.content.startswith(b"\xff\xd8\xff")

    def test_response_carries_no_exif(self, client, portrait):
        from app.services.image_ops import has_metadata

        response = client.post(
            "/api/v1/media/blur",
            files={"file": ("p.jpg", portrait, "image/jpeg")},
            headers=auth(),
        )
        assert response.status_code == 200
        assert not has_metadata(response.content)


class TestPolicy:
    def test_policy_exposes_thresholds(self, client):
        response = client.get("/api/v1/media/policy", headers=auth())
        assert response.status_code == 200
        body = response.json()
        assert body["verification"]["max_residual_detail"] > 0
        assert body["zero_detection_policy"] == "human_review"
        assert body["exif_stripped"] is True
        assert body["max_pixels"] > 0
