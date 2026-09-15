"""Callback endpoints consumed by the AI engine worker.

These endpoints are authenticated by HMAC, not by a user session, because the
caller is a service with no user context. They are deliberately the only way
an asset transitions out of PENDING.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.parsers import BaseParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .callbacks import parse_body, verify_signature
from .models import MediaAsset, ModerationStatus

logger = logging.getLogger(__name__)

#: Outcomes the worker is permitted to report. Anything else is a protocol
#: violation and is refused rather than guessed at.
VALID_OUTCOMES = frozenset({"approved", "needs_review", "rejected", "failed"})


class SignatureChallengeAuthentication(BaseAuthentication):
    """Contributes only a WWW-Authenticate challenge.

    Authentication really happens in ``verify_signature``. Without an
    authenticator declared, DRF downgrades every AuthenticationFailed to 403;
    declaring this one makes the endpoint answer 401 as an unauthenticated
    service request should.
    """

    def authenticate(self, request):
        return None

    def authenticate_header(self, request):
        return 'Signature realm="ferasha-ai-engine"'


class RawBytesParser(BaseParser):
    """Passes the body through untouched, for binary derivative uploads."""

    media_type = "image/jpeg"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()


class MediaCallbackView(APIView):
    """``POST /api/v1/media/callback/`` - report a processing outcome."""

    authentication_classes = [SignatureChallengeAuthentication]
    permission_classes = [AllowAny]  # Authentication is the HMAC signature.

    @extend_schema(
        operation_id="media_callback",
        request=None,
        responses={
            200: OpenApiResponse(description="Outcome recorded."),
            401: OpenApiResponse(description="Missing, invalid or replayed signature."),
            404: OpenApiResponse(description="Unknown asset."),
            409: OpenApiResponse(description="Checksum mismatch - original changed."),
        },
    )
    def post(self, request):
        body = parse_body(request)
        verify_signature(request, body)

        asset_id = body.get("asset_id")
        outcome = body.get("outcome")
        if not asset_id or outcome not in VALID_OUTCOMES:
            return Response(
                {"detail": "Callback must supply an asset_id and a known outcome."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                asset = MediaAsset.objects.select_for_update().get(pk=asset_id)
            except (MediaAsset.DoesNotExist, DjangoValidationError, ValueError):
                return Response(
                    {"detail": "Unknown asset."}, status=status.HTTP_404_NOT_FOUND
                )

            # A callback carrying a stale checksum refers to a different
            # version of the file than the one now on disk. Applying it could
            # approve image B on the strength of having blurred image A.
            if body.get("checksum") and body["checksum"] != asset.checksum:
                logger.warning("Checksum mismatch on callback for asset %s", asset_id)
                return Response(
                    {"detail": "Checksum does not match the stored original."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Idempotency: the worker retries, and a duplicate delivery must
            # not flip an already-settled asset or double-count anything.
            if asset.moderation_status in {
                ModerationStatus.APPROVED,
                ModerationStatus.REJECTED,
            }:
                return Response(
                    {"detail": "Asset already settled.", "status": asset.moderation_status}
                )

            detail = str(body.get("detail", ""))[:1000]
            try:
                if outcome == "approved":
                    asset.mark_approved(
                        faces=int(body.get("faces_detected", 0)),
                        blur_verified=bool(body.get("blur_verified", False)),
                    )
                elif outcome == "needs_review":
                    asset.mark_needs_review(detail or "Flagged for human review.")
                elif outcome == "rejected":
                    asset.mark_rejected(detail or "Rejected by the privacy pipeline.")
                else:
                    asset.mark_failed(detail or "Processing failed.")
            except DjangoValidationError as exc:
                # The model refused the transition. That is the last line of
                # defence working, so surface it rather than swallowing it.
                logger.error("Refused callback transition for %s: %s", asset_id, exc)
                return Response(
                    {"detail": exc.messages}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

        return Response({"detail": "Recorded.", "status": asset.moderation_status})


class MediaDerivativeUploadView(APIView):
    """``PUT /api/v1/media/<uuid>/derivative/`` - store the blurred image."""

    authentication_classes = [SignatureChallengeAuthentication]
    permission_classes = [AllowAny]
    parser_classes = [RawBytesParser]

    @extend_schema(
        operation_id="media_derivative_upload",
        request=bytes,
        responses={
            200: OpenApiResponse(description="Derivative stored."),
            401: OpenApiResponse(description="Missing or invalid signature."),
            404: OpenApiResponse(description="Unknown asset."),
        },
    )
    def put(self, request, asset_id):
        try:
            asset = MediaAsset.objects.get(pk=asset_id)
        except (MediaAsset.DoesNotExist, DjangoValidationError, ValueError):
            return Response({"detail": "Unknown asset."}, status=status.HTTP_404_NOT_FOUND)

        # The signed payload names the asset and the checksum of the original
        # it was derived from. Binding both means a captured upload cannot be
        # replayed against a different asset, nor against the same asset after
        # its original has been swapped.
        checksum = request.headers.get("X-Ferasha-Checksum", "")
        verify_signature(request, {"asset_id": str(asset_id), "checksum": checksum})

        if checksum != asset.checksum:
            return Response(
                {"detail": "Checksum does not match the stored original."},
                status=status.HTTP_409_CONFLICT,
            )

        payload = request.data
        if not isinstance(payload, bytes) or not payload:
            return Response(
                {"detail": "Derivative body was empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset.derivative.save(f"{asset.pk}.jpg", ContentFile(payload), save=True)
        return Response({"detail": "Derivative stored.", "bytes": len(payload)})
