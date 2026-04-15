"""
A2A SSE Streaming
Server-Sent Events implementation for real-time task updates
"""
import asyncio
from typing import AsyncGenerator, Optional

from a2a.models import SSEEvent, SSEEventType


class StreamManager:
    """
    Manages SSE subscriptions for task updates.
    Thread-safe — emit() can be called from any thread.
    """

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the async event loop for thread-safe emission"""
        self._loop = loop

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to events for a task. Returns an asyncio.Queue."""
        queue: asyncio.Queue = asyncio.Queue()
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        """Unsubscribe from task events"""
        if task_id in self._subscribers:
            try:
                self._subscribers[task_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[task_id]:
                del self._subscribers[task_id]

    def emit(self, event: SSEEvent):
        """
        Emit an event to all subscribers of a task.
        Thread-safe — can be called from sync agent threads.
        """
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._emit_sync, event)
        else:
            # Fallback for when no loop is set (e.g., testing)
            self._emit_sync(event)

    def _emit_sync(self, event: SSEEvent):
        """Push event to all subscriber queues (must run on event loop thread)"""
        queues = self._subscribers.get(event.task_id, [])
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop event if queue is full

    def has_subscribers(self, task_id: str) -> bool:
        """Check if a task has any active subscribers"""
        return bool(self._subscribers.get(task_id))


async def sse_event_generator(
    task_id: str,
    queue: asyncio.Queue,
    stream_manager: StreamManager,
    keepalive_interval: float = 30.0,
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted events from a queue.
    Used with Starlette's StreamingResponse.

    Yields events in SSE format:
        event: <type>
        data: <json>

    Sends keepalive comments every keepalive_interval seconds.
    Terminates when a terminal status event is received.
    """
    terminal_statuses = {"completed", "failed", "canceled"}

    try:
        while True:
            try:
                event: SSEEvent = await asyncio.wait_for(
                    queue.get(), timeout=keepalive_interval
                )
                yield f"event: {event.event_type.value}\ndata: {event.model_dump_json()}\n\n"

                # Stop streaming on terminal status
                if (
                    event.event_type == SSEEventType.STATUS
                    and event.data.get("status") in terminal_statuses
                ):
                    break

            except asyncio.TimeoutError:
                # Send keepalive comment
                yield ": keepalive\n\n"

    finally:
        stream_manager.unsubscribe(task_id, queue)
