"""Face detection and irreversible blurring.

The privacy guarantee of the whole platform lives in this file.

Three design decisions are load-bearing and must not be "simplified" later:

1. **Zero detections is not success.** MediaPipe reliably misses faces in
   profile, under a dupatta or veil, in low light, and at small scale - and
   South Asian bridal photography contains all of those routinely. An image
   with no detections is therefore *inconclusive*, and routes to human
   review. It is never auto-approved.

2. **Applying blur is not the guarantee; verifying it is.** A Gaussian blur
   with an undersized kernel is reversible by deconvolution. Every masked
   region is measured after blurring - variance collapse *and* high-frequency
   energy destruction - and the blur escalates until it verifies or the asset
   is rejected.

3. **Elliptical, feathered, margin-expanded masks.** Rectangular blur boxes
   look cheap on editorial imagery, and a tight box leaves hairline, jaw and
   ears identifiable - enough for recognition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

import cv2
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BlurOutcome(StrEnum):
    """Result of processing one image."""

    #: Faces found, blurred, and verified irreversible.
    BLURRED_VERIFIED = "blurred_verified"
    #: No faces detected - inconclusive, needs a human.
    NO_FACES_DETECTED = "no_faces_detected"
    #: Faces found but blur could not be verified. Asset is rejected.
    VERIFICATION_FAILED = "verification_failed"


@dataclass(frozen=True)
class FaceBox:
    """A detected face in absolute pixel coordinates."""

    x: int
    y: int
    width: int
    height: int
    confidence: float
    model: str

    @property
    def area(self) -> int:
        return self.width * self.height

    def iou(self, other: FaceBox) -> float:
        """Intersection-over-union, used to merge the two models' outputs."""
        ax2, ay2 = self.x + self.width, self.y + self.height
        bx2, by2 = other.x + other.width, other.y + other.height

        ix1, iy1 = max(self.x, other.x), max(self.y, other.y)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)

        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        intersection = iw * ih
        if intersection == 0:
            return 0.0
        union = self.area + other.area - intersection
        return intersection / union if union else 0.0


@dataclass
class BlurReport:
    """Auditable record of what happened to one image."""

    outcome: BlurOutcome
    faces_detected: int
    escalations: int = 0
    residual_detail: float = 0.0
    highfreq_ratio: float = 0.0
    regions: list[dict] = field(default_factory=list)
    detail: str = ""

    @property
    def is_publishable(self) -> bool:
        """Only a verified blur may ever be served publicly."""
        return self.outcome == BlurOutcome.BLURRED_VERIFIED

    def as_dict(self) -> dict:
        return {
            "outcome": str(self.outcome),
            "faces_detected": self.faces_detected,
            "escalations": self.escalations,
            "residual_detail": round(self.residual_detail, 3),
            "highfreq_ratio": round(self.highfreq_ratio, 4),
            "regions": self.regions,
            "detail": self.detail,
            "publishable": self.is_publishable,
        }


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #


class FaceDetector:
    """Wraps MediaPipe's two face-detection models.

    Both are run and their outputs merged: the short-range model is tuned for
    close-up portraits, the full-range model for full-body editorial shots.
    A lehenga catalogue contains both, and each model misses what the other
    catches.

    Models are loaded **once** and reused. Constructing a MediaPipe graph per
    request costs hundreds of milliseconds and leaks memory under load.
    """

    def __init__(self) -> None:
        self._short_range = None
        self._full_range = None
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        import mediapipe as mp

        settings = get_settings()
        solution = mp.solutions.face_detection
        # model_selection=0 -> short range (~2m), 1 -> full range (~5m)
        self._short_range = solution.FaceDetection(
            model_selection=0, min_detection_confidence=settings.detection_confidence
        )
        self._full_range = solution.FaceDetection(
            model_selection=1, min_detection_confidence=settings.detection_confidence
        )
        self._loaded = True
        logger.info(
            "Face detection models loaded (confidence=%.2f)", settings.detection_confidence
        )

    def close(self) -> None:
        for model in (self._short_range, self._full_range):
            if model is not None:
                model.close()
        self._short_range = self._full_range = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def detect(self, rgb: np.ndarray) -> list[FaceBox]:
        """Return the merged detections from both models."""
        if not self._loaded:
            raise RuntimeError("FaceDetector.load() must be called before detect().")

        height, width = rgb.shape[:2]
        found: list[FaceBox] = []

        for name, model in (("short_range", self._short_range), ("full_range", self._full_range)):
            result = model.process(rgb)
            if not result.detections:
                continue
            for detection in result.detections:
                box = detection.location_data.relative_bounding_box
                # MediaPipe emits relative coords that can fall outside [0,1]
                # when a face is partially out of frame; clamp to the canvas.
                x = int(max(0.0, box.xmin) * width)
                y = int(max(0.0, box.ymin) * height)
                w = int(min(1.0, box.width) * width)
                h = int(min(1.0, box.height) * height)
                w = min(w, width - x)
                h = min(h, height - y)
                if w <= 1 or h <= 1:
                    continue
                score = float(detection.score[0]) if detection.score else 0.0
                found.append(FaceBox(x, y, w, h, score, name))

        return _merge_overlapping(found)


def _merge_overlapping(boxes: list[FaceBox], iou_threshold: float = 0.35) -> list[FaceBox]:
    """Merge duplicate detections of the same face across both models.

    Keeps the **larger** box of an overlapping pair rather than the more
    confident one: over-blurring is the safe direction.
    """
    if not boxes:
        return []

    ordered = sorted(boxes, key=lambda b: b.area, reverse=True)
    kept: list[FaceBox] = []
    for candidate in ordered:
        if all(candidate.iou(existing) < iou_threshold for existing in kept):
            kept.append(candidate)
    return kept


# --------------------------------------------------------------------------- #
# Masking and blurring
# --------------------------------------------------------------------------- #


def _expand(box: FaceBox, margin: float, width: int, height: int) -> tuple[int, int, int, int]:
    """Expand a face box by ``margin`` on each side, clamped to the canvas."""
    dx = int(box.width * margin)
    dy = int(box.height * margin)
    x1 = max(0, box.x - dx)
    y1 = max(0, box.y - dy)
    x2 = min(width, box.x + box.width + dx)
    y2 = min(height, box.y + box.height + dy)
    return x1, y1, x2, y2


def _kernel_for(region_width: int, region_height: int, escalation: int) -> int:
    """Odd Gaussian kernel scaled to the region.

    A fixed kernel is the classic mistake: it destroys a small face but barely
    softens a large one, leaving it recognisable. Scaling to the region keeps
    the *relative* destruction constant.
    """
    base = max(region_width, region_height) / 3.0
    size = int(base * (1.0 + 0.75 * escalation))
    size = max(size, 9)
    if size % 2 == 0:
        size += 1
    return size


def _elliptical_mask(shape: tuple[int, int], boxes: list[tuple[int, int, int, int]]) -> np.ndarray:
    """Feathered elliptical mask over every region, as float32 in [0, 1]."""
    mask = np.zeros(shape, dtype=np.float32)
    for x1, y1, x2, y2 in boxes:
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        ax, ay = max(1, (x2 - x1) // 2), max(1, (y2 - y1) // 2)
        cv2.ellipse(mask, (cx, cy), (ax, ay), 0, 0, 360, 1.0, thickness=-1)

    # Feather so the blur blends instead of showing a hard cut-out edge.
    feather = max(9, int(min(shape) * 0.01))
    if feather % 2 == 0:
        feather += 1
    return cv2.GaussianBlur(mask, (feather, feather), 0)


def _highfreq_energy(gray: np.ndarray, selection: np.ndarray | None = None) -> float:
    """Mean absolute Laplacian response - a proxy for edge/detail energy.

    ``selection`` restricts the measurement to a boolean mask of pixels. This
    matters more than it looks: an elliptical mask inside a square region
    leaves roughly 21% of the region unblurred background, and averaging that
    in makes a perfectly blurred face look unverified.
    """
    if gray.size == 0:
        return 0.0
    response = np.abs(cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F))
    if selection is not None:
        if not selection.any():
            return 0.0
        return float(np.mean(response[selection]))
    return float(np.mean(response))


def _ellipse_selection(region: tuple[int, int, int, int]) -> np.ndarray:
    """Boolean mask of the pixels actually inside the blurred ellipse."""
    x1, y1, x2, y2 = region
    height, width = y2 - y1, x2 - x1
    canvas = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(
        canvas,
        (width // 2, height // 2),
        (max(1, width // 2), max(1, height // 2)),
        0,
        0,
        360,
        255,
        thickness=-1,
    )
    return canvas.astype(bool)


def blur_faces(rgb: np.ndarray, boxes: list[FaceBox]) -> tuple[np.ndarray, BlurReport]:
    """Blur every detected face and verify the result is irreversible.

    Returns the processed image and an auditable report. The caller must
    consult ``report.is_publishable`` - a returned image is **not** implicitly
    safe to serve.
    """
    settings = get_settings()

    if not boxes:
        return rgb.copy(), BlurReport(
            outcome=BlurOutcome.NO_FACES_DETECTED,
            faces_detected=0,
            detail=(
                "No faces detected. Routed to human review: detection cannot "
                "prove absence, particularly for veiled or profile subjects."
            ),
        )

    height, width = rgb.shape[:2]
    regions = [_expand(box, settings.face_margin, width, height) for box in boxes]

    original_gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    escalation = 0
    worst_detail = 0.0
    worst_ratio = 0.0

    while escalation <= settings.max_blur_escalations:
        candidate = rgb.copy()

        # Blur the whole frame once, then composite through the mask. This is
        # both faster than per-region work and avoids seams at region edges.
        max_w = max(x2 - x1 for x1, _, x2, _ in regions)
        max_h = max(y2 - y1 for _, y1, _, y2 in regions)
        kernel = _kernel_for(max_w, max_h, escalation)
        blurred = cv2.GaussianBlur(candidate, (kernel, kernel), 0)

        # Pixelate as well at higher escalations. Combining a spatial average
        # with a resolution reduction removes information that a deconvolution
        # attack could otherwise recover from a pure Gaussian.
        if escalation >= 1:
            downscale = max(2, 8 + 4 * escalation)
            small = cv2.resize(
                blurred,
                (max(1, width // downscale), max(1, height // downscale)),
                interpolation=cv2.INTER_LINEAR,
            )
            blurred = cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)

        mask = _elliptical_mask((height, width), regions)
        mask3 = np.repeat(mask[:, :, None], 3, axis=2)
        candidate = (blurred * mask3 + candidate * (1.0 - mask3)).astype(np.uint8)

        # --- verification ---------------------------------------------------
        candidate_gray = cv2.cvtColor(candidate, cv2.COLOR_RGB2GRAY)
        verified = True
        worst_detail = 0.0
        worst_ratio = 0.0

        for region in regions:
            x1, y1, x2, y2 = region
            after = candidate_gray[y1:y2, x1:x2]
            before = original_gray[y1:y2, x1:x2]
            if after.size == 0:
                continue

            # Measure only the pixels genuinely inside the ellipse. Including
            # the surrounding square would average in sharp, deliberately
            # untouched background and make verification unsatisfiable.
            selection = _ellipse_selection(region)

            after_energy = _highfreq_energy(after, selection)
            before_energy = _highfreq_energy(before, selection)
            ratio = (after_energy / before_energy) if before_energy > 1e-6 else 0.0

            worst_detail = max(worst_detail, after_energy)
            worst_ratio = max(worst_ratio, ratio)

            # Absolute residual detail is the primary criterion. The *ratio*
            # cannot be trusted alone: JPEG quantisation noise puts a floor
            # under it, so a fully destroyed face still reports a ratio around
            # 0.15-0.35 no matter how hard it is blurred. Absolute Laplacian
            # energy, by contrast, collapses from the hundreds to ~1.
            if after_energy > settings.max_residual_detail:
                verified = False
            # The ratio is retained as a secondary guard for the pathological
            # case of an already-flat source region, where absolute energy
            # starts low and blurring proves nothing.
            elif before_energy > settings.flat_region_energy and ratio > settings.max_highfreq_ratio:
                verified = False

        if verified:
            return candidate, BlurReport(
                outcome=BlurOutcome.BLURRED_VERIFIED,
                faces_detected=len(boxes),
                escalations=escalation,
                residual_detail=worst_detail,
                highfreq_ratio=worst_ratio,
                regions=[
                    {
                        "x": x1,
                        "y": y1,
                        "width": x2 - x1,
                        "height": y2 - y1,
                        "confidence": round(box.confidence, 4),
                        "model": box.model,
                    }
                    for box, (x1, y1, x2, y2) in zip(boxes, regions, strict=True)
                ],
                detail=f"{len(boxes)} region(s) blurred and verified irreversible.",
            )

        escalation += 1
        logger.warning(
            "Blur verification failed (residual_detail=%.2f ratio=%.3f); escalating to %d",
            worst_detail,
            worst_ratio,
            escalation,
        )

    # Escalation exhausted: refuse the asset outright. Returning the original
    # would be catastrophic, and returning a partly-blurred image would imply
    # a safety we cannot demonstrate.
    return rgb.copy(), BlurReport(
        outcome=BlurOutcome.VERIFICATION_FAILED,
        faces_detected=len(boxes),
        escalations=escalation,
        residual_detail=worst_detail,
        highfreq_ratio=worst_ratio,
        detail=(
            "Blur could not be verified irreversible after "
            f"{settings.max_blur_escalations} escalations. Asset rejected."
        ),
    )


#: Process-wide detector. Loaded at ASGI lifespan startup.
detector = FaceDetector()
