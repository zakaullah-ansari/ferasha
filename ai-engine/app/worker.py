"""Redis-backed media processing worker.

Crash semantics are the whole point of this module. If the worker dies at any
moment - OOM, SIGKILL, node eviction - the asset must remain PENDING in
Django. There is no code path that marks an asset APPROVED except a
successfully verified blur followed by a signed callback.

Queue choice: a Redis *reliable queue* (BRPOPLPUSH into a processing list),
not a plain list pop. A plain `BRPOP` loses the job entirely if the worker
dies between popping and finishing, which would strand the asset in
PROCESSING forever with nothing to retry it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.security import sign_callback
from app.services.face_blur import BlurOutcome, blur_faces, detector
from app.services.image_ops import ImageRejected, decode_image, encode_jpeg

logger = logging.getLogger(__name__)


@dataclass
class Job:
    asset_id: str
    checksum: str
    download_url: str
    attempt: int = 0

    @classmethod
    def parse(cls, raw: str) -> Job:
        payload = json.loads(raw)
        return cls(
            asset_id=str(payload["asset_id"]),
            checksum=str(payload["checksum"]),
            download_url=str(payload["download_url"]),
            attempt=int(payload.get("attempt", 0)),
        )

    def dump(self) -> str:
        return json.dumps(
            {
                "asset_id": self.asset_id,
                "checksum": self.checksum,
                "download_url": self.download_url,
                "attempt": self.attempt,
            },
            sort_keys=True,
        )


class MediaWorker:
    """Consumes blur jobs and reports results back to Django."""

    def __init__(self, redis: aioredis.Redis, client: httpx.AsyncClient) -> None:
        self.redis = redis
        self.client = client
        self.settings = get_settings()
        self._running = False

    # -- queue plumbing ----------------------------------------------------

    @property
    def _processing_key(self) -> str:
        return f"{self.settings.media_queue}:processing"

    async def enqueue(self, job: Job) -> None:
        await self.redis.lpush(self.settings.media_queue, job.dump())

    async def _claim(self, timeout: int = 5) -> str | None:
        """Atomically move a job to the processing list.

        If we crash after this, the job is still in the processing list and a
        reaper can return it to the queue - it is never silently lost.
        """
        return await self.redis.brpoplpush(
            self.settings.media_queue, self._processing_key, timeout=timeout
        )

    async def _release(self, raw: str) -> None:
        await self.redis.lrem(self._processing_key, 1, raw)

    async def _dead_letter(self, raw: str, reason: str) -> None:
        """Isolate a poison message. Never silently dropped."""
        await self.redis.lpush(
            self.settings.media_dlq,
            json.dumps({"job": raw, "reason": reason, "failed_at": int(time.time())}),
        )
        logger.error("Job dead-lettered: %s", reason)

    # -- processing --------------------------------------------------------

    async def _download(self, url: str) -> bytes:
        response = await self.client.get(url, timeout=30.0)
        response.raise_for_status()
        return response.content

    async def _callback(self, payload: dict[str, Any]) -> None:
        """Report the outcome to Django over a signed request."""
        url = f"{self.settings.backend_base_url.rstrip('/')}/api/v1/media/callback/"
        headers = sign_callback(payload)
        headers["Content-Type"] = "application/json"

        # The body must be byte-identical to what was signed, so the canonical
        # encoding is sent directly rather than re-serialised by httpx.
        from app.core.security import canonical_payload

        response = await self.client.post(
            url, content=canonical_payload(payload), headers=headers, timeout=30.0
        )
        response.raise_for_status()

    async def process(self, job: Job) -> str:
        """Process one job. Returns the outcome string.

        Any exception propagates to the caller, which decides retry vs DLQ.
        Crucially, an exception means *no callback is sent*, so the asset
        stays PENDING.
        """
        data = await self._download(job.download_url)

        try:
            image = decode_image(data)
        except ImageRejected as exc:
            # Terminal: retrying a malformed file forever just fills the queue.
            await self._callback(
                {
                    "asset_id": job.asset_id,
                    "checksum": job.checksum,
                    "outcome": "rejected",
                    "faces_detected": 0,
                    "detail": str(exc),
                }
            )
            return "rejected"

        boxes = detector.detect(image.pixels)
        processed, report = blur_faces(image.pixels, boxes)

        if not report.is_publishable:
            await self._callback(
                {
                    "asset_id": job.asset_id,
                    "checksum": job.checksum,
                    "outcome": (
                        "needs_review"
                        if report.outcome == BlurOutcome.NO_FACES_DETECTED
                        else "rejected"
                    ),
                    "faces_detected": report.faces_detected,
                    "detail": report.detail,
                }
            )
            return str(report.outcome)

        derivative = encode_jpeg(processed)
        upload_url = (
            f"{self.settings.backend_base_url.rstrip('/')}"
            f"/api/v1/media/{job.asset_id}/derivative/"
        )
        headers = sign_callback({"asset_id": job.asset_id, "checksum": job.checksum})
        upload = await self.client.put(
            upload_url,
            content=derivative,
            headers={
                **headers,
                "Content-Type": "image/jpeg",
                "X-Ferasha-Checksum": job.checksum,
            },
            timeout=60.0,
        )
        upload.raise_for_status()

        await self._callback(
            {
                "asset_id": job.asset_id,
                "checksum": job.checksum,
                "outcome": "approved",
                "faces_detected": report.faces_detected,
                "blur_verified": True,
                "escalations": report.escalations,
                "detail": report.detail,
            }
        )
        return "approved"

    async def handle(self, raw: str) -> None:
        """Claim-process-release with retry and dead-lettering."""
        try:
            job = Job.parse(raw)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            await self._dead_letter(raw, f"unparseable job: {exc}")
            await self._release(raw)
            return

        try:
            outcome = await self.process(job)
            logger.info("Asset %s -> %s", job.asset_id, outcome)
            await self._release(raw)
        except Exception as exc:  # noqa: BLE001 - must not kill the worker loop
            await self._release(raw)
            job.attempt += 1
            if job.attempt >= self.settings.max_attempts:
                await self._dead_letter(
                    job.dump(), f"exhausted {self.settings.max_attempts} attempts: {exc}"
                )
                return

            delay = self.settings.retry_base_seconds * (2 ** (job.attempt - 1))
            logger.warning(
                "Asset %s attempt %d failed (%s); retrying in %.1fs",
                job.asset_id,
                job.attempt,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
            await self.enqueue(job)

    async def run(self) -> None:
        self._running = True
        detector.load()
        logger.info("Worker consuming from %s", self.settings.media_queue)
        while self._running:
            raw = await self._claim()
            if raw is None:
                continue
            await self.handle(raw)

    def stop(self) -> None:
        self._running = False


async def main() -> None:  # pragma: no cover - entrypoint
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    async with httpx.AsyncClient() as client:
        await MediaWorker(redis, client).run()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
