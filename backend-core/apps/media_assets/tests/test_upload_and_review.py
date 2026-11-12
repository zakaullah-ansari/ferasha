"""Getting an image in, and a person signing off on what the detector cannot.

Upload -> private original -> job queued for the blur worker -> worker fetches
the original through a short-lived signed link -> outcome. When the detector
finds no face it cannot prove there is none, so a person decides; on their
approval Django itself writes the public copy (EXIF and GPS stripped), so
nothing reaches public storage before a check has passed.
"""

from __future__ import annotations

import io
import json

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse
from PIL import Image

from apps.media_assets import services
from apps.media_assets.models import AssetKind, MediaAsset, ModerationStatus

pytestmark = pytest.mark.django_db


def jpeg_bytes(*, size=(40, 60), with_exif: bool = False) -> bytes:
    image = Image.new("RGB", size, (120, 60, 30))
    buffer = io.BytesIO()
    if with_exif:
        exif = Image.Exif()
        exif[0x010F] = "SecretCam"  # Make
        image.save(buffer, "JPEG", exif=exif.tobytes())
    else:
        image.save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.fixture
def owner(db):
    return get_user_model().objects.create_user(
        email="owner@ferasha.test",
        password="not-a-real-password",
        full_name="Owner",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def queued(monkeypatch):
    """Capture jobs instead of talking to Redis."""
    jobs: list[dict] = []
    monkeypatch.setattr(services, "_push_job", lambda raw: jobs.append(json.loads(raw)))
    return jobs


def upload(owner, data: bytes | None = None, name: str = "kurta.jpg") -> MediaAsset:
    file = SimpleUploadedFile(name, data if data is not None else jpeg_bytes(), "image/jpeg")
    return services.create_from_upload(file, kind=AssetKind.PRODUCT, uploaded_by=owner)


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #


class TestUpload:
    def test_upload_stores_a_private_pending_original(self, owner, queued):
        asset = upload(owner)

        assert asset.moderation_status == ModerationStatus.PENDING
        assert asset.original.name.startswith(f"private/originals/{asset.pk}/")
        assert not asset.derivative
        assert (asset.width, asset.height) == (40, 60)
        assert asset.content_type == "image/jpeg"
        assert len(asset.checksum) == 64
        assert asset.public_url is None

    def test_upload_queues_a_blur_job_after_commit(
        self, owner, queued, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            asset = upload(owner)

        assert len(queued) == 1
        job = queued[0]
        assert job["asset_id"] == str(asset.pk)
        assert job["checksum"] == asset.checksum
        assert job["download_url"].startswith("http")

    def test_a_non_image_is_refused(self, owner, queued):
        with pytest.raises(ValidationError):
            upload(owner, b"<?php echo 'hi'; ?>", name="evil.jpg")
        assert MediaAsset.objects.count() == 0

    def test_an_oversized_file_is_refused(self, owner, queued, settings):
        settings.MEDIA_UPLOAD_MAX_BYTES = 100
        with pytest.raises(ValidationError):
            upload(owner)

    def test_a_gif_is_refused(self, owner, queued):
        buffer = io.BytesIO()
        Image.new("RGB", (4, 4)).save(buffer, "GIF")
        with pytest.raises(ValidationError):
            upload(owner, buffer.getvalue(), name="anim.gif")


# --------------------------------------------------------------------------- #
# The worker's signed download link
# --------------------------------------------------------------------------- #


class TestOriginalDownload:
    def test_signed_link_returns_the_original(self, client, owner, queued):
        data = jpeg_bytes()
        asset = upload(owner, data)
        response = client.get(services.original_download_path(asset))

        assert response.status_code == 200
        assert b"".join(response.streaming_content) == data
        assert "no-store" in response["Cache-Control"]

    def test_missing_or_forged_token_is_refused(self, client, owner, queued):
        asset = upload(owner)
        url = reverse("media_assets:original", args=[asset.pk])
        assert client.get(url).status_code == 403
        assert client.get(url, {"token": "forged"}).status_code == 403

    def test_token_for_one_asset_does_not_open_another(self, client, owner, queued):
        first, second = upload(owner), upload(owner, jpeg_bytes(size=(10, 10)))
        token = services.original_download_path(first).split("token=")[1]
        url = reverse("media_assets:original", args=[second.pk])
        assert client.get(url, {"token": token}).status_code == 403

    def test_expired_token_is_refused(self, client, owner, queued, settings):
        asset = upload(owner)
        path = services.original_download_path(asset)
        settings.MEDIA_ORIGINAL_LINK_MAX_AGE = -1
        assert client.get(path).status_code == 403

    def test_link_dies_once_the_asset_is_settled(self, client, owner, queued):
        asset = upload(owner)
        path = services.original_download_path(asset)
        asset.mark_rejected("bad file")
        assert client.get(path).status_code == 403


# --------------------------------------------------------------------------- #
# Rejection (the callback used to crash: the model had no mark_rejected)
# --------------------------------------------------------------------------- #


def test_mark_rejected_settles_the_asset(owner, queued):
    asset = upload(owner)
    asset.mark_rejected("Could not verify blur.")
    asset.refresh_from_db()
    assert asset.moderation_status == ModerationStatus.REJECTED
    assert asset.processing_error == "Could not verify blur."
    assert asset.public_url is None


# --------------------------------------------------------------------------- #
# Human review
# --------------------------------------------------------------------------- #


@pytest.fixture
def needs_review(owner, queued):
    asset = upload(owner, jpeg_bytes(with_exif=True))
    asset.mark_needs_review("No faces detected.")
    return asset


class TestHumanApproval:
    def test_approval_writes_a_clean_public_copy(self, needs_review, owner):
        services.approve_after_review(needs_review, reviewer=owner, notes="Flat-lay, no people.")
        needs_review.refresh_from_db()

        assert needs_review.moderation_status == ModerationStatus.APPROVED
        assert needs_review.derivative.name.startswith(f"public/derivatives/{needs_review.pk}/")
        assert needs_review.reviewed_by == owner
        assert needs_review.reviewed_at is not None
        assert needs_review.review_notes == "Flat-lay, no people."
        assert needs_review.exif_stripped is True
        assert needs_review.blur_verified is False  # nothing was blurred; a person vouched
        assert needs_review.is_publishable
        assert needs_review.public_url

        with needs_review.derivative.open("rb") as handle:
            copy = Image.open(io.BytesIO(handle.read()))
        assert not copy.getexif(), "EXIF survived into the public copy"

    def test_only_needs_review_assets_can_be_approved_by_hand(self, owner, queued):
        pending = upload(owner)
        with pytest.raises(ValidationError):
            services.approve_after_review(pending, reviewer=owner)
        pending.refresh_from_db()
        assert pending.moderation_status == ModerationStatus.PENDING

    def test_rejecting_after_review(self, needs_review, owner):
        services.reject_after_review(needs_review, reviewer=owner, notes="Face visible.")
        needs_review.refresh_from_db()
        assert needs_review.moderation_status == ModerationStatus.REJECTED
        assert needs_review.reviewed_by == owner
        assert not needs_review.derivative

    def test_database_refuses_approval_with_neither_blur_nor_review(self, needs_review):
        needs_review.derivative.save("x.jpg", ContentFile(b"x"), save=False)
        with pytest.raises(IntegrityError), transaction.atomic():
            MediaAsset.objects.filter(pk=needs_review.pk).update(
                moderation_status=ModerationStatus.APPROVED,
                derivative=needs_review.derivative.name,
            )


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #


class TestAdmin:
    def test_owner_uploads_several_images_at_once(
        self, client, owner, queued, django_capture_on_commit_callbacks
    ):
        client.force_login(owner)
        files = [
            SimpleUploadedFile("a.jpg", jpeg_bytes(), "image/jpeg"),
            SimpleUploadedFile("b.jpg", jpeg_bytes(size=(20, 20)), "image/jpeg"),
        ]
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(
                reverse("admin:media_assets_mediaasset_add"),
                {"kind": AssetKind.PRODUCT, "files": files},
            )

        assert response.status_code == 302, response.content.decode()[:2000]
        assert MediaAsset.objects.count() == 2
        assert len(queued) == 2

    def test_add_page_renders(self, client, owner):
        client.force_login(owner)
        assert client.get(reverse("admin:media_assets_mediaasset_add")).status_code == 200

    def test_review_page_renders_with_preview(self, client, owner, needs_review):
        client.force_login(owner)
        response = client.get(reverse("admin:media_assets_mediaasset_change", args=[needs_review.pk]))
        assert response.status_code == 200
        assert reverse("admin:media_assets_mediaasset_review_image", args=[needs_review.pk]) in (
            response.content.decode()
        )

    def test_approve_requires_the_faces_checkbox(self, client, owner, needs_review):
        client.force_login(owner)
        url = reverse("admin:media_assets_mediaasset_change", args=[needs_review.pk])

        client.post(url, {"decision": "approve", "review_notes": ""})
        needs_review.refresh_from_db()
        assert needs_review.moderation_status == ModerationStatus.NEEDS_REVIEW

        client.post(url, {"decision": "approve", "faces_checked": "on", "review_notes": "ok"})
        needs_review.refresh_from_db()
        assert needs_review.moderation_status == ModerationStatus.APPROVED
        assert needs_review.reviewed_by == owner

    def test_review_image_is_staff_only_and_only_while_in_review(
        self, client, owner, needs_review, queued
    ):
        url = reverse("admin:media_assets_mediaasset_review_image", args=[needs_review.pk])
        assert client.get(url).status_code in (302, 403)  # anonymous

        client.force_login(owner)
        response = client.get(url)
        assert response.status_code == 200
        assert "no-store" in response["Cache-Control"]

        pending = upload(owner)
        url = reverse("admin:media_assets_mediaasset_review_image", args=[pending.pk])
        assert client.get(url).status_code == 404

    def test_staff_without_permission_cannot_upload(self, client, db):
        clerk = get_user_model().objects.create_user(
            email="clerk@ferasha.test", password="x-not-real-1", full_name="Clerk", is_staff=True
        )
        client.force_login(clerk)
        assert client.get(reverse("admin:media_assets_mediaasset_add")).status_code == 403
