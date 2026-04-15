"""
Tests for Implementation Agent
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from tools.all_tools import register_all_tools
from agents.implementation_agent import ImplementationAgent
from mcp.server import ToolCategory


@pytest.fixture
def impl_agent():
    """Create an Implementation Agent with tools registered"""
    register_all_tools()
    agent = ImplementationAgent()
    agent.start()
    yield agent
    agent.stop()


class TestImplementationAgentConfig:

    def test_agent_id(self, impl_agent):
        assert impl_agent.agent_id == "implementation_agent"

    def test_agent_name(self, impl_agent):
        assert impl_agent.config.name == "Implementation Agent"

    def test_agent_has_development_category(self, impl_agent):
        assert ToolCategory.DEVELOPMENT in impl_agent.config.tool_categories

    def test_agent_has_filesystem_category(self, impl_agent):
        assert ToolCategory.FILESYSTEM in impl_agent.config.tool_categories

    def test_agent_has_content_category(self, impl_agent):
        assert ToolCategory.CONTENT in impl_agent.config.tool_categories

    def test_agent_capabilities_cover_sections(self, impl_agent):
        caps = " ".join(impl_agent.config.capabilities).lower()
        assert "backend" in caps
        assert "frontend" in caps
        assert "database" in caps

    def test_agent_running(self, impl_agent):
        assert impl_agent.running is True

    def test_agent_has_implement_section_tool(self, impl_agent):
        tools = impl_agent._get_my_tools_list()
        assert "implement_section" in tools

    def test_agent_has_generate_code_tool(self, impl_agent):
        tools = impl_agent._get_my_tools_list()
        assert "generate_code" in tools

    def test_agent_has_generate_text_tool(self, impl_agent):
        """Implementation agent has CONTENT category so it should have generate_text"""
        tools = impl_agent._get_my_tools_list()
        assert "generate_text" in tools

    def test_agent_status(self, impl_agent):
        status = impl_agent.get_status()
        assert status["name"] == "Implementation Agent"
        assert status["running"] is True
        assert len(status["tools"]) > 0


class TestImplementationAgentTaskHandling:

    def test_handle_task_implement_backend_python(self, impl_agent, temp_dir):
        task = {
            "tool": "implement_section",
            "args": {
                "section": "backend",
                "tech": "python",
                "project_name": "TestApp",
                "directory": temp_dir
            }
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is True
        assert result["section"] == "backend"
        assert result["tech"] == "python"
        assert os.path.isdir(os.path.join(temp_dir, "backend"))
        assert os.path.isfile(os.path.join(temp_dir, "backend", "app.py"))

    def test_handle_task_implement_frontend_react(self, impl_agent, temp_dir):
        task = {
            "tool": "implement_section",
            "args": {
                "section": "frontend",
                "tech": "react",
                "project_name": "TestApp",
                "directory": temp_dir
            }
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "frontend", "src", "App.js"))

    def test_handle_task_implement_database(self, impl_agent, temp_dir):
        task = {
            "tool": "implement_section",
            "args": {
                "section": "database",
                "tech": "sql",
                "project_name": "TestApp",
                "directory": temp_dir
            }
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "database", "schema.sql"))

    def test_handle_task_implement_testing(self, impl_agent, temp_dir):
        task = {
            "tool": "implement_section",
            "args": {
                "section": "testing",
                "tech": "python",
                "project_name": "TestApp",
                "directory": temp_dir
            }
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "testing", "tests", "test_example.py"))

    def test_handle_task_implement_api(self, impl_agent, temp_dir):
        task = {
            "tool": "implement_section",
            "args": {
                "section": "api",
                "tech": "rest",
                "project_name": "TestApp",
                "directory": temp_dir
            }
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is True
        assert os.path.isdir(os.path.join(temp_dir, "api", "routes"))
        assert os.path.isdir(os.path.join(temp_dir, "api", "middleware"))

    def test_handle_task_invalid_section(self, impl_agent, temp_dir):
        task = {
            "tool": "implement_section",
            "args": {
                "section": "mobile",
                "tech": "swift",
                "project_name": "TestApp",
                "directory": temp_dir
            }
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is False

    def test_handle_task_invalid_tech(self, impl_agent, temp_dir):
        task = {
            "tool": "implement_section",
            "args": {
                "section": "backend",
                "tech": "rust",
                "project_name": "TestApp",
                "directory": temp_dir
            }
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is False

    def test_handle_task_unknown_tool(self, impl_agent):
        task = {
            "tool": "nonexistent_tool",
            "args": {}
        }
        result = impl_agent.handle_task(task)
        assert result["success"] is False


class TestImplementationAgentMessaging:

    def test_handle_task_request_message(self, impl_agent, temp_dir):
        from core.a2a_bus import Message, MessageType

        msg = Message.create(
            sender="orchestrator_agent",
            recipient="implementation_agent",
            msg_type=MessageType.TASK_REQUEST,
            payload={
                "tool": "implement_section",
                "args": {
                    "section": "backend",
                    "tech": "node",
                    "project_name": "MsgApp",
                    "directory": temp_dir
                }
            }
        )
        result = impl_agent.handle_message(msg)
        assert result is not None
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "backend", "index.js"))

    def test_handle_tool_request_message(self, impl_agent):
        from core.a2a_bus import Message, MessageType

        msg = Message.create(
            sender="orchestrator_agent",
            recipient="implementation_agent",
            msg_type=MessageType.TOOL_REQUEST,
            payload={
                "tool": "list_templates",
                "args": {}
            }
        )
        result = impl_agent.handle_message(msg)
        assert result is not None
        assert result["success"] is True

    def test_handle_irrelevant_message(self, impl_agent):
        from core.a2a_bus import Message, MessageType

        msg = Message.create(
            sender="test",
            recipient="implementation_agent",
            msg_type=MessageType.INFO_REQUEST,
            payload={}
        )
        result = impl_agent.handle_message(msg)
        assert result is None
