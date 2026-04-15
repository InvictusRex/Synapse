"""
Tests for A2A Task Manager - state machine and task lifecycle
"""
import pytest

from a2a.models import A2AMessage, Artifact, ArtifactType, MessageRole, TaskStatus
from a2a.task_manager import TaskManager, VALID_TRANSITIONS
from a2a.errors import A2AException
from a2a.streaming import StreamManager


@pytest.fixture
def stream_manager():
    return StreamManager()


@pytest.fixture
def tm(stream_manager):
    return TaskManager(stream_manager=stream_manager)


# ============================================================
# State Machine Transition Rules
# ============================================================

class TestValidTransitions:

    def test_submitted_can_go_to_working(self):
        assert TaskStatus.WORKING in VALID_TRANSITIONS[TaskStatus.SUBMITTED]

    def test_submitted_can_go_to_canceled(self):
        assert TaskStatus.CANCELED in VALID_TRANSITIONS[TaskStatus.SUBMITTED]

    def test_working_can_go_to_completed(self):
        assert TaskStatus.COMPLETED in VALID_TRANSITIONS[TaskStatus.WORKING]

    def test_working_can_go_to_failed(self):
        assert TaskStatus.FAILED in VALID_TRANSITIONS[TaskStatus.WORKING]

    def test_working_can_go_to_input_required(self):
        assert TaskStatus.INPUT_REQUIRED in VALID_TRANSITIONS[TaskStatus.WORKING]

    def test_working_can_go_to_canceled(self):
        assert TaskStatus.CANCELED in VALID_TRANSITIONS[TaskStatus.WORKING]

    def test_input_required_can_go_to_working(self):
        assert TaskStatus.WORKING in VALID_TRANSITIONS[TaskStatus.INPUT_REQUIRED]

    def test_input_required_can_go_to_canceled(self):
        assert TaskStatus.CANCELED in VALID_TRANSITIONS[TaskStatus.INPUT_REQUIRED]

    def test_completed_is_terminal(self):
        assert VALID_TRANSITIONS[TaskStatus.COMPLETED] == set()

    def test_failed_is_terminal(self):
        assert VALID_TRANSITIONS[TaskStatus.FAILED] == set()

    def test_canceled_is_terminal(self):
        assert VALID_TRANSITIONS[TaskStatus.CANCELED] == set()


# ============================================================
# Task Creation
# ============================================================

class TestTaskCreation:

    def test_create_task(self, tm):
        task = tm.create_task("Hello")
        assert task.status == TaskStatus.SUBMITTED
        assert len(task.id) > 0
        assert len(task.messages) == 1
        assert task.messages[0].role == MessageRole.USER
        assert task.messages[0].content == "Hello"

    def test_create_task_with_skill(self, tm):
        task = tm.create_task("test", skill_id="code_generation")
        assert task.metadata["skill_id"] == "code_generation"

    def test_create_task_with_metadata(self, tm):
        task = tm.create_task("test", metadata={"priority": "high"})
        assert task.metadata["priority"] == "high"

    def test_created_task_is_stored(self, tm):
        task = tm.create_task("test")
        retrieved = tm.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id

    def test_get_nonexistent_task(self, tm):
        assert tm.get_task("nonexistent") is None


# ============================================================
# State Transitions
# ============================================================

class TestStateTransitions:

    def test_submitted_to_working(self, tm):
        task = tm.create_task("test")
        task = tm.transition(task.id, TaskStatus.WORKING, "Starting")
        assert task.status == TaskStatus.WORKING
        assert len(task.history) == 1
        assert task.history[0].from_state == TaskStatus.SUBMITTED
        assert task.history[0].to_state == TaskStatus.WORKING

    def test_working_to_completed(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        task = tm.transition(task.id, TaskStatus.COMPLETED, "Done")
        assert task.status == TaskStatus.COMPLETED

    def test_working_to_failed(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        task = tm.transition(task.id, TaskStatus.FAILED, "Error occurred")
        assert task.status == TaskStatus.FAILED

    def test_working_to_input_required(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        task = tm.transition(task.id, TaskStatus.INPUT_REQUIRED, "Need more info")
        assert task.status == TaskStatus.INPUT_REQUIRED

    def test_input_required_to_working(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        tm.transition(task.id, TaskStatus.INPUT_REQUIRED)
        task = tm.transition(task.id, TaskStatus.WORKING, "Resuming")
        assert task.status == TaskStatus.WORKING

    def test_cancel_from_submitted(self, tm):
        task = tm.create_task("test")
        task = tm.cancel_task(task.id, "Not needed")
        assert task.status == TaskStatus.CANCELED

    def test_cancel_from_working(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        task = tm.cancel_task(task.id)
        assert task.status == TaskStatus.CANCELED

    def test_cancel_from_input_required(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        tm.transition(task.id, TaskStatus.INPUT_REQUIRED)
        task = tm.cancel_task(task.id)
        assert task.status == TaskStatus.CANCELED

    def test_history_tracks_all_transitions(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        tm.transition(task.id, TaskStatus.INPUT_REQUIRED)
        tm.transition(task.id, TaskStatus.WORKING)
        task = tm.transition(task.id, TaskStatus.COMPLETED)
        assert len(task.history) == 4

    def test_updated_at_changes(self, tm):
        task = tm.create_task("test")
        original = task.updated_at
        task = tm.transition(task.id, TaskStatus.WORKING)
        assert task.updated_at >= original


# ============================================================
# Invalid Transitions
# ============================================================

class TestInvalidTransitions:

    def test_submitted_to_completed_fails(self, tm):
        task = tm.create_task("test")
        with pytest.raises(A2AException) as exc_info:
            tm.transition(task.id, TaskStatus.COMPLETED)
        assert exc_info.value.code == 400

    def test_submitted_to_failed_fails(self, tm):
        task = tm.create_task("test")
        with pytest.raises(A2AException):
            tm.transition(task.id, TaskStatus.FAILED)

    def test_completed_to_working_fails(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        tm.transition(task.id, TaskStatus.COMPLETED)
        with pytest.raises(A2AException):
            tm.transition(task.id, TaskStatus.WORKING)

    def test_failed_to_working_fails(self, tm):
        task = tm.create_task("test")
        tm.transition(task.id, TaskStatus.WORKING)
        tm.transition(task.id, TaskStatus.FAILED)
        with pytest.raises(A2AException):
            tm.transition(task.id, TaskStatus.WORKING)

    def test_canceled_to_working_fails(self, tm):
        task = tm.create_task("test")
        tm.cancel_task(task.id)
        with pytest.raises(A2AException):
            tm.transition(task.id, TaskStatus.WORKING)

    def test_transition_nonexistent_task_fails(self, tm):
        with pytest.raises(A2AException) as exc_info:
            tm.transition("nonexistent", TaskStatus.WORKING)
        assert exc_info.value.code == 404


# ============================================================
# Messages
# ============================================================

class TestMessages:

    def test_add_user_message(self, tm):
        task = tm.create_task("initial")
        msg = A2AMessage(role=MessageRole.USER, content="follow up")
        task = tm.add_message(task.id, msg)
        assert len(task.messages) == 2
        assert task.messages[1].content == "follow up"

    def test_add_agent_message(self, tm):
        task = tm.create_task("initial")
        msg = A2AMessage(role=MessageRole.AGENT, content="here is the result")
        task = tm.add_message(task.id, msg)
        assert task.messages[1].role == MessageRole.AGENT

    def test_add_message_nonexistent_task(self, tm):
        msg = A2AMessage(role=MessageRole.USER, content="test")
        with pytest.raises(A2AException) as exc_info:
            tm.add_message("nonexistent", msg)
        assert exc_info.value.code == 404

    def test_message_ordering(self, tm):
        task = tm.create_task("first")
        tm.add_message(task.id, A2AMessage(role=MessageRole.AGENT, content="second"))
        tm.add_message(task.id, A2AMessage(role=MessageRole.USER, content="third"))
        task = tm.get_task(task.id)
        assert [m.content for m in task.messages] == ["first", "second", "third"]


# ============================================================
# Artifacts
# ============================================================

class TestArtifacts:

    def test_add_artifact(self, tm):
        task = tm.create_task("test")
        artifact = Artifact(type=ArtifactType.TEXT, name="result", data="hello")
        task = tm.add_artifact(task.id, artifact)
        assert len(task.artifacts) == 1
        assert task.artifacts[0].name == "result"

    def test_add_multiple_artifacts(self, tm):
        task = tm.create_task("test")
        tm.add_artifact(task.id, Artifact(type=ArtifactType.TEXT, name="a", data="1"))
        task = tm.add_artifact(task.id, Artifact(type=ArtifactType.FILE, name="b", uri="/path"))
        assert len(task.artifacts) == 2

    def test_append_artifact(self, tm):
        task = tm.create_task("test")
        tm.add_artifact(task.id, Artifact(type=ArtifactType.TEXT, name="stream", data="chunk1", index=0))
        task = tm.add_artifact(task.id, Artifact(type=ArtifactType.TEXT, name="stream", data="chunk2", index=0, append=True))
        assert task.artifacts[0].data == "chunk1chunk2"

    def test_add_artifact_nonexistent_task(self, tm):
        artifact = Artifact(type=ArtifactType.TEXT, name="test", data="data")
        with pytest.raises(A2AException):
            tm.add_artifact("nonexistent", artifact)
