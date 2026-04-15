"""
Tests for A2A SSE Streaming
"""
import asyncio
import pytest

from a2a.models import SSEEvent, SSEEventType
from a2a.streaming import StreamManager, sse_event_generator


@pytest.fixture
def sm():
    return StreamManager()


class TestStreamManager:

    def test_subscribe(self, sm):
        queue = sm.subscribe("task-1")
        assert queue is not None
        assert sm.has_subscribers("task-1")

    def test_unsubscribe(self, sm):
        queue = sm.subscribe("task-1")
        sm.unsubscribe("task-1", queue)
        assert not sm.has_subscribers("task-1")

    def test_unsubscribe_nonexistent(self, sm):
        queue = asyncio.Queue()
        sm.unsubscribe("nonexistent", queue)  # Should not raise

    def test_multiple_subscribers(self, sm):
        q1 = sm.subscribe("task-1")
        q2 = sm.subscribe("task-1")
        assert sm.has_subscribers("task-1")

    def test_emit_to_subscribers(self, sm):
        queue = sm.subscribe("task-1")
        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="task-1",
            data={"status": "working"},
        )
        sm._emit_sync(event)
        assert not queue.empty()
        received = queue.get_nowait()
        assert received.event_type == SSEEventType.STATUS
        assert received.data["status"] == "working"

    def test_emit_only_to_correct_task(self, sm):
        q1 = sm.subscribe("task-1")
        q2 = sm.subscribe("task-2")
        event = SSEEvent(event_type=SSEEventType.STATUS, task_id="task-1", data={})
        sm._emit_sync(event)
        assert not q1.empty()
        assert q2.empty()

    def test_emit_to_multiple_subscribers(self, sm):
        q1 = sm.subscribe("task-1")
        q2 = sm.subscribe("task-1")
        event = SSEEvent(event_type=SSEEventType.MESSAGE, task_id="task-1", data={"content": "hi"})
        sm._emit_sync(event)
        assert not q1.empty()
        assert not q2.empty()

    def test_has_subscribers_false(self, sm):
        assert not sm.has_subscribers("nonexistent")


class TestSSEEventGenerator:

    @pytest.mark.asyncio
    async def test_yields_status_event(self, sm):
        queue = sm.subscribe("task-1")
        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="task-1",
            data={"status": "completed"},
        )
        queue.put_nowait(event)

        chunks = []
        async for chunk in sse_event_generator("task-1", queue, sm):
            chunks.append(chunk)
            if len(chunks) >= 1:
                break

        assert len(chunks) == 1
        assert "event: status" in chunks[0]
        assert '"status":"completed"' in chunks[0]

    @pytest.mark.asyncio
    async def test_terminates_on_completed(self, sm):
        queue = sm.subscribe("task-1")
        queue.put_nowait(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="task-1",
            data={"status": "working"},
        ))
        queue.put_nowait(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="task-1",
            data={"status": "completed"},
        ))

        chunks = []
        async for chunk in sse_event_generator("task-1", queue, sm):
            chunks.append(chunk)

        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_terminates_on_failed(self, sm):
        queue = sm.subscribe("task-1")
        queue.put_nowait(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="task-1",
            data={"status": "failed"},
        ))

        chunks = []
        async for chunk in sse_event_generator("task-1", queue, sm):
            chunks.append(chunk)

        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_message_event(self, sm):
        queue = sm.subscribe("task-1")
        queue.put_nowait(SSEEvent(
            event_type=SSEEventType.MESSAGE,
            task_id="task-1",
            data={"content": "hello"},
        ))
        # Add terminal event to end the stream
        queue.put_nowait(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="task-1",
            data={"status": "completed"},
        ))

        chunks = []
        async for chunk in sse_event_generator("task-1", queue, sm):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert "event: message" in chunks[0]

    @pytest.mark.asyncio
    async def test_artifact_event(self, sm):
        queue = sm.subscribe("task-1")
        queue.put_nowait(SSEEvent(
            event_type=SSEEventType.ARTIFACT,
            task_id="task-1",
            data={"type": "text", "name": "result"},
        ))
        queue.put_nowait(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="task-1",
            data={"status": "completed"},
        ))

        chunks = []
        async for chunk in sse_event_generator("task-1", queue, sm):
            chunks.append(chunk)

        assert "event: artifact" in chunks[0]

    @pytest.mark.asyncio
    async def test_keepalive_on_timeout(self, sm):
        queue = sm.subscribe("task-1")

        chunks = []
        # Use a very short keepalive to trigger timeout
        gen = sse_event_generator("task-1", queue, sm, keepalive_interval=0.1)
        chunk = await gen.__anext__()
        chunks.append(chunk)

        assert ": keepalive" in chunks[0]
