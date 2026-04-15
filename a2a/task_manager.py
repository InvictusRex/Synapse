"""
A2A Task Manager
Task lifecycle state machine with in-memory storage
"""
import asyncio
import threading
from datetime import datetime, timezone
from typing import Optional

from a2a.models import (
    A2AMessage,
    Artifact,
    MessageRole,
    SSEEvent,
    SSEEventType,
    Task,
    TaskStatus,
    TaskStateTransition,
)
from a2a.errors import invalid_transition, task_not_found


# Valid state transitions
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.SUBMITTED: {TaskStatus.WORKING, TaskStatus.CANCELED},
    TaskStatus.WORKING: {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.INPUT_REQUIRED,
        TaskStatus.CANCELED,
    },
    TaskStatus.INPUT_REQUIRED: {TaskStatus.WORKING, TaskStatus.CANCELED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELED: set(),
}


class TaskManager:
    """
    Manages task lifecycle with a 6-state state machine.
    Thread-safe — can be called from sync agent threads.
    Emits SSE events via StreamManager and push notifications via PushNotificationDispatcher.
    """

    def __init__(self, stream_manager=None, push_dispatcher=None):
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._stream_manager = stream_manager
        self._push_dispatcher = push_dispatcher
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the async event loop for thread-safe event emission"""
        self._loop = loop

    # ==================== Task CRUD ====================

    def create_task(self, message: str, skill_id: Optional[str] = None,
                    metadata: Optional[dict] = None) -> Task:
        """Create a new task in SUBMITTED state"""
        task = Task(metadata=metadata or {})
        task.messages.append(
            A2AMessage(role=MessageRole.USER, content=message)
        )
        if skill_id:
            task.metadata["skill_id"] = skill_id

        with self._lock:
            self._tasks[task.id] = task

        self._emit_event(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id=task.id,
            data={"status": task.status.value, "task_id": task.id},
        ))
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        with self._lock:
            return self._tasks.get(task_id)

    # ==================== State Machine ====================

    def transition(self, task_id: str, new_status: TaskStatus,
                   reason: str = "") -> Task:
        """
        Transition a task to a new state.
        Validates the transition against the state machine.
        Records the transition in history.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise task_not_found(task_id)

            if new_status not in VALID_TRANSITIONS.get(task.status, set()):
                raise invalid_transition(task.status.value, new_status.value)

            old_status = task.status
            task.status = new_status
            task.updated_at = datetime.now(timezone.utc)
            task.history.append(TaskStateTransition(
                from_state=old_status,
                to_state=new_status,
                reason=reason,
            ))

        # Emit events outside the lock
        self._emit_event(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id=task_id,
            data={
                "status": new_status.value,
                "previous_status": old_status.value,
                "reason": reason,
            },
        ))

        # Push notification for terminal states
        if new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
            self._push_task_event("task/completed", task)
        else:
            self._push_task_event("task/updated", task)

        return task

    # ==================== Messages ====================

    def add_message(self, task_id: str, message: A2AMessage) -> Task:
        """Add a message to a task's conversation history"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise task_not_found(task_id)
            task.messages.append(message)
            task.updated_at = datetime.now(timezone.utc)

        self._emit_event(SSEEvent(
            event_type=SSEEventType.MESSAGE,
            task_id=task_id,
            data={
                "role": message.role.value,
                "content": message.content,
            },
        ))
        return task

    # ==================== Artifacts ====================

    def add_artifact(self, task_id: str, artifact: Artifact) -> Task:
        """Add an artifact to a task"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise task_not_found(task_id)

            if artifact.append and artifact.index < len(task.artifacts):
                # Append to existing artifact
                existing = task.artifacts[artifact.index]
                if existing.data and artifact.data:
                    existing.data += artifact.data
            else:
                task.artifacts.append(artifact)
            task.updated_at = datetime.now(timezone.utc)

        self._emit_event(SSEEvent(
            event_type=SSEEventType.ARTIFACT,
            task_id=task_id,
            data=artifact.model_dump(),
        ))
        return task

    # ==================== Cancel ====================

    def cancel_task(self, task_id: str, reason: str = "") -> Task:
        """Cancel a task"""
        return self.transition(task_id, TaskStatus.CANCELED, reason or "Canceled by client")

    # ==================== Progress Events ====================

    def emit_progress(self, task_id: str, event_type: str, data: dict) -> None:
        """
        Emit a progress event for a task (non-transition).
        Used to stream real-time execution updates (stage changes, per-task progress).
        """
        self._emit_event(SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id=task_id,
            data={"progress": event_type, **data},
        ))

    # ==================== Event Emission ====================

    def _emit_event(self, event: SSEEvent):
        """Emit an SSE event via StreamManager (thread-safe)"""
        if self._stream_manager:
            self._stream_manager.emit(event)

    def _push_task_event(self, event_name: str, task: Task):
        """Dispatch a push notification (async, non-blocking)"""
        if self._push_dispatcher and self._loop:
            from a2a.models import PushEvent
            push_event = PushEvent(
                event=event_name,
                task_id=task.id,
                task=task,
            )
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(
                    self._push_dispatcher.dispatch(push_event)
                )
            )
