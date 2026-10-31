# Phase 3 — AI Engine: Face-Blur Privacy Pipeline

| | |
|---|---|
| **Status** | ⬜ Not started |
| **Depends on** | Phase 2 (API contract) |
| **Blocks** | Phase 4 (image display), Phase 6 |
| **Effort** | 24–30 hrs |
| **Risk** | 🔴 **Highest compliance risk in the project** |

---

## 1. Objective

Every vendor-supplied image passes through automated face detection and irreversible Gaussian blurring before it can ever be served publicly. Model privacy is a hard requirement, not a feature.

**The governing principle is fail-closed.** If anything goes wrong — worker crash, model miss, timeout, malformed file — the image stays private. There is no failure mode that results in an unblurred face being served.

---

## 2. Why this is the riskiest phase

Vendor imagery comes from manufacturers and online sources. It contains identifiable people who have not consented to appear on Ferasha. Under the **DPDP Act 2023**, a facial image is personal data; publishing it without a lawful basis is a breach with real penalties, and reputationally it destroys vendor trust permanently.

A single leaked unblurred face is worse than a week of downtime.

---

## 3. Architecture

```
Vendor upload
   │
   ▼
Django: MediaAsset(status=PENDING, original → PRIVATE storage)   ← never publicly routable
   │
   ├─ enqueue job {asset_id, checksum} → Redis
   │
   ▼
FastAPI worker
   ├─ fetch original from private storage
   ├─ MediaPipe face detection (short-range + full-range)
   ├─ elliptical Gaussian blur, kernel scaled to face size
   ├─ irreversibility verification  ← the actual privacy guarantee
   ├─ write derivative → PUBLIC storage
   └─ HMAC-signed callback → Django
   │
   ▼
Django: status = APPROVED (faces=0 → NEEDS_REVIEW instead)
   │
   ▼
Only APPROVED derivatives are ever served
```

---

## 4. Detection

MediaPipe Face Detection, **both models**:
- **Short-range** — close-up portraits, the common case for garment photography
- **Full-range** — full-body editorial shots, the common case for lehenga catalogues

Union of both detection sets. Confidence threshold tuned deliberately **low** — a false positive blurs a handbag clasp (harmless); a false negative publishes someone's face (a breach).

### 4.1 Known limits — and why humans stay in the loop

MediaPipe will miss faces in profile, under heavy dupatta or veil coverage, in low light, at extreme angles, or when very small in frame. South Asian bridal photography contains **all** of these routinely.

Therefore: **zero detections never means auto-approve.** An image with no detected face goes to `NEEDS_REVIEW` for a human. This inverts the usual convenience/safety trade-off on purpose.

---

## 5. Blurring

Rectangular blur boxes look cheap on editorial imagery and undermine a luxury brand. Implementation uses:

- **Elliptical mask** following the face bounding box, feathered at the edge
- **Bounding box expanded** by a configurable margin — a tight crop leaves hairline, jaw and ear identifiable
- **Kernel size scaled to face size** — a fixed kernel leaves small faces recoverable
- Operating on a copy; the original is never mutated in place

### 5.1 Irreversibility verification

A weak blur is reversible by deconvolution. Applying blur is not the guarantee — *verifying* it is:

- Assert pixel variance inside the mask collapses below a threshold
- Assert high-frequency energy is destroyed, not merely attenuated
- If verification fails, escalate blur strength and re-verify; if it still fails, **reject the asset**

Tested with synthetic faces, asserting variance collapse.

---

## 6. Worker semantics

| Property | Implementation |
|---|---|
| Idempotent | Keyed by asset ID + content checksum; reprocessing is safe |
| Retries | Exponential backoff, capped |
| Dead-letter queue | Poison messages isolated, alerted, never silently dropped |
| Crash safety | Asset remains `PENDING` — **never** `APPROVED` |
| Model loading | Loaded **once** at ASGI lifespan startup, not per request |
| Resource limits | Max dimensions, max file size, decode timeout — guards against decompression bombs |
| Format validation | Magic-byte sniffing, not file extension |
| EXIF | **Stripped** — GPS coordinates in vendor photos are a separate privacy leak |

---

## 7. Service boundary

FastAPI verifies Django-signed HS256 JWTs using the shared `JWT_SIGNING_KEY` (Phase 0, D1). It issues no credentials.

Internal callbacks (worker → Django) are authenticated with an **HMAC signature** over the payload using `AI_ENGINE_SHARED_SECRET`, with a timestamp and nonce to prevent replay. A callback that merely knows an asset ID must not be able to mark it approved.

---

## 8. Deliverables

| File | Purpose |
|---|---|
| `ai-engine/app/main.py` | FastAPI app, CORS, lifespan model loading, `/health`, `/ready` |
| `ai-engine/app/core/security.py` | JWT verification, HMAC callback signing |
| `ai-engine/app/core/config.py` | Pydantic settings |
| `ai-engine/app/services/face_blur.py` | Detection, elliptical blur, irreversibility check |
| `ai-engine/app/services/image_ops.py` | Decode, EXIF strip, resize, format guards |
| `ai-engine/app/worker.py` | Redis consumer, retries, DLQ |
| `ai-engine/app/api/routes_media.py` | Sync endpoint for previews |
| `backend-core/apps/media_assets/models.py` | MediaAsset, moderation status, storage split |
| `ai-engine/Dockerfile` | Pinned OpenCV/MediaPipe, non-root |
| `ai-engine/tests/` | Synthetic-face fixtures, variance-collapse assertions |

---

## 9. Exit criteria

Assessed 2026-10-26 by executing the suites, then reassessed after clearing
V1–V3 in [Verification debt](../ROADMAP.md#verification-debt). A test that
exists but does not run proves nothing, so each criterion is marked on whether
a *passing* test demonstrates it. Six of nine now do; the three that do not are
blocked on V4, the missing photograph fixtures.

| Criterion | Status | Evidence |
|---|---|---|
| Upload → blurred derivative end-to-end in `docker compose` | ⬜ | Still no live end-to-end run. The worker's happy path, `test_verified_blur_uploads_then_approves`, skips on V4, so even the in-process equivalent has never executed. |
| Killing the worker mid-job leaves the asset `PENDING`, never `APPROVED` | ✅ | `test_crash_before_completion_leaves_job_recoverable` passes, and `test_media_privacy.py`'s database constraints independently reject `APPROVED` without a verified blur. The sibling case `test_failed_derivative_upload_never_reports_approved` skips on V4. |
| Original is not reachable via any public URL (**explicitly tested**) | ✅ | `test_original_not_public.py` — 5 passing tests, including traversal and a URLconf sweep. |
| Zero-detection images route to `NEEDS_REVIEW`, not auto-approve | ✅ | Proven at three layers: `test_zero_detections_never_auto_approves` (engine), `test_no_faces_reports_needs_review_and_uploads_nothing` (worker), and `test_zero_faces_cannot_be_approved` (callback, unblocked by the V1 fix). |
| Variance collapse verified inside mask regions | 🟡 | Verified on synthetic faces: `test_unverifiable_blur_is_not_publishable` and `test_escalation_increases_strength_until_verified` pass. **Not verified on real photographs** — `test_face_region_is_unrecognisable_afterwards` skips on V4. |
| EXIF/GPS stripped from every derivative | ✅ | `test_fixture_actually_has_gps` then `test_gps_is_stripped_from_derivative` pass, as does `test_orientation_is_applied_then_dropped`. The API-level `test_response_carries_no_exif` skips on V4, but the derivative path itself is proven. |
| Malformed and oversized uploads rejected without crashing the worker | ✅ | Seven decode guards pass — truncated, oversized, unknown-magic, SVG, and a decompression bomb refused before decode — plus `test_malformed_image_is_rejected_not_retried_forever`. |
| Unsigned or replayed callbacks rejected | ✅ | Unsigned, wrong-secret, tampered, stale and future-dated are refused, and `test_replayed_callback_is_rejected` now passes, so nonce replay protection is demonstrated rather than assumed. |
| Model loads once, not per request (measured) | 🟡 | Structurally sound: a module-level singleton with an idempotent `load()` behind a `_loaded` flag, called once in the lifespan and exposed on `/ready`, which `test_ready_reports_model_state` checks. Nothing *measures* a load count, so the criterion as written is still unmet. |

**Verdict:** six of nine criteria are met under execution, up from one before
V1–V3 were cleared. The privacy model is sound and every Django-side guarantee
holds. Two gaps remain and both are narrow: blur efficacy is proven on
synthetic faces but not on real photographs, and the happy path has never run
— both blocked on V4 — plus a load-count measurement that was never written.
This phase should not be recorded complete until V4 is closed.

---

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Unblurred face served | 🔴 Severe — DPDP breach, vendor trust | Fail-closed at every step; originals never in public path; approval only via signed callback |
| MediaPipe misses a veiled/profile face | 🔴 High | Dual models, low threshold, mandatory human review on zero-detection |
| Blur reversible by deconvolution | 🟠 Medium-high | Explicit irreversibility verification, not just blur application |
| Worker backlog delays merchandising | 🟡 Medium | Horizontal scaling; queue-depth alerting |
| GPS in vendor EXIF | 🟠 Medium | Unconditional EXIF strip |
