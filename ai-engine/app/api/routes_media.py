"""Media privacy endpoints.

The synchronous endpoint here exists for back-office previews and for the
Phase 4 upload UI to show an immediate result. Bulk vendor ingestion goes
through the Redis worker instead - a 40MP bridal shot can take seconds, which
is far too long to hold an HTTP connection during a catalogue import.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.core.config import get_settings
from app.core.security import Principal, enforce_body_limit, require_back_office
from app.services.face_blur import BlurOutcome, blur_faces, detector
from app.services.image_ops import ImageRejected, decode_image, encode_jpeg

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])


@router.post(
    "/media/analyse",
    summary="Detect faces without modifying the image",
    dependencies=[Depends(enforce_body_limit)],
)
async def analyse(
    file: UploadFile = File(...),
    principal: Principal = Depends(require_back_office),
) -> dict:
    """Report what the detector sees. Used by moderators triaging review queues."""
    data = await file.read()
    try:
        image = decode_image(data)
    except ImageRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    boxes = detector.detect(image.pixels)
    return {
        "width": image.width,
        "height": image.height,
        "format": image.source_format,
        "faces_detected": len(boxes),
        "faces": [
            {
                "x": b.x,
                "y": b.y,
                "width": b.width,
                "height": b.height,
                "confidence": round(b.confidence, 4),
                "model": b.model,
            }
            for b in boxes
        ],
        # Restating the rule at the API boundary so no client can infer that
        # "zero faces" means "safe to publish".
        "requires_human_review": len(boxes) == 0,
    }


@router.post(
    "/media/blur",
    summary="Blur faces and return the verified derivative",
    dependencies=[Depends(enforce_body_limit)],
    responses={
        200: {"content": {"image/jpeg": {}}, "description": "Verified blurred derivative."},
        409: {"description": "No faces detected, or blur could not be verified."},
    },
)
async def blur(
    file: UploadFile = File(...),
    principal: Principal = Depends(require_back_office),
) -> Response:
    """Blur every detected face, verify irreversibility, and return the JPEG.

    **Fail-closed:** anything other than a verified blur returns 409 and no
    image bytes. The caller cannot accidentally publish an unprocessed file,
    because it is never in the response.
    """
    data = await file.read()
    try:
        image = decode_image(data)
    except ImageRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    boxes = detector.detect(image.pixels)
    processed, report = blur_faces(image.pixels, boxes)

    if not report.is_publishable:
        # 409, not 400: the request was well-formed, but the resulting state
        # conflicts with the publication rule. Mirrors the Phase 2 convention
        # for IllegalTransition.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "reason": str(report.outcome),
                "message": report.detail,
                "faces_detected": report.faces_detected,
                "next_step": (
                    "route_to_human_review"
                    if report.outcome == BlurOutcome.NO_FACES_DETECTED
                    else "reject_asset"
                ),
            },
        )

    jpeg = encode_jpeg(processed)
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={
            "X-Faces-Detected": str(report.faces_detected),
            "X-Blur-Escalations": str(report.escalations),
            "X-Blur-Verified": "true",
            "Cache-Control": "no-store",
        },
    )


@router.get("/media/policy", summary="The privacy policy this engine enforces")
async def policy() -> dict:
    """Machine-readable statement of the guarantees, for audit and for tests."""
    settings = get_settings()
    return {
        "detection_models": ["mediapipe_short_range", "mediapipe_full_range"],
        "detection_confidence": settings.detection_confidence,
        "face_margin": settings.face_margin,
        "zero_detection_policy": "human_review",
        "verification": {
            "max_residual_detail": settings.max_residual_detail,
            "max_highfreq_ratio": settings.max_highfreq_ratio,
            "max_escalations": settings.max_blur_escalations,
        },
        "exif_stripped": True,
        "accepted_formats": list(settings.allowed_formats),
        "max_pixels": settings.max_pixels,
    }
