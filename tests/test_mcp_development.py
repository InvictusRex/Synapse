"""
Tests for MCP server DEVELOPMENT tool category integration
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from mcp.server import MCPServer, ToolCategory, get_mcp_server
from tools.all_tools import register_all_tools


@pytest.fixture
def mcp():
    """Get MCP server with all tools registered"""
    register_all_tools()
    return get_mcp_server()


class TestDevelopmentCategory:

    def test_development_category_exists(self):
        assert ToolCategory.DEVELOPMENT.value == "development"

    def test_development_tools_registered(self, mcp):
        dev_tools = mcp.get_tools_by_category(ToolCategory.DEVELOPMENT)
        assert "generate_template" in dev_tools
        assert "list_templates" in dev_tools
        assert "scaffold_project" in dev_tools
        assert "implement_section" in dev_tools
        assert "generate_code" in dev_tools

    def test_development_tool_count(self, mcp):
        dev_tools = mcp.get_tools_by_category(ToolCategory.DEVELOPMENT)
        assert len(dev_tools) == 5

    def test_total_tool_count(self, mcp):
        assert len(mcp.tools) == 28


class TestMCPToolsListDevelopment:

    def test_tools_list_development_filter(self, mcp):
        tools = mcp.tools_list(ToolCategory.DEVELOPMENT)
        assert len(tools) == 5
        names = [t["name"] for t in tools]
        assert "generate_template" in names
        assert "scaffold_project" in names

    def test_tools_list_all_includes_development(self, mcp):
        all_tools = mcp.tools_list()
        names = [t["name"] for t in all_tools]
        assert "generate_template" in names
        assert "scaffold_project" in names
        assert "implement_section" in names

    def test_tool_schema_structure(self, mcp):
        tools = mcp.tools_list(ToolCategory.DEVELOPMENT)
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "category" in tool
            assert tool["category"] == "development"
            assert "parameters" in tool
            assert "required" in tool


class TestMCPToolsCallDevelopment:

    def test_call_generate_template(self, mcp):
        result = mcp.tools_call("generate_template", {
            "template_type": "python:class",
            "name": "TestService"
        })
        assert result["success"] is True
        assert "class TestService" in result["code"]

    def test_call_list_templates(self, mcp):
        result = mcp.tools_call("list_templates", {})
        assert result["success"] is True
        assert "code_templates" in result
        assert "project_templates" in result
        assert "section_templates" in result

    def test_call_scaffold_project(self, mcp, temp_dir):
        result = mcp.tools_call("scaffold_project", {
            "project_name": "MCPTest",
            "template": "python",
            "directory": temp_dir
        })
        assert result["success"] is True
        assert os.path.isdir(os.path.join(temp_dir, "MCPTest"))

    def test_call_implement_section(self, mcp, temp_dir):
        result = mcp.tools_call("implement_section", {
            "section": "backend",
            "tech": "python",
            "project_name": "MCPTest",
            "directory": temp_dir
        })
        assert result["success"] is True
        assert os.path.isdir(os.path.join(temp_dir, "backend"))

    def test_call_generate_template_missing_required(self, mcp):
        result = mcp.tools_call("generate_template", {
            "description": "something"
        })
        assert result["success"] is False
        assert "Missing required" in result["error"]

    def test_call_scaffold_project_missing_required(self, mcp):
        result = mcp.tools_call("scaffold_project", {
            "directory": "."
        })
        assert result["success"] is False
        assert "Missing required" in result["error"]

    def test_call_implement_section_missing_required(self, mcp):
        result = mcp.tools_call("implement_section", {
            "section": "backend"
        })
        assert result["success"] is False
        assert "Missing required" in result["error"]


class TestMCPToolsDescribeDevelopment:

    def test_describe_generate_template(self, mcp):
        desc = mcp.tools_describe("generate_template")
        assert desc is not None
        assert desc["name"] == "generate_template"
        assert desc["category"] == "development"
        assert "template_type" in desc["required"]
        assert "name" in desc["required"]

    def test_describe_scaffold_project(self, mcp):
        desc = mcp.tools_describe("scaffold_project")
        assert desc is not None
        assert "project_name" in desc["required"]
        assert "template" in desc["required"]

    def test_describe_implement_section(self, mcp):
        desc = mcp.tools_describe("implement_section")
        assert desc is not None
        assert "section" in desc["required"]
        assert "tech" in desc["required"]
        assert "project_name" in desc["required"]

    def test_describe_generate_code(self, mcp):
        desc = mcp.tools_describe("generate_code")
        assert desc is not None
        assert "prompt" in desc["required"]

    def test_describe_list_templates(self, mcp):
        desc = mcp.tools_describe("list_templates")
        assert desc is not None
        assert desc["required"] == []


class TestMCPExecutionStats:

    def test_stats_after_dev_tool_calls(self, mcp):
        mcp.tools_call("list_templates", {})
        mcp.tools_call("generate_template", {
            "template_type": "python:function",
            "name": "test"
        })

        stats = mcp.get_execution_stats()
        assert stats["total_executions"] >= 2
        assert stats["successful"] >= 2

    def test_stats_count_failed_calls(self, mcp):
        mcp.tools_call("generate_template", {"description": "missing required"})

        stats = mcp.get_execution_stats()
        assert stats["failed"] >= 1


class TestMCPGetToolsForPrompt:

    def test_prompt_includes_development_tools(self, mcp):
        prompt_text = mcp.get_tools_for_prompt()
        assert "DEVELOPMENT TOOLS:" in prompt_text
        assert "generate_template" in prompt_text
        assert "scaffold_project" in prompt_text
        assert "implement_section" in prompt_text
        assert "generate_code" in prompt_text
        assert "list_templates" in prompt_text
