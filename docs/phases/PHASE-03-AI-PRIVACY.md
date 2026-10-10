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

- [ ] Upload → blurred derivative end-to-end in `docker compose`
- [ ] Killing the worker mid-job leaves the asset `PENDING`, never `APPROVED`
- [ ] Original is not reachable via any public URL (**explicitly tested**)
- [ ] Zero-detection images route to `NEEDS_REVIEW`, not auto-approve
- [ ] Variance collapse verified inside mask regions
- [ ] EXIF/GPS stripped from every derivative
- [ ] Malformed and oversized uploads rejected without crashing the worker
- [ ] Unsigned or replayed callbacks rejected
- [ ] Model loads once, not per request (measured)

---

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Unblurred face served | 🔴 Severe — DPDP breach, vendor trust | Fail-closed at every step; originals never in public path; approval only via signed callback |
| MediaPipe misses a veiled/profile face | 🔴 High | Dual models, low threshold, mandatory human review on zero-detection |
| Blur reversible by deconvolution | 🟠 Medium-high | Explicit irreversibility verification, not just blur application |
| Worker backlog delays merchandising | 🟡 Medium | Horizontal scaling; queue-depth alerting |
| GPS in vendor EXIF | 🟠 Medium | Unconditional EXIF strip |
