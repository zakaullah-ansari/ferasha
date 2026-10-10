"""Worker reliability semantics.

The claim this suite defends: no failure mode results in an unblurred face
being published, and no job is ever silently lost. Everything here simulates
a way the worker can die or be lied to.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.worker import Job, MediaWorker
from tests.conftest import encode, featureless_noise

pytestmark = pytest.mark.asyncio


class FakeRedis:
    """Minimal in-memory stand-in for the list operations the worker uses."""

    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}

    async def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    async def brpoplpush(self, source: str, destination: str, timeout: int = 0):
        items = self.lists.get(source, [])
        if not items:
            return None
        value = items.pop()
        self.lists.setdefault(destination, []).insert(0, value)
        return value

    async def lrem(self, key: str, count: int, value: str) -> None:
        items = self.lists.get(key, [])
        if value in items:
            items.remove(value)


def make_worker(handler) -> tuple[MediaWorker, FakeRedis, list]:
    """Wire a worker to a scripted HTTP transport, recording every request."""
    recorded: list[httpx.Request] = []

    def track(request: httpx.Request) -> httpx.Response:
        recorded.append(request)
        return handler(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(track))
    redis = FakeRedis()
    return MediaWorker(redis, client), redis, recorded


def job(**overrides) -> Job:
    base = {
        "asset_id": "11111111-1111-1111-1111-111111111111",
        "checksum": "c" * 64,
        "download_url": "https://storage.test/original.jpg",
    }
    base.update(overrides)
    return Job(**base)


@pytest.fixture
def portrait_bytes(photo_paths):
    if not photo_paths:
        pytest.skip("photograph fixtures unavailable")
    return photo_paths[0].read_bytes()


class TestHappyPath:
    async def test_verified_blur_uploads_then_approves(
        self, loaded_detector, portrait_bytes
    ):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, content=portrait_bytes)
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        outcome = await worker.process(job())
        assert outcome == "approved"

        methods = [r.method for r in recorded]
        assert methods == ["GET", "PUT", "POST"], (
            "the derivative must be uploaded before approval is reported"
        )

        callback = json.loads(recorded[-1].content)
        assert callback["outcome"] == "approved"
        assert callback["blur_verified"] is True
        assert callback["faces_detected"] >= 1

    async def test_callback_is_signed(self, loaded_detector, portrait_bytes):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, content=portrait_bytes)
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        await worker.process(job())

        callback = recorded[-1]
        for header in (
            "X-Ferasha-Timestamp",
            "X-Ferasha-Nonce",
            "X-Ferasha-Signature",
        ):
            assert header in callback.headers, f"{header} missing - Django will reject"

    async def test_signed_body_matches_bytes_sent(
        self, loaded_detector, portrait_bytes
    ):
        """The signature covers the exact bytes on the wire.

        Re-serialising the payload with different key order would produce a
        valid-looking request that Django rejects.
        """
        from app.core.security import canonical_payload

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, content=portrait_bytes)
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        await worker.process(job())

        body = recorded[-1].content
        assert body == canonical_payload(json.loads(body))


class TestFailClosedSemantics:
    async def test_no_faces_reports_needs_review_and_uploads_nothing(
        self, loaded_detector
    ):
        """An image with no detectable face must not be published.

        This is the fail-closed path that matters most: detection returning
        nothing means "a human decides", never "publish it".
        """
        plain = encode(featureless_noise(), quality=95)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, content=plain)
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        await worker.process(job())

        assert "PUT" not in [r.method for r in recorded], (
            "an unverified image was uploaded to public storage"
        )
        callback = json.loads(recorded[-1].content)
        assert callback["outcome"] == "needs_review"
        assert "blur_verified" not in callback or callback.get("blur_verified") is not True

    async def test_malformed_image_is_rejected_not_retried_forever(
        self, loaded_detector
    ):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, content=b"this is not an image at all")
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        outcome = await worker.process(job())

        assert outcome == "rejected"
        assert "PUT" not in [r.method for r in recorded]

    async def test_download_failure_sends_no_callback(self, loaded_detector):
        """Storage being down must leave the asset PENDING, never settled."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(503, text="storage unavailable")
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await worker.process(job())

        assert [r.method for r in recorded] == ["GET"], (
            "a callback was sent despite the job failing - asset would be settled"
        )

    async def test_failed_derivative_upload_never_reports_approved(
        self, loaded_detector, portrait_bytes
    ):
        """If the blurred image did not reach storage, nothing is approved.

        Otherwise Django would be told to publish an asset whose derivative
        does not exist, and the public URL would resolve to nothing - or, far
        worse, to a stale object.
        """

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, content=portrait_bytes)
            if request.method == "PUT":
                return httpx.Response(500, text="storage write failed")
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        with pytest.raises(httpx.HTTPStatusError):
            await worker.process(job())

        approvals = [
            r for r in recorded
            if r.method == "POST" and b'"outcome":"approved"' in r.content
        ]
        assert not approvals, "reported approval despite the upload failing"

    async def test_crash_before_completion_leaves_job_recoverable(
        self, loaded_detector
    ):
        """Simulates the worker dying mid-job.

        The job must still be in the processing list, where a reaper can
        return it to the queue. This is why BRPOPLPUSH is used instead of a
        plain pop.
        """
        worker, redis, _ = make_worker(lambda r: httpx.Response(200))
        await worker.enqueue(job())

        claimed = await worker._claim()
        assert claimed is not None

        # Worker dies here - no release, no callback.
        assert redis.lists[worker._processing_key] == [claimed], (
            "job vanished on crash; it would never be retried"
        )
        assert not redis.lists.get(worker.settings.media_queue)


class TestRetryAndDeadLettering:
    async def test_transient_failure_is_retried_with_backoff(
        self, loaded_detector, monkeypatch
    ):
        import app.worker as worker_module

        slept: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            slept.append(seconds)

        monkeypatch.setattr(worker_module.asyncio, "sleep", fake_sleep)

        worker, redis, _ = make_worker(
            lambda r: httpx.Response(500, text="backend down")
        )
        await worker.handle(job().dump())

        assert slept, "no backoff was applied"
        queued = redis.lists.get(worker.settings.media_queue, [])
        assert len(queued) == 1
        assert json.loads(queued[0])["attempt"] == 1

    async def test_exhausted_attempts_go_to_the_dead_letter_queue(
        self, loaded_detector, monkeypatch
    ):
        """A job is never dropped silently - it lands in the DLQ."""
        import app.worker as worker_module

        async def fake_sleep(seconds: float) -> None:
            return None

        monkeypatch.setattr(worker_module.asyncio, "sleep", fake_sleep)

        worker, redis, _ = make_worker(lambda r: httpx.Response(500))
        exhausted = job(attempt=worker.settings.max_attempts - 1)
        await worker.handle(exhausted.dump())

        dlq = redis.lists.get(worker.settings.media_dlq, [])
        assert len(dlq) == 1, "job was lost instead of dead-lettered"
        assert "exhausted" in json.loads(dlq[0])["reason"]
        assert not redis.lists.get(worker.settings.media_queue)

    async def test_unparseable_job_is_dead_lettered(self, loaded_detector):
        worker, redis, _ = make_worker(lambda r: httpx.Response(200))
        await worker.handle("{not valid json")

        dlq = redis.lists.get(worker.settings.media_dlq, [])
        assert len(dlq) == 1
        assert "unparseable" in json.loads(dlq[0])["reason"]

    async def test_job_round_trips_through_serialisation(self):
        original = job(attempt=3)
        assert Job.parse(original.dump()) == original


class TestIdempotency:
    async def test_checksum_travels_with_every_report(
        self, loaded_detector, portrait_bytes
    ):
        """Django uses the checksum to detect a swapped original."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET":
                return httpx.Response(200, content=portrait_bytes)
            return httpx.Response(200, json={"detail": "ok"})

        worker, _, recorded = make_worker(handler)
        await worker.process(job())

        upload = next(r for r in recorded if r.method == "PUT")
        assert upload.headers["X-Ferasha-Checksum"] == "c" * 64

        callback = json.loads(recorded[-1].content)
        assert callback["checksum"] == "c" * 64
