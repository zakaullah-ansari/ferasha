"""Product reviews with verified-purchase and fit feedback.

Fit feedback is the highest-value review data for a tailoring business: it
tells a prospective customer whether to size up, and it tells the atelier which
products have a systematic sizing problem.
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel


class FitFeedback(models.TextChoices):
    RAN_SMALL = "ran_small", _("Ran small")
    TRUE_TO_SIZE = "true_to_size", _("True to size")
    RAN_LARGE = "ran_large", _("Ran large")


class ReviewStatus(models.TextChoices):
    PENDING = "pending", _("Pending moderation")
    PUBLISHED = "published", _("Published")
    REJECTED = "rejected", _("Rejected")


class Review(BaseModel):
    product = models.ForeignKey(
        "catalog.Product", on_delete=models.CASCADE, related_name="reviews"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    #: Set when the reviewer actually bought the item. Drives the verified badge.
    order_line = models.ForeignKey(
        "orders.OrderLine",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=140, blank=True)
    body = models.TextField(blank=True)

    fit_feedback = models.CharField(max_length=14, choices=FitFeedback.choices, blank=True)
    #: Whether the garment's modesty attributes matched the listing. A mismatch
    #: is a trust failure and must be visible to operations, not buried.
    modesty_as_described = models.BooleanField(null=True, blank=True)

    status = models.CharField(
        max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.PENDING, db_index=True
    )
    helpful_count = models.PositiveIntegerField(default=0)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="moderated_reviews",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["product", "author"], name="one_review_per_product_per_user"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[c[0] for c in ReviewStatus.choices]),
                name="review_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "status"], name="review_product_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} {self.rating}* by {self.author_id}"

    @property
    def is_verified_purchase(self) -> bool:
        return self.order_line_id is not None


class ReviewPhoto(BaseModel):
    """Customer photo. Routed through the Phase 3 privacy pipeline like any
    other image - a customer photo is as likely to contain a face as a vendor's.
    """

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="photos")
    asset = models.ForeignKey(
        "media_assets.MediaAsset", on_delete=models.PROTECT, related_name="review_photos"
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order",)

    def __str__(self) -> str:
        return f"Photo for review {self.review_id}"
