"""
A2A FastAPI Server
HTTP endpoints for the Agent-to-Agent protocol
"""
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from a2a.models import (
    A2AMessage,
    MessageRole,
    ResubscribeRequest,
    TaskCancelRequest,
    TaskCancelResponse,
    TaskGetRequest,
    TaskGetResponse,
    TaskSendRequest,
    TaskSendResponse,
    TaskStatus,
    WebhookRegistration,
    WebhookRegistrationResponse,
)
from a2a.errors import (
    A2AException,
    a2a_exception_handler,
    internal_error,
    invalid_request,
    task_not_found,
    webhook_not_found,
)
from a2a.task_manager import TaskManager
from a2a.agent_registry import AgentRegistry
from a2a.streaming import StreamManager, sse_event_generator
from a2a.push_notifications import PushNotificationDispatcher
from a2a.auth import verify_auth


def create_app(
    synapse=None,
    task_manager: Optional[TaskManager] = None,
    agent_registry: Optional[AgentRegistry] = None,
    stream_manager: Optional[StreamManager] = None,
    push_dispatcher: Optional[PushNotificationDispatcher] = None,
) -> FastAPI:
    """
    Create the FastAPI application with all A2A endpoints.
    Accepts pre-built components or creates defaults.
    """
    # Initialize components
    if stream_manager is None:
        stream_manager = StreamManager()
    if push_dispatcher is None:
        push_dispatcher = PushNotificationDispatcher()
    if task_manager is None:
        task_manager = TaskManager(
            stream_manager=stream_manager,
            push_dispatcher=push_dispatcher,
        )
    if synapse is None:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from synapse import get_synapse
        synapse = get_synapse()
    if agent_registry is None:
        agent_registry = AgentRegistry(synapse, task_manager)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Startup
        loop = asyncio.get_running_loop()
        stream_manager.set_loop(loop)
        task_manager.set_loop(loop)
        yield
        # Shutdown (nothing needed)

    app = FastAPI(
        title="Synapse A2A Protocol",
        description="Agent-to-Agent protocol server for the Synapse multi-agent system",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register exception handler
    app.add_exception_handler(A2AException, a2a_exception_handler)

    # Store components on app state for access in endpoints
    app.state.task_manager = task_manager
    app.state.agent_registry = agent_registry
    app.state.stream_manager = stream_manager
    app.state.push_dispatcher = push_dispatcher
    app.state.synapse = synapse

    # ==================== Public Endpoints ====================

    @app.get("/.well-known/agent.json")
    async def agent_card(request: Request):
        """Agent Discovery - serve agent metadata"""
        base_url = str(request.base_url).rstrip("/")
        card = agent_registry.get_agent_card(base_url)
        return card.model_dump()

    @app.get("/health")
    async def health():
        """Health check"""
        status = synapse.get_status()
        return {
            "status": "ok",
            "agents": len(status["agents"]),
            "tools": status["mcp"]["tools_registered"],
        }

    # ==================== Task Lifecycle (Protected) ====================

    @app.post("/tasks/send", dependencies=[Depends(verify_auth)])
    async def tasks_send(req: TaskSendRequest) -> TaskSendResponse:
        """
        Create a new task or continue an existing one.
        - No task_id: creates new task, executes through Synapse pipeline
        - With task_id: continues an input-required task
        """
        if req.task_id:
            # Continue existing task
            task = task_manager.get_task(req.task_id)
            if not task:
                raise task_not_found(req.task_id)
            if task.status != TaskStatus.INPUT_REQUIRED:
                raise invalid_request(
                    f"Task {req.task_id} is in '{task.status.value}' state, "
                    f"expected 'input-required' for continuation"
                )
            # Add user message and resume
            task_manager.add_message(
                req.task_id,
                A2AMessage(role=MessageRole.USER, content=req.message),
            )
            # Resume execution in background thread
            await asyncio.to_thread(
                agent_registry.execute,
                req.task_id,
                req.message,
                req.skill_id,
            )
            task = task_manager.get_task(req.task_id)
            return TaskSendResponse(task=task)

        # Create new task
        task = task_manager.create_task(
            message=req.message,
            skill_id=req.skill_id,
            metadata=req.metadata,
        )

        # Execute in background thread
        await asyncio.to_thread(
            agent_registry.execute,
            task.id,
            req.message,
            req.skill_id,
        )

        # Get updated task
        task = task_manager.get_task(task.id)
        return TaskSendResponse(task=task)

    @app.post("/tasks/get", dependencies=[Depends(verify_auth)])
    async def tasks_get(req: TaskGetRequest) -> TaskGetResponse:
        """Get current task state, message history, and artifacts"""
        task = task_manager.get_task(req.task_id)
        if not task:
            raise task_not_found(req.task_id)
        return TaskGetResponse(task=task)

    @app.post("/tasks/cancel", dependencies=[Depends(verify_auth)])
    async def tasks_cancel(req: TaskCancelRequest) -> TaskCancelResponse:
        """Cancel an in-progress task"""
        task = task_manager.get_task(req.task_id)
        if not task:
            raise task_not_found(req.task_id)
        task = task_manager.cancel_task(req.task_id, req.reason)
        return TaskCancelResponse(task=task)

    # ==================== Streaming (Protected) ====================

    @app.post("/tasks/sendSubscribe", dependencies=[Depends(verify_auth)])
    async def tasks_send_subscribe(req: TaskSendRequest):
        """
        Send a task and subscribe to SSE updates in one call.
        Returns an SSE stream instead of a JSON response.
        """
        if req.task_id:
            # Continue existing task
            task = task_manager.get_task(req.task_id)
            if not task:
                raise task_not_found(req.task_id)
            if task.status != TaskStatus.INPUT_REQUIRED:
                raise invalid_request(
                    f"Task {req.task_id} is in '{task.status.value}' state, "
                    f"expected 'input-required' for continuation"
                )
            task_manager.add_message(
                req.task_id,
                A2AMessage(role=MessageRole.USER, content=req.message),
            )
            task_id = req.task_id
        else:
            task = task_manager.create_task(
                message=req.message,
                skill_id=req.skill_id,
                metadata=req.metadata,
            )
            task_id = task.id

        # Subscribe to events
        queue = stream_manager.subscribe(task_id)

        # Start execution in background
        asyncio.get_running_loop().run_in_executor(
            None,
            agent_registry.execute,
            task_id,
            req.message,
            req.skill_id,
        )

        return StreamingResponse(
            sse_event_generator(task_id, queue, stream_manager),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/tasks/resubscribe", dependencies=[Depends(verify_auth)])
    async def tasks_resubscribe(req: ResubscribeRequest):
        """
        Reconnect to SSE updates for an existing task.
        Useful after a disconnect.
        """
        task = task_manager.get_task(req.task_id)
        if not task:
            raise task_not_found(req.task_id)

        # If task is already in a terminal state, return single event
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED):
            async def terminal_stream():
                from a2a.models import SSEEvent, SSEEventType
                event = SSEEvent(
                    event_type=SSEEventType.STATUS,
                    task_id=req.task_id,
                    data={"status": task.status.value},
                )
                yield f"event: {event.event_type.value}\ndata: {event.model_dump_json()}\n\n"

            return StreamingResponse(
                terminal_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

        # Subscribe to ongoing events
        queue = stream_manager.subscribe(req.task_id)

        return StreamingResponse(
            sse_event_generator(req.task_id, queue, stream_manager),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ==================== Push Notifications (Protected) ====================

    @app.post("/webhooks/register", dependencies=[Depends(verify_auth)])
    async def webhooks_register(req: WebhookRegistration) -> WebhookRegistrationResponse:
        """Register a webhook for push notifications"""
        webhook_id = push_dispatcher.register(req)
        return WebhookRegistrationResponse(id=webhook_id)

    @app.delete("/webhooks/{webhook_id}", dependencies=[Depends(verify_auth)])
    async def webhooks_unregister(webhook_id: str):
        """Unregister a webhook"""
        if not push_dispatcher.unregister(webhook_id):
            raise webhook_not_found(webhook_id)
        return {"ok": True}

    return app
