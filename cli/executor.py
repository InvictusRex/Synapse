"""
CLI Executor - Bridges the CLI to the MCP server for tool execution.
Contains no tool logic — delegates entirely to MCPServer.call_tool().
"""
from typing import Any, Dict
from mcp.server import get_mcp_server


class ToolExecutor:
    """Thin wrapper that routes CLI calls to the MCP server."""

    def __init__(self):
        self._server = get_mcp_server()

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool through the MCP server.

        Returns:
            {"success": bool, "result": Any, "error": str|None}
        """
        return self._server.call_tool(tool_name, arguments)

    def list_tools(self):
        """Passthrough to MCP server's tool listing."""
        return self._server.list_tools()
