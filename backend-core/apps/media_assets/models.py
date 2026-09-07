"""Media assets and the privacy moderation state machine.

Ferasha's vendor imagery contains identifiable people who have not consented to
appear on the storefront. Under the DPDP Act 2023 a facial image is personal
data, so every asset must pass through automated face-blurring (Phase 3) before
it can be served.

The model is deliberately **fail-closed**:

* the original is stored under a private prefix that is never publicly routed;
* only ``derivative`` is servable, and only when status is APPROVED;
* the default status is PENDING, so an asset that is created and then abandoned
  by a crashed worker is never publishable;
* zero detected faces routes to NEEDS_REVIEW, not to APPROVED - MediaPipe
  reliably misses veiled and profile faces, which are common in this catalogue.
"""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class ModerationStatus(models.TextChoices):
    PENDING = "pending", _("Pending processing")
    PROCESSING = "processing", _("Processing")
    NEEDS_REVIEW = "needs_review", _("Needs human review")
    APPROVED = "approved", _("Approved for publication")
    REJECTED = "rejected", _("Rejected")
    FAILED = "failed", _("Processing failed")


#: The only status at which a derivative may be served publicly.
PUBLISHABLE_STATUSES = frozenset({ModerationStatus.APPROVED})


class AssetKind(models.TextChoices):
    PRODUCT = "product", _("Product image")
    REVIEW = "review", _("Customer review photo")
    LOOKBOOK = "lookbook", _("Lookbook / editorial")
    VENDOR_DOC = "vendor_doc", _("Vendor document")


def private_upload_path(instance: MediaAsset, filename: str) -> str:
    """Originals live under a prefix that is never mapped to a public URL."""
    return f"private/originals/{instance.id}/{filename}"


def public_upload_path(instance: MediaAsset, filename: str) -> str:
    return f"public/derivatives/{instance.id}/{filename}"


class MediaAsset(BaseModel):
    """An uploaded image and its privacy-processed derivative."""

    kind = models.CharField(max_length=12, choices=AssetKind.choices, default=AssetKind.PRODUCT)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_assets"
    )

    original = models.FileField(upload_to=private_upload_path, max_length=512)
    derivative = models.FileField(
        upload_to=public_upload_path, max_length=512, blank=True, null=True
    )

    #: SHA-256 of the original. Makes worker processing idempotent and detects
    #: an original being swapped after approval.
    checksum = models.CharField(max_length=64, db_index=True)
    content_type = models.CharField(max_length=64)
    byte_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    moderation_status = models.CharField(
        max_length=14,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
        db_index=True,
    )
    faces_detected = models.PositiveSmallIntegerField(default=0)
    blur_verified = models.BooleanField(
        default=False,
        help_text=_("Irreversibility check passed: variance collapsed inside every mask."),
    )
    exif_stripped = models.BooleanField(default=False)

    processing_started_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_assets",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=["moderation_status", "created_at"], name="asset_status_created_idx"
            ),
            models.Index(fields=["kind", "moderation_status"], name="asset_kind_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(moderation_status__in=[c[0] for c in ModerationStatus.choices]),
                name="asset_status_valid",
            ),
            # The core privacy invariant, enforced by the database: an asset
            # cannot be APPROVED without a derivative and a verified blur.
            models.CheckConstraint(
                condition=~models.Q(moderation_status=ModerationStatus.APPROVED)
                | (
                    models.Q(blur_verified=True)
                    & models.Q(derivative__isnull=False)
                    & ~models.Q(derivative="")
                ),
                name="asset_approved_requires_verified_derivative",
            ),
            models.CheckConstraint(
                condition=models.Q(byte_size__gt=0), name="asset_byte_size_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.id} [{self.moderation_status}]"

    def clean(self):
        super().clean()
        if self.moderation_status == ModerationStatus.APPROVED:
            if not self.derivative:
                raise ValidationError(
                    {"derivative": _("An approved asset must have a processed derivative.")}
                )
            if not self.blur_verified:
                raise ValidationError(
                    {
                        "blur_verified": _(
                            "An approved asset must have passed blur verification."
                        )
                    }
                )

    @property
    def is_publishable(self) -> bool:
        return (
            self.moderation_status in PUBLISHABLE_STATUSES
            and bool(self.derivative)
            and self.blur_verified
        )

    @property
    def public_url(self) -> str | None:
        """The only URL that may ever be handed to a browser.

        Returns None unless the asset is publishable. Callers must not fall
        back to ``original`` - that file is not publicly routable by design.
        """
        if not self.is_publishable:
            return None
        return self.derivative.url

    @staticmethod
    def compute_checksum(file_obj) -> str:
        digest = hashlib.sha256()
        for chunk in iter(lambda: file_obj.read(8192), b""):
            digest.update(chunk)
        file_obj.seek(0)
        return digest.hexdigest()

    # -- State transitions ---------------------------------------------------
    def mark_processing(self) -> None:
        self.moderation_status = ModerationStatus.PROCESSING
        self.processing_started_at = timezone.now()
        self.attempts += 1
        self.save(
            update_fields=[
                "moderation_status", "processing_started_at", "attempts", "updated_at",
            ]
        )

    def mark_approved(self, *, faces: int, blur_verified: bool) -> None:
        """Approve. Refuses unless the privacy guarantees actually hold."""
        if not self.derivative:
            raise ValidationError("Cannot approve an asset without a derivative.")
        if not blur_verified:
            raise ValidationError("Cannot approve an asset whose blur was not verified.")
        if faces == 0:
            # MediaPipe misses veiled and profile faces routinely. Zero
            # detections is a reason for a human to look, not to publish.
            raise ValidationError(
                "Zero detected faces requires human review; auto-approval is refused."
            )
        self.faces_detected = faces
        self.blur_verified = True
        self.moderation_status = ModerationStatus.APPROVED
        self.processed_at = timezone.now()
        self.processing_error = ""
        self.save(
            update_fields=[
                "faces_detected", "blur_verified", "moderation_status",
                "processed_at", "processing_error", "updated_at",
            ]
        )

    def mark_needs_review(self, reason: str) -> None:
        self.moderation_status = ModerationStatus.NEEDS_REVIEW
        self.processing_error = reason
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                "moderation_status", "processing_error", "processed_at", "updated_at",
            ]
        )

    def mark_failed(self, error: str) -> None:
        self.moderation_status = ModerationStatus.FAILED
        self.processing_error = error[:2000]
        self.save(
            update_fields=["moderation_status", "processing_error", "updated_at"]
        )
