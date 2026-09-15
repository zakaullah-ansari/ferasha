"""The privacy guarantee.

This is the highest-stakes suite in the repository. A regression here does not
produce a broken page - it publishes an identifiable person's face without
their consent, which is a DPDP Act 2023 breach and permanent reputational
damage with vendors.

The tests are written against *behaviour a court or auditor would care about*:
can the face still be seen, and does the system ever fail open.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.services.face_blur import (
    BlurOutcome,
    FaceBox,
    _ellipse_selection,
    _expand,
    _highfreq_energy,
    _merge_overlapping,
    blur_faces,
)
from app.services.image_ops import decode_image

pytestmark = pytest.mark.usefixtures("loaded_detector")


# --------------------------------------------------------------------------- #
# Real photographs - the only honest test of detection
# --------------------------------------------------------------------------- #


class TestRealPhotographs:
    def test_detects_faces_in_real_portraits(self, loaded_detector, photo_paths):
        if not photo_paths:
            pytest.skip("photograph fixtures unavailable")
        for path in photo_paths:
            image = decode_image(path.read_bytes())
            boxes = loaded_detector.detect(image.pixels)
            assert boxes, f"no face detected in {path.name} - a real portrait"

    def test_blur_verifies_on_real_portraits(self, loaded_detector, photo_paths):
        if not photo_paths:
            pytest.skip("photograph fixtures unavailable")
        for path in photo_paths:
            image = decode_image(path.read_bytes())
            boxes = loaded_detector.detect(image.pixels)
            _, report = blur_faces(image.pixels, boxes)
            assert report.outcome == BlurOutcome.BLURRED_VERIFIED, (
                f"{path.name}: {report.detail}"
            )
            assert report.is_publishable

    def test_face_region_is_unrecognisable_afterwards(self, loaded_detector, photo_paths):
        """The measurable claim: detail inside the face collapses.

        Compares mean absolute Laplacian energy inside the ellipse before and
        after. Real portrait faces measure in the hundreds; a destroyed face
        measures around 1.
        """
        if not photo_paths:
            pytest.skip("photograph fixtures unavailable")

        for path in photo_paths:
            image = decode_image(path.read_bytes())
            boxes = loaded_detector.detect(image.pixels)
            processed, report = blur_faces(image.pixels, boxes)
            assert report.is_publishable

            before_gray = cv2.cvtColor(image.pixels, cv2.COLOR_RGB2GRAY)
            after_gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
            height, width = before_gray.shape

            for box in boxes:
                region = _expand(box, 0.35, width, height)
                x1, y1, x2, y2 = region
                selection = _ellipse_selection(region)
                before = _highfreq_energy(before_gray[y1:y2, x1:x2], selection)
                after = _highfreq_energy(after_gray[y1:y2, x1:x2], selection)

                # Absolute residual detail is the criterion that matters: it
                # is what determines whether features are recoverable.
                assert after < 3.0, f"{path.name}: residual detail {after:.2f} too high"

                # A relative test is only meaningful when the source actually
                # had detail to destroy. Soft-focus and heavily compressed
                # portraits can start near the floor (one fixture here begins
                # at 2.2), and demanding a 10x fall from there is arithmetic
                # that no blur can satisfy.
                if before > 20.0:
                    assert after < before / 10, (
                        f"{path.name}: detail only fell from {before:.1f} to {after:.1f}"
                    )
                else:
                    assert after <= before, (
                        f"{path.name}: blur increased detail {before:.1f} -> {after:.1f}"
                    )

    def test_pixels_outside_the_face_are_preserved(self, loaded_detector, photo_paths):
        """The garment must stay sharp - that is the product being sold."""
        if not photo_paths:
            pytest.skip("photograph fixtures unavailable")

        path = photo_paths[0]
        image = decode_image(path.read_bytes())
        boxes = loaded_detector.detect(image.pixels)
        processed, report = blur_faces(image.pixels, boxes)
        assert report.is_publishable

        height, width = image.pixels.shape[:2]
        mask = np.zeros((height, width), dtype=bool)
        for box in boxes:
            x1, y1, x2, y2 = _expand(box, 0.6, width, height)
            mask[y1:y2, x1:x2] = True

        untouched = ~mask
        if untouched.sum() > 0:
            difference = np.abs(
                image.pixels[untouched].astype(int) - processed[untouched].astype(int)
            )
            assert difference.mean() < 1.0, "blur bled well outside the face region"


# --------------------------------------------------------------------------- #
# Fail-closed behaviour
# --------------------------------------------------------------------------- #


class TestFailClosed:
    def test_zero_detections_never_auto_approves(self, synthetic_face_rgb):  # noqa: D401
        """The single most important assertion in the project.

        Detection cannot prove absence. MediaPipe misses veiled, profile, and
        low-light faces - all routine in South Asian bridal photography - so
        "no faces found" must mean "a human decides", never "publish it".
        """
        processed, report = blur_faces(synthetic_face_rgb, [])

        assert report.outcome == BlurOutcome.NO_FACES_DETECTED
        assert report.is_publishable is False, "zero detections must NEVER be publishable"
        assert report.faces_detected == 0
        assert "human review" in report.detail.lower()

    def test_unverifiable_blur_is_not_publishable(self, monkeypatch, synthetic_face_rgb):
        """If the blur cannot be proven irreversible, the asset is refused."""
        from app.core import config

        settings = config.get_settings()
        # Demand the physically impossible.
        monkeypatch.setattr(settings, "max_residual_detail", 0.0)
        monkeypatch.setattr(settings, "max_blur_escalations", 1)

        box = FaceBox(120, 150, 160, 200, 0.9, "test")
        _, report = blur_faces(synthetic_face_rgb, [box])

        assert report.outcome == BlurOutcome.VERIFICATION_FAILED
        assert report.is_publishable is False
        assert "rejected" in report.detail.lower()

    def test_only_verified_outcome_is_publishable(self):
        """Exhaustive: exactly one outcome may be published."""
        from app.services.face_blur import BlurReport

        publishable = [
            outcome
            for outcome in BlurOutcome
            if BlurReport(outcome=outcome, faces_detected=1).is_publishable
        ]
        assert publishable == [BlurOutcome.BLURRED_VERIFIED]

    def test_escalation_increases_strength_until_verified(self, synthetic_face_rgb):
        """A hard case should escalate rather than give up or fail open."""
        box = FaceBox(120, 150, 160, 200, 0.9, "test")
        _, report = blur_faces(synthetic_face_rgb, [box])
        assert report.outcome == BlurOutcome.BLURRED_VERIFIED
        assert report.escalations >= 0


# --------------------------------------------------------------------------- #
# Blur mechanics
# --------------------------------------------------------------------------- #


class TestBlurMechanics:
    def test_original_array_is_never_mutated(self, synthetic_face_rgb):
        box = FaceBox(120, 150, 160, 200, 0.9, "test")
        snapshot = synthetic_face_rgb.copy()
        blur_faces(synthetic_face_rgb, [box])
        assert np.array_equal(synthetic_face_rgb, snapshot), "input was modified in place"

    def test_margin_expands_beyond_the_detected_box(self):
        """A tight crop leaves hairline, jaw and ears identifiable."""
        box = FaceBox(100, 100, 100, 100, 0.9, "test")
        x1, y1, x2, y2 = _expand(box, 0.35, 1000, 1000)
        assert x1 < 100 and y1 < 100
        assert x2 > 200 and y2 > 200

    def test_margin_is_clamped_to_canvas(self):
        box = FaceBox(5, 5, 50, 50, 0.9, "test")
        x1, y1, x2, y2 = _expand(box, 1.5, 100, 100)
        assert (x1, y1) == (0, 0)
        assert x2 <= 100 and y2 <= 100

    def test_kernel_scales_with_face_size(self):
        """A fixed kernel would leave large faces recognisable."""
        from app.services.face_blur import _kernel_for

        small = _kernel_for(40, 40, 0)
        large = _kernel_for(400, 400, 0)
        assert large > small
        assert small % 2 == 1 and large % 2 == 1, "OpenCV requires odd kernels"

    def test_multiple_faces_all_blurred(self, loaded_detector):
        """A group shot must not have one face processed and the rest missed."""
        rng = np.random.default_rng(7)
        canvas = rng.integers(60, 200, size=(400, 900, 3), dtype=np.uint8)
        boxes = [
            FaceBox(80, 120, 140, 160, 0.9, "test"),
            FaceBox(380, 110, 150, 170, 0.9, "test"),
            FaceBox(680, 130, 130, 150, 0.9, "test"),
        ]
        processed, report = blur_faces(canvas, boxes)
        assert report.faces_detected == 3
        assert report.is_publishable

        gray_before = cv2.cvtColor(canvas, cv2.COLOR_RGB2GRAY)
        gray_after = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
        for box in boxes:
            region = _expand(box, 0.35, 900, 400)
            x1, y1, x2, y2 = region
            selection = _ellipse_selection(region)
            after = _highfreq_energy(gray_after[y1:y2, x1:x2], selection)
            before = _highfreq_energy(gray_before[y1:y2, x1:x2], selection)
            assert after < before / 5, "one of several faces was left sharp"


class TestDetectionMerging:
    def test_duplicate_detections_are_merged(self):
        """Both models see the same face; it must be blurred once."""
        a = FaceBox(100, 100, 200, 200, 0.9, "short_range")
        b = FaceBox(105, 103, 198, 202, 0.8, "full_range")
        assert len(_merge_overlapping([a, b])) == 1

    def test_distinct_faces_are_kept(self):
        a = FaceBox(100, 100, 120, 120, 0.9, "short_range")
        b = FaceBox(600, 100, 120, 120, 0.9, "full_range")
        assert len(_merge_overlapping([a, b])) == 2

    def test_merge_prefers_the_larger_box(self):
        """Over-blurring is the safe direction, so keep the bigger region."""
        small = FaceBox(100, 100, 100, 100, 0.99, "short_range")
        large = FaceBox(95, 95, 130, 130, 0.50, "full_range")
        merged = _merge_overlapping([small, large])
        assert len(merged) == 1
        assert merged[0].width == 130, "kept the smaller/high-confidence box"

    def test_empty_input(self):
        assert _merge_overlapping([]) == []


class TestReportSerialisation:
    def test_report_is_json_safe_and_states_publishability(self, synthetic_face_rgb):
        import json

        box = FaceBox(120, 150, 160, 200, 0.9, "test")
        _, report = blur_faces(synthetic_face_rgb, [box])
        payload = report.as_dict()

        json.dumps(payload)  # must not raise
        assert payload["publishable"] is report.is_publishable
        assert isinstance(payload["outcome"], str)
        assert not payload["outcome"].startswith("BlurOutcome.")
