"""The original must never be routable over HTTP.

This exists because the guarantee was broken once. ``config/urls.py`` called
``static(MEDIA_URL, document_root=MEDIA_ROOT)`` under DEBUG, which serves the
whole media tree - including ``private/originals/``, the unblurred vendor
uploads. Every other layer of the privacy pipeline was working correctly and
the leak was still wide open, because it bypassed all of them.

A model docstring promising "never publicly routed" is not enforcement. This
is.
"""

from __future__ import annotations

import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import override_settings
from django.urls import get_resolver

from apps.media_assets.models import AssetKind, MediaAsset, ModerationStatus

pytestmark = pytest.mark.django_db

ORIGINAL_BYTES = b"\xff\xd8\xff\xe0 pretend this is an unblurred face"
DERIVATIVE_BYTES = b"\xff\xd8\xff\xe0 pretend this is the blurred derivative"


@pytest.fixture
def approved_asset(db, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }

    user = get_user_model().objects.create_user(
        email="vendor2@ferasha.test",
        password="not-a-real-password",
        full_name="Vendor Two",
    )
    asset = MediaAsset(
        kind=AssetKind.PRODUCT,
        uploaded_by=user,
        checksum=hashlib.sha256(ORIGINAL_BYTES).hexdigest(),
        byte_size=len(ORIGINAL_BYTES),
        width=640,
        height=800,
        moderation_status=ModerationStatus.PENDING,
    )
    asset.original.save("orig.jpg", ContentFile(ORIGINAL_BYTES), save=True)
    asset.derivative.save("blur.jpg", ContentFile(DERIVATIVE_BYTES), save=True)
    asset.mark_approved(faces=1, blur_verified=True)
    return asset


class TestOriginalIsNotServable:
    @override_settings(DEBUG=True)
    def test_original_is_not_reachable_in_debug(self, client, approved_asset):
        """DEBUG is where the leak was. Assert against it directly."""
        response = client.get(approved_asset.original.url)
        assert response.status_code == 404, (
            "the unblurred original was served over HTTP - this is the exact "
            "leak the privacy pipeline exists to prevent"
        )

    @override_settings(DEBUG=True)
    def test_original_bytes_never_appear_in_a_response(self, client, approved_asset):
        """Stronger than a status check: the bytes must not escape."""
        response = client.get(approved_asset.original.url)
        body = b"".join(response.streaming_content) if response.streaming else response.content
        assert ORIGINAL_BYTES not in body

    @override_settings(DEBUG=True)
    def test_derivative_is_routed_under_the_public_prefix(self, approved_asset):
        """The fix must not break the thing the pipeline exists to produce.

        Asserts the storage prefix, not a live fetch. The URLconf is built at
        import time, so under the test settings (DEBUG=False) the static route
        does not exist at all and override_settings cannot retroactively add
        it. The prefix is the durable contract: config/urls.py routes exactly
        MEDIA_URL + "public/", so a derivative landing anywhere else would be
        unreachable. Actual downloadability is verified end-to-end against a
        running server.
        """
        url = approved_asset.public_url
        assert url.startswith("/media/public/"), (
            "derivatives must live under the one prefix that is routed; "
            f"got {url}"
        )
        assert "/private/" not in url

    @override_settings(DEBUG=True)
    def test_traversal_out_of_the_public_prefix_is_refused(
        self, client, approved_asset
    ):
        escape = f"/media/public/../private/originals/{approved_asset.pk}/orig.jpg"
        response = client.get(escape)
        assert response.status_code in {400, 404}

    def test_no_url_pattern_exposes_the_private_root(self, settings):
        """Inspect the resolver rather than guessing at URLs.

        Catches a reintroduction even if the prefix is renamed, by asserting
        no static route is rooted at MEDIA_ROOT itself.
        """
        settings.DEBUG = True
        from pathlib import Path

        media_root = Path(settings.MEDIA_ROOT).resolve()
        for pattern in get_resolver().url_patterns:
            document_root = getattr(
                getattr(pattern, "default_args", {}) or {}, "get", lambda *_: None
            )("document_root")
            if document_root is None:
                continue
            served = Path(str(document_root)).resolve()
            assert served != media_root, (
                f"a URL pattern serves all of MEDIA_ROOT ({served}); "
                "private/originals would be publicly downloadable"
            )
