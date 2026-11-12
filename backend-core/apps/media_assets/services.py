"""Getting an image into the privacy pipeline, and a person's sign-off on it.

The flow, end to end:

1. ``create_from_upload`` checks the file really is a JPEG/PNG/WebP within the
   size limits, stores it under the private prefix, and - once the row is
   committed - queues a blur job for the AI worker.
2. The worker fetches the original through ``original_download_path``: a
   short-lived link signed with Django's SECRET_KEY, bound to the asset and to
   its checksum, and dead the moment the asset settles.
3. The worker reports back over the HMAC callback (views.py). A verified blur
   approves; no face found goes to NEEDS_REVIEW.
4. ``approve_after_review`` is the only other road to APPROVED: a person has
   looked at the original and vouches there is no face. Django then writes the
   public copy itself (orientation applied, EXIF/GPS dropped), so nothing that
   has not been checked is ever in public storage.
"""

from __future__ import annotations

import io
import json
import logging
from functools import lru_cache

import redis
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.catalog.models import Product
from apps.catalog.services import sync_face_coverage

from .models import AssetKind, MediaAsset, ModerationStatus

logger = logging.getLogger(__name__)

#: Pillow format name -> the content type we record. Matches the engine's
#: allowed_formats; anything else would only be rejected there later.
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

_LINK_SALT = "media_assets.original-download"

# Decompression-bomb guard, aligned with the engine's max_pixels.
Image.MAX_IMAGE_PIXELS = 50_000_000


# --------------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------------- #


def inspect_image(data: bytes) -> tuple[str, int, int]:
    """Return (content_type, width, height), or refuse the file."""
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()  # structural check; the image is unusable afterwards
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValidationError(_("This file is not a readable image.")) from exc

    if fmt not in ALLOWED_FORMATS:
        raise ValidationError(
            _("Only JPEG, PNG and WebP images are accepted (this one is %(fmt)s).")
            % {"fmt": fmt or "unknown"}
        )
    limit = settings.MEDIA_UPLOAD_MAX_DIMENSION
    if width > limit or height > limit:
        raise ValidationError(
            _("Images can be at most %(limit)s pixels on a side.") % {"limit": limit}
        )
    return ALLOWED_FORMATS[fmt], width, height


def create_from_upload(file, *, kind: str = AssetKind.PRODUCT, uploaded_by) -> MediaAsset:
    """Store one uploaded file as a PENDING asset and queue it for blurring."""
    if file.size > settings.MEDIA_UPLOAD_MAX_BYTES:
        raise ValidationError(
            _("%(name)s is larger than %(mb)s MB.")
            % {"name": file.name, "mb": settings.MEDIA_UPLOAD_MAX_BYTES // (1024 * 1024)}
        )
    data = file.read()
    content_type, width, height = inspect_image(data)

    with transaction.atomic():
        asset = MediaAsset(
            kind=kind,
            uploaded_by=uploaded_by,
            checksum=MediaAsset.compute_checksum(io.BytesIO(data)),
            content_type=content_type,
            byte_size=len(data),
            width=width,
            height=height,
        )
        # Only the extension of the client's name is kept; the rest of the
        # path is ours (private/originals/<id>/).
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
        asset.original.save(f"original.{extension}", ContentFile(data), save=False)
        asset.save()
        transaction.on_commit(lambda: enqueue_blur(asset))
    return asset


# --------------------------------------------------------------------------- #
# Queue + the worker's download link
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=1)
def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL)


def _push_job(raw: str) -> None:
    _redis().lpush(settings.MEDIA_BLUR_QUEUE, raw)


def original_download_path(asset: MediaAsset) -> str:
    """Path + query the worker may GET the original from, for a limited time."""
    token = signing.dumps(
        {"id": str(asset.pk), "checksum": asset.checksum}, salt=_LINK_SALT, compress=True
    )
    return f"{reverse('media_assets:original', args=[asset.pk])}?token={token}"


def read_download_token(token: str, asset: MediaAsset) -> bool:
    """True only for an unexpired token minted for this asset's current file."""
    try:
        claims = signing.loads(token, salt=_LINK_SALT, max_age=settings.MEDIA_ORIGINAL_LINK_MAX_AGE)
    except signing.BadSignature:  # includes SignatureExpired
        return False
    return claims.get("id") == str(asset.pk) and claims.get("checksum") == asset.checksum


def enqueue_blur(asset: MediaAsset) -> None:
    """Hand the asset to the AI worker. Safe to call again (the worker is idempotent)."""
    job = {
        "asset_id": str(asset.pk),
        "checksum": asset.checksum,
        "download_url": settings.BACKEND_INTERNAL_URL.rstrip("/") + original_download_path(asset),
        "attempt": 0,
    }
    try:
        _push_job(json.dumps(job, sort_keys=True))
    except redis.RedisError:
        # The asset stays PENDING (never publishable) and "Send to the privacy
        # check again" in the admin re-queues it. Loud, not silent.
        logger.exception("Could not queue blur job for asset %s", asset.pk)
        raise


# --------------------------------------------------------------------------- #
# Human review
# --------------------------------------------------------------------------- #


def _clean_copy(asset: MediaAsset) -> bytes:
    """Re-encode the original: orientation applied, every bit of metadata dropped."""
    with asset.original.open("rb") as handle:
        data = handle.read()
    if MediaAsset.compute_checksum(io.BytesIO(data)) != asset.checksum:
        raise ValidationError(_("The stored original changed after upload; not approving it."))
    with Image.open(io.BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        clean = Image.new("RGB", image.size)
        clean.paste(image)  # fresh image: no info dict, no EXIF/XMP/ICC carried over
    buffer = io.BytesIO()
    clean.save(buffer, "JPEG", quality=88, optimize=True)
    return buffer.getvalue()


def _resync_products(asset: MediaAsset) -> None:
    for product in Product.objects.filter(images__asset=asset).distinct():
        sync_face_coverage(product)


def approve_after_review(asset: MediaAsset, *, reviewer, notes: str = "") -> MediaAsset:
    """A person has checked the image and vouches it shows no face."""
    with transaction.atomic():
        asset = MediaAsset.objects.select_for_update().get(pk=asset.pk)
        if asset.moderation_status != ModerationStatus.NEEDS_REVIEW:
            raise ValidationError(
                _("Only images waiting for review can be approved by hand (this one is %(s)s).")
                % {"s": asset.get_moderation_status_display()}
            )
        asset.derivative.save(f"{asset.pk}.jpg", ContentFile(_clean_copy(asset)), save=False)
        asset.exif_stripped = True
        asset.reviewed_by = reviewer
        asset.reviewed_at = timezone.now()
        asset.review_notes = notes
        asset.moderation_status = ModerationStatus.APPROVED
        asset.full_clean(exclude=["original", "uploaded_by"])
        asset.save()
        _resync_products(asset)
    return asset


def reject_after_review(asset: MediaAsset, *, reviewer, notes: str = "") -> MediaAsset:
    with transaction.atomic():
        asset = MediaAsset.objects.select_for_update().get(pk=asset.pk)
        if asset.moderation_status != ModerationStatus.NEEDS_REVIEW:
            raise ValidationError(_("Only images waiting for review can be rejected here."))
        asset.reviewed_by = reviewer
        asset.reviewed_at = timezone.now()
        asset.review_notes = notes
        asset.save(update_fields=["reviewed_by", "reviewed_at", "review_notes", "updated_at"])
        asset.mark_rejected(notes or "Rejected after human review.")
        _resync_products(asset)
    return asset
