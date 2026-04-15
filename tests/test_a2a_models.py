"""
Tests for A2A Protocol Pydantic models
"""
import json
import pytest
from datetime import datetime, timezone

from a2a.models import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    Artifact,
    ArtifactType,
    AuthScheme,
    A2AError,
    A2AMessage,
    MessageRole,
    PushEvent,
    ResubscribeRequest,
    SkillInputSchema,
    SSEEvent,
    SSEEventType,
    Task,
    TaskCancelRequest,
    TaskCancelResponse,
    TaskGetRequest,
    TaskGetResponse,
    TaskSendRequest,
    TaskSendResponse,
    TaskStateTransition,
    TaskStatus,
    WebhookRegistration,
    WebhookRegistrationResponse,
)


class TestTaskStatusEnum:

    def test_all_states_present(self):
        assert TaskStatus.SUBMITTED == "submitted"
        assert TaskStatus.WORKING == "working"
        assert TaskStatus.INPUT_REQUIRED == "input-required"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELED == "canceled"

    def test_status_count(self):
        assert len(TaskStatus) == 6


class TestMessageRoleEnum:

    def test_roles(self):
        assert MessageRole.USER == "user"
        assert MessageRole.AGENT == "agent"


class TestArtifactTypeEnum:

    def test_all_types(self):
        assert ArtifactType.TEXT == "text"
        assert ArtifactType.FILE == "file"
        assert ArtifactType.IMAGE == "image"
        assert ArtifactType.STRUCTURED_DATA == "structured_data"
        assert ArtifactType.CUSTOM == "custom"

    def test_type_count(self):
        assert len(ArtifactType) == 5


class TestSSEEventTypeEnum:

    def test_all_types(self):
        assert SSEEventType.STATUS == "status"
        assert SSEEventType.ARTIFACT == "artifact"
        assert SSEEventType.MESSAGE == "message"
        assert SSEEventType.ERROR == "error"


class TestA2AMessage:

    def test_create_user_message(self):
        msg = A2AMessage(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)

    def test_create_agent_message(self):
        msg = A2AMessage(role=MessageRole.AGENT, content="Hi there")
        assert msg.role == MessageRole.AGENT

    def test_message_metadata(self):
        msg = A2AMessage(role=MessageRole.USER, content="test", metadata={"key": "val"})
        assert msg.metadata["key"] == "val"

    def test_message_serialization(self):
        msg = A2AMessage(role=MessageRole.USER, content="test")
        data = msg.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "test"


class TestArtifact:

    def test_text_artifact(self):
        a = Artifact(type=ArtifactType.TEXT, name="result", data="hello world")
        assert a.type == ArtifactType.TEXT
        assert a.data == "hello world"
        assert a.mime_type == "text/plain"

    def test_file_artifact_with_uri(self):
        a = Artifact(type=ArtifactType.FILE, name="report.pdf", uri="/path/to/file", mime_type="application/pdf")
        assert a.uri == "/path/to/file"
        assert a.data is None

    def test_streaming_artifact(self):
        a = Artifact(type=ArtifactType.TEXT, name="stream", data="chunk1", index=0, append=False)
        assert a.index == 0
        assert a.append is False

    def test_structured_data_artifact(self):
        a = Artifact(type=ArtifactType.STRUCTURED_DATA, name="data", mime_type="application/json", data='{"key": "value"}')
        assert a.type == ArtifactType.STRUCTURED_DATA

    def test_artifact_serialization(self):
        a = Artifact(type=ArtifactType.TEXT, name="test", data="content")
        data = a.model_dump()
        assert data["type"] == "text"
        assert data["name"] == "test"


class TestTask:

    def test_create_task_defaults(self):
        task = Task()
        assert task.status == TaskStatus.SUBMITTED
        assert len(task.id) > 0
        assert task.messages == []
        assert task.artifacts == []
        assert task.history == []
        assert isinstance(task.created_at, datetime)

    def test_task_with_messages(self):
        task = Task(messages=[A2AMessage(role=MessageRole.USER, content="test")])
        assert len(task.messages) == 1

    def test_task_serialization_roundtrip(self):
        task = Task()
        task.messages.append(A2AMessage(role=MessageRole.USER, content="hello"))
        task.artifacts.append(Artifact(type=ArtifactType.TEXT, name="r", data="world"))
        data = task.model_dump()
        restored = Task(**data)
        assert restored.id == task.id
        assert restored.status == task.status
        assert len(restored.messages) == 1
        assert len(restored.artifacts) == 1

    def test_task_json_serialization(self):
        task = Task()
        json_str = task.model_dump_json()
        parsed = json.loads(json_str)
        assert "id" in parsed
        assert parsed["status"] == "submitted"


class TestTaskStateTransition:

    def test_transition_record(self):
        t = TaskStateTransition(
            from_state=TaskStatus.SUBMITTED,
            to_state=TaskStatus.WORKING,
            reason="Processing started",
        )
        assert t.from_state == TaskStatus.SUBMITTED
        assert t.to_state == TaskStatus.WORKING
        assert t.reason == "Processing started"


class TestAgentCard:

    def test_agent_card_creation(self):
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:8000",
            skills=[AgentSkill(id="test", name="Test", description="A test skill")],
        )
        assert card.name == "Test Agent"
        assert card.version == "1.0.0"
        assert len(card.skills) == 1

    def test_agent_card_capabilities(self):
        caps = AgentCapabilities(streaming=True, push_notifications=True, state_transition_history=True)
        card = AgentCard(name="A", description="B", url="http://x", capabilities=caps)
        assert card.capabilities.streaming is True
        assert card.capabilities.push_notifications is True

    def test_agent_card_auth_schemes(self):
        card = AgentCard(
            name="A", description="B", url="http://x",
            auth_schemes=[
                AuthScheme(scheme="apiKey", description="API key auth"),
                AuthScheme(scheme="bearer", description="Bearer token auth"),
            ],
        )
        assert len(card.auth_schemes) == 2
        assert card.auth_schemes[0].scheme == "apiKey"

    def test_agent_card_serialization(self):
        card = AgentCard(name="A", description="B", url="http://x")
        data = card.model_dump()
        assert "name" in data
        assert "capabilities" in data
        assert "skills" in data


class TestRequestResponseModels:

    def test_task_send_request_new(self):
        req = TaskSendRequest(message="do something")
        assert req.message == "do something"
        assert req.task_id is None
        assert req.skill_id is None

    def test_task_send_request_continue(self):
        req = TaskSendRequest(message="yes", task_id="abc-123")
        assert req.task_id == "abc-123"

    def test_task_get_request(self):
        req = TaskGetRequest(task_id="abc-123")
        assert req.task_id == "abc-123"

    def test_task_cancel_request(self):
        req = TaskCancelRequest(task_id="abc-123", reason="No longer needed")
        assert req.reason == "No longer needed"

    def test_resubscribe_request(self):
        req = ResubscribeRequest(task_id="abc-123")
        assert req.task_id == "abc-123"

    def test_task_send_response(self):
        task = Task()
        resp = TaskSendResponse(task=task)
        assert resp.task.id == task.id


class TestSSEEvent:

    def test_status_event(self):
        event = SSEEvent(
            event_type=SSEEventType.STATUS,
            task_id="abc",
            data={"status": "working"},
        )
        assert event.event_type == SSEEventType.STATUS
        assert event.data["status"] == "working"

    def test_event_json(self):
        event = SSEEvent(event_type=SSEEventType.MESSAGE, task_id="abc", data={"content": "hi"})
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "message"


class TestWebhookModels:

    def test_webhook_registration(self):
        wh = WebhookRegistration(url="https://example.com/hook", secret="my-secret")
        assert wh.url == "https://example.com/hook"
        assert "task/updated" in wh.events
        assert "task/completed" in wh.events

    def test_webhook_registration_response(self):
        resp = WebhookRegistrationResponse(id="abc-123")
        assert resp.id == "abc-123"

    def test_push_event(self):
        task = Task()
        event = PushEvent(event="task/completed", task_id=task.id, task=task)
        assert event.event == "task/completed"


class TestA2AError:

    def test_error_model(self):
        err = A2AError(code=404, message="Not found")
        assert err.code == 404
        assert err.retryable is False
        assert err.retry_after_seconds is None

    def test_retryable_error(self):
        err = A2AError(code=429, message="Busy", retryable=True, retry_after_seconds=5)
        assert err.retryable is True
        assert err.retry_after_seconds == 5

    def test_error_with_data(self):
        err = A2AError(code=400, message="Bad", data={"field": "value"})
        assert err.data["field"] == "value"
