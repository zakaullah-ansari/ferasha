"""Privacy pipeline model tests.

The invariant under test: an unblurred face must never become publishable. The
model is fail-closed, and these tests attempt to defeat that from every angle
the database and the Python API allow.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction

from apps.media_assets.models import MediaAsset, ModerationStatus
from tests.factories import make_vendor

pytestmark = pytest.mark.django_db


def make_asset(**kw):
    defaults = dict(
        uploaded_by=make_vendor(),
        original=SimpleUploadedFile("photo.jpg", b"fake-image-bytes"),
        checksum="a" * 64,
        content_type="image/jpeg",
        byte_size=1024,
    )
    defaults.update(kw)
    return MediaAsset.objects.create(**defaults)


class TestDefaultsAreFailClosed:
    def test_new_asset_is_pending(self):
        assert make_asset().moderation_status == ModerationStatus.PENDING

    def test_new_asset_is_not_publishable(self):
        assert make_asset().is_publishable is False

    def test_pending_asset_has_no_public_url(self):
        """The original must never be offered as a fallback."""
        assert make_asset().public_url is None

    def test_abandoned_asset_never_becomes_publishable(self):
        """Simulates a worker crashing mid-job."""
        asset = make_asset()
        asset.mark_processing()
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.PROCESSING
        assert asset.is_publishable is False
        assert asset.public_url is None


class TestApprovalGuards:
    def test_cannot_approve_without_derivative(self):
        asset = make_asset()
        with pytest.raises(ValidationError, match="without a derivative"):
            asset.mark_approved(faces=1, blur_verified=True)

    def test_cannot_approve_without_blur_verification(self):
        asset = make_asset(
            derivative=SimpleUploadedFile("blurred.jpg", b"blurred-bytes")
        )
        with pytest.raises(ValidationError, match="blur was not verified"):
            asset.mark_approved(faces=1, blur_verified=False)

    def test_zero_detections_cannot_auto_approve(self):
        """MediaPipe misses veiled and profile faces; zero is not 'safe'."""
        asset = make_asset(
            derivative=SimpleUploadedFile("blurred.jpg", b"blurred-bytes")
        )
        with pytest.raises(ValidationError, match="human review"):
            asset.mark_approved(faces=0, blur_verified=True)

    def test_valid_approval_succeeds(self):
        asset = make_asset(
            derivative=SimpleUploadedFile("blurred.jpg", b"blurred-bytes")
        )
        asset.mark_approved(faces=2, blur_verified=True)
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.APPROVED
        assert asset.is_publishable is True
        assert asset.public_url is not None

    def test_database_rejects_approved_without_verified_blur(self):
        """Bypassing the Python API must still fail at the database."""
        asset = make_asset(
            derivative=SimpleUploadedFile("blurred.jpg", b"blurred-bytes")
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                MediaAsset.objects.filter(pk=asset.pk).update(
                    moderation_status=ModerationStatus.APPROVED, blur_verified=False
                )

    def test_database_rejects_approved_without_derivative(self):
        asset = make_asset()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                MediaAsset.objects.filter(pk=asset.pk).update(
                    moderation_status=ModerationStatus.APPROVED, blur_verified=True
                )

    def test_clean_rejects_inconsistent_approval(self):
        asset = make_asset()
        asset.moderation_status = ModerationStatus.APPROVED
        with pytest.raises(ValidationError):
            asset.full_clean()


class TestReviewAndFailure:
    def test_needs_review_is_not_publishable(self):
        asset = make_asset()
        asset.mark_needs_review("No faces detected")
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.NEEDS_REVIEW
        assert asset.is_publishable is False

    def test_failure_is_not_publishable(self):
        asset = make_asset()
        asset.mark_failed("Decode error")
        asset.refresh_from_db()
        assert asset.moderation_status == ModerationStatus.FAILED
        assert asset.is_publishable is False

    def test_attempts_increment(self):
        asset = make_asset()
        asset.mark_processing()
        asset.mark_processing()
        asset.refresh_from_db()
        assert asset.attempts == 2


class TestStorageSeparation:
    def test_original_stored_under_private_prefix(self):
        asset = make_asset()
        assert asset.original.name.startswith("private/")

    def test_derivative_stored_under_public_prefix(self):
        asset = make_asset(
            derivative=SimpleUploadedFile("blurred.jpg", b"blurred-bytes")
        )
        assert asset.derivative.name.startswith("public/")

    def test_checksum_helper(self):
        import io

        digest = MediaAsset.compute_checksum(io.BytesIO(b"hello"))
        assert digest == (
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )


class TestProductImageGuard:
    def test_unapproved_asset_cannot_be_published(self):
        """The storefront relation refuses anything not through the pipeline."""
        from apps.catalog.models import ProductImage
        from tests.factories import make_product

        asset = make_asset()
        image = ProductImage(product=make_product(), asset=asset, alt_text="Bridal lehenga")
        with pytest.raises(ValidationError, match="privacy pipeline"):
            image.full_clean(exclude=["product"])

    def test_approved_asset_can_be_published(self):
        from apps.catalog.models import ProductImage
        from tests.factories import make_product

        asset = make_asset(
            derivative=SimpleUploadedFile("blurred.jpg", b"blurred-bytes")
        )
        asset.mark_approved(faces=1, blur_verified=True)
        image = ProductImage(product=make_product(), asset=asset, alt_text="Bridal lehenga")
        image.full_clean(exclude=["product"])
        image.save()
        assert image.pk

    def test_asset_is_protected_from_deletion_while_published(self):
        from apps.catalog.models import ProductImage
        from tests.factories import make_product

        asset = make_asset(
            derivative=SimpleUploadedFile("blurred.jpg", b"blurred-bytes")
        )
        asset.mark_approved(faces=1, blur_verified=True)
        ProductImage.objects.create(
            product=make_product(), asset=asset, alt_text="Alt"
        )
        with pytest.raises(Exception):
            asset.delete()
