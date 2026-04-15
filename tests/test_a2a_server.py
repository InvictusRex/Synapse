"""
Tests for A2A FastAPI Server endpoints
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from a2a.models import TaskStatus
from a2a.task_manager import TaskManager
from a2a.streaming import StreamManager
from a2a.push_notifications import PushNotificationDispatcher
from a2a.agent_registry import AgentRegistry
from a2a.server import create_app
from a2a.auth import reset_auth_config


@pytest.fixture(autouse=True)
def reset_auth():
    reset_auth_config()
    yield
    reset_auth_config()


@pytest.fixture
def mock_synapse():
    """Create a mock Synapse instance"""
    synapse = MagicMock()
    synapse.get_status.return_value = {
        "agents": [{"name": "Agent1", "running": True, "tools": []}],
        "mcp": {"tools_registered": 28, "total_executions": 0, "successful": 0, "failed": 0},
        "bus": {"registered_agents": ["agent1"], "message_count": 0},
    }
    synapse.process.return_value = {
        "success": True,
        "formatted_result": "Task completed successfully",
        "final_output": {
            "all_outputs": [
                {"type": "generate_text", "content": "Generated content here"}
            ]
        },
        "stages": {},
    }
    return synapse


@pytest.fixture
def app(mock_synapse):
    """Create FastAPI test app"""
    sm = StreamManager()
    pd = PushNotificationDispatcher()
    tm = TaskManager(stream_manager=sm, push_dispatcher=pd)
    ar = AgentRegistry(mock_synapse, tm)

    with patch.dict(os.environ, {"A2A_API_KEYS": "test-key", "A2A_BEARER_TOKENS": "test-token"}, clear=False):
        reset_auth_config()
        application = create_app(
            synapse=mock_synapse,
            task_manager=tm,
            agent_registry=ar,
            stream_manager=sm,
            push_dispatcher=pd,
        )
        yield application
        reset_auth_config()


@pytest.fixture
def client(app):
    with patch.dict(os.environ, {"A2A_API_KEYS": "test-key", "A2A_BEARER_TOKENS": "test-token"}, clear=False):
        reset_auth_config()
        yield TestClient(app)


AUTH_HEADER = {"x-api-key": "test-key"}
BEARER_HEADER = {"authorization": "Bearer test-token"}


# ============================================================
# Public Endpoints
# ============================================================

class TestAgentCard:

    def test_agent_card_endpoint(self, client):
        resp = client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Synapse"
        assert "capabilities" in data
        assert "skills" in data
        assert len(data["skills"]) > 0

    def test_agent_card_capabilities(self, client):
        resp = client.get("/.well-known/agent.json")
        caps = resp.json()["capabilities"]
        assert caps["streaming"] is True
        assert caps["push_notifications"] is True
        assert caps["state_transition_history"] is True

    def test_agent_card_skills_have_required_fields(self, client):
        resp = client.get("/.well-known/agent.json")
        for skill in resp.json()["skills"]:
            assert "id" in skill
            assert "name" in skill
            assert "description" in skill

    def test_agent_card_auth_schemes(self, client):
        resp = client.get("/.well-known/agent.json")
        schemes = resp.json()["auth_schemes"]
        assert len(schemes) >= 2
        scheme_types = [s["scheme"] for s in schemes]
        assert "apiKey" in scheme_types
        assert "bearer" in scheme_types

    def test_agent_card_no_auth_required(self, client):
        resp = client.get("/.well-known/agent.json")
        assert resp.status_code == 200  # No auth header needed


class TestHealthCheck:

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "agents" in data
        assert "tools" in data

    def test_health_no_auth_required(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200


# ============================================================
# Authentication
# ============================================================

class TestAuthentication:

    def test_api_key_auth(self, client):
        resp = client.post("/tasks/send", json={"message": "test"}, headers=AUTH_HEADER)
        assert resp.status_code == 200

    def test_bearer_auth(self, client):
        resp = client.post("/tasks/send", json={"message": "test"}, headers=BEARER_HEADER)
        assert resp.status_code == 200

    def test_no_auth_rejected(self, client):
        resp = client.post("/tasks/send", json={"message": "test"})
        assert resp.status_code == 401

    def test_wrong_api_key_rejected(self, client):
        resp = client.post("/tasks/send", json={"message": "test"}, headers={"x-api-key": "wrong"})
        assert resp.status_code == 401

    def test_wrong_bearer_rejected(self, client):
        resp = client.post("/tasks/send", json={"message": "test"}, headers={"authorization": "Bearer wrong"})
        assert resp.status_code == 401


# ============================================================
# Task Lifecycle
# ============================================================

class TestTasksSend:

    def test_create_new_task(self, client):
        resp = client.post("/tasks/send", json={"message": "list files"}, headers=AUTH_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert "task" in data
        task = data["task"]
        assert len(task["id"]) > 0
        assert task["status"] in ["completed", "failed"]
        assert len(task["messages"]) >= 1

    def test_task_has_user_message(self, client):
        resp = client.post("/tasks/send", json={"message": "hello"}, headers=AUTH_HEADER)
        task = resp.json()["task"]
        user_msgs = [m for m in task["messages"] if m["role"] == "user"]
        assert len(user_msgs) >= 1
        assert user_msgs[0]["content"] == "hello"

    def test_task_with_skill_id(self, client):
        resp = client.post("/tasks/send", json={"message": "test", "skill_id": "general"}, headers=AUTH_HEADER)
        assert resp.status_code == 200

    def test_task_with_metadata(self, client):
        resp = client.post("/tasks/send", json={"message": "test", "metadata": {"priority": "high"}}, headers=AUTH_HEADER)
        task = resp.json()["task"]
        assert task["metadata"].get("priority") == "high"


class TestTasksGet:

    def test_get_existing_task(self, client):
        # Create a task first
        resp = client.post("/tasks/send", json={"message": "test"}, headers=AUTH_HEADER)
        task_id = resp.json()["task"]["id"]

        # Get it
        resp = client.post("/tasks/get", json={"task_id": task_id}, headers=AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.json()["task"]["id"] == task_id

    def test_get_nonexistent_task(self, client):
        resp = client.post("/tasks/get", json={"task_id": "nonexistent"}, headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_get_task_has_history(self, client):
        resp = client.post("/tasks/send", json={"message": "test"}, headers=AUTH_HEADER)
        task_id = resp.json()["task"]["id"]
        resp = client.post("/tasks/get", json={"task_id": task_id}, headers=AUTH_HEADER)
        task = resp.json()["task"]
        assert len(task["history"]) > 0

    def test_get_task_has_artifacts(self, client):
        resp = client.post("/tasks/send", json={"message": "test"}, headers=AUTH_HEADER)
        task = resp.json()["task"]
        # Artifacts may or may not be present depending on mock result
        assert "artifacts" in task


class TestTasksCancel:

    def test_cancel_nonexistent_task(self, client):
        resp = client.post("/tasks/cancel", json={"task_id": "nonexistent"}, headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_cancel_completed_task_fails(self, client):
        # Create and complete a task
        resp = client.post("/tasks/send", json={"message": "test"}, headers=AUTH_HEADER)
        task_id = resp.json()["task"]["id"]

        # Try to cancel (it's already completed)
        resp = client.post("/tasks/cancel", json={"task_id": task_id}, headers=AUTH_HEADER)
        assert resp.status_code == 400


# ============================================================
# Multi-turn Conversation
# ============================================================

class TestMultiTurn:

    def test_continue_nonexistent_task(self, client):
        resp = client.post("/tasks/send", json={"message": "answer", "task_id": "nonexistent"}, headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_continue_non_input_required_task(self, client):
        # Create and complete a task
        resp = client.post("/tasks/send", json={"message": "test"}, headers=AUTH_HEADER)
        task_id = resp.json()["task"]["id"]

        # Try to continue (not in input-required state)
        resp = client.post("/tasks/send", json={"message": "more", "task_id": task_id}, headers=AUTH_HEADER)
        assert resp.status_code == 400


# ============================================================
# Webhooks
# ============================================================

class TestWebhooks:

    def test_register_webhook(self, client):
        resp = client.post(
            "/webhooks/register",
            json={"url": "https://example.com/hook"},
            headers=AUTH_HEADER,
        )
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_unregister_webhook(self, client):
        # Register
        resp = client.post(
            "/webhooks/register",
            json={"url": "https://example.com/hook"},
            headers=AUTH_HEADER,
        )
        wh_id = resp.json()["id"]

        # Unregister
        resp = client.delete(f"/webhooks/{wh_id}", headers=AUTH_HEADER)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_unregister_nonexistent_webhook(self, client):
        resp = client.delete("/webhooks/nonexistent", headers=AUTH_HEADER)
        assert resp.status_code == 404

    def test_webhook_auth_required(self, client):
        resp = client.post("/webhooks/register", json={"url": "https://example.com/hook"})
        assert resp.status_code == 401


# ============================================================
# Error Handling
# ============================================================

class TestErrorHandling:

    def test_error_response_format(self, client):
        resp = client.post("/tasks/get", json={"task_id": "nonexistent"}, headers=AUTH_HEADER)
        assert resp.status_code == 404
        data = resp.json()
        assert "code" in data
        assert "message" in data
        assert data["code"] == 404

    def test_retryable_error(self, client):
        resp = client.post("/tasks/cancel", json={"task_id": "nonexistent"}, headers=AUTH_HEADER)
        data = resp.json()
        assert "retryable" in data
