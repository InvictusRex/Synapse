"""
Tests for Scaffolding Agent
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from tools.all_tools import register_all_tools
from agents.scaffolding_agent import ScaffoldingAgent
from mcp.server import ToolCategory


@pytest.fixture
def scaffolding_agent():
    """Create a Scaffolding Agent with tools registered"""
    register_all_tools()
    agent = ScaffoldingAgent()
    agent.start()
    yield agent
    agent.stop()


class TestScaffoldingAgentConfig:

    def test_agent_id(self, scaffolding_agent):
        assert scaffolding_agent.agent_id == "scaffolding_agent"

    def test_agent_name(self, scaffolding_agent):
        assert scaffolding_agent.config.name == "Scaffolding Agent"

    def test_agent_has_development_category(self, scaffolding_agent):
        assert ToolCategory.DEVELOPMENT in scaffolding_agent.config.tool_categories

    def test_agent_has_filesystem_category(self, scaffolding_agent):
        assert ToolCategory.FILESYSTEM in scaffolding_agent.config.tool_categories

    def test_agent_capabilities(self, scaffolding_agent):
        caps = scaffolding_agent.config.capabilities
        assert len(caps) > 0
        caps_text = " ".join(caps).lower()
        assert "scaffold" in caps_text or "bootstrap" in caps_text or "project" in caps_text

    def test_agent_running(self, scaffolding_agent):
        assert scaffolding_agent.running is True

    def test_agent_has_scaffold_tool(self, scaffolding_agent):
        tools = scaffolding_agent._get_my_tools_list()
        assert "scaffold_project" in tools

    def test_agent_has_list_templates_tool(self, scaffolding_agent):
        tools = scaffolding_agent._get_my_tools_list()
        assert "list_templates" in tools


class TestScaffoldingAgentTaskHandling:

    def test_handle_task_scaffold_project(self, scaffolding_agent, temp_dir):
        task = {
            "tool": "scaffold_project",
            "args": {
                "project_name": "TestApp",
                "template": "python",
                "directory": temp_dir
            }
        }
        result = scaffolding_agent.handle_task(task)
        assert result["success"] is True
        assert result["project_name"] == "TestApp"
        assert os.path.isdir(os.path.join(temp_dir, "TestApp"))
        assert os.path.isfile(os.path.join(temp_dir, "TestApp", "main.py"))

    def test_handle_task_scaffold_react(self, scaffolding_agent, temp_dir):
        task = {
            "tool": "scaffold_project",
            "args": {
                "project_name": "ReactApp",
                "template": "react",
                "directory": temp_dir
            }
        }
        result = scaffolding_agent.handle_task(task)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "ReactApp", "package.json"))

    def test_handle_task_scaffold_invalid_template(self, scaffolding_agent, temp_dir):
        task = {
            "tool": "scaffold_project",
            "args": {
                "project_name": "App",
                "template": "invalid_template",
                "directory": temp_dir
            }
        }
        result = scaffolding_agent.handle_task(task)
        assert result["success"] is False

    def test_handle_task_list_templates(self, scaffolding_agent):
        task = {
            "tool": "list_templates",
            "args": {}
        }
        result = scaffolding_agent.handle_task(task)
        assert result["success"] is True
        assert "project_templates" in result

    def test_handle_task_unknown_tool(self, scaffolding_agent):
        task = {
            "tool": "nonexistent_tool",
            "args": {}
        }
        result = scaffolding_agent.handle_task(task)
        assert result["success"] is False

    def test_handle_task_scaffold_duplicate_directory(self, scaffolding_agent, temp_dir):
        os.makedirs(os.path.join(temp_dir, "Existing"))
        task = {
            "tool": "scaffold_project",
            "args": {
                "project_name": "Existing",
                "template": "python",
                "directory": temp_dir
            }
        }
        result = scaffolding_agent.handle_task(task)
        assert result["success"] is False
        assert "already exists" in result["error"]


class TestScaffoldingAgentMessaging:

    def test_handle_task_request_message(self, scaffolding_agent, temp_dir):
        from core.a2a_bus import Message, MessageType

        msg = Message.create(
            sender="orchestrator_agent",
            recipient="scaffolding_agent",
            msg_type=MessageType.TASK_REQUEST,
            payload={
                "tool": "scaffold_project",
                "args": {
                    "project_name": "MsgApp",
                    "template": "node",
                    "directory": temp_dir
                }
            }
        )
        result = scaffolding_agent.handle_message(msg)
        assert result is not None
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "MsgApp", "index.js"))

    def test_handle_tool_request_message(self, scaffolding_agent):
        from core.a2a_bus import Message, MessageType

        msg = Message.create(
            sender="orchestrator_agent",
            recipient="scaffolding_agent",
            msg_type=MessageType.TOOL_REQUEST,
            payload={
                "tool": "list_templates",
                "args": {}
            }
        )
        result = scaffolding_agent.handle_message(msg)
        assert result is not None
        assert result["success"] is True

    def test_handle_irrelevant_message(self, scaffolding_agent):
        from core.a2a_bus import Message, MessageType

        msg = Message.create(
            sender="test",
            recipient="scaffolding_agent",
            msg_type=MessageType.INFO_REQUEST,
            payload={}
        )
        result = scaffolding_agent.handle_message(msg)
        assert result is None
