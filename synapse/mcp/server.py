"""
MCP Server - Tool execution and routing
"""
from typing import Any, Dict, Optional
from .registry import get_registry, ToolSchema


class MCPServer:
    """
    MCP-style server for tool execution
    Handles tool invocation with schema validation
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.execution_count = 0
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool (MCP tools/call style)
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            {"success": bool, "result": Any, "error": str|None}
        """
        self.execution_count += 1
        
        # Get tool from registry
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "result": None,
                "error": f"Tool not found: {tool_name}"
            }
        
        # Validate arguments
        if not tool.validate_args(arguments):
            return {
                "success": False,
                "result": None,
                "error": f"Invalid arguments for {tool_name}"
            }
        
        # Execute tool
        try:
            print(f"[MCP] Executing: {tool_name}({arguments})")
            result = tool.handler(**arguments)
            return {
                "success": True,
                "result": result,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    def list_tools(self):
        """List all available tools"""
        return self.registry.list_tools()


# Global server instance
_server_instance = None

def get_mcp_server() -> MCPServer:
    """Get the global MCP server"""
    global _server_instance
    if _server_instance is None:
        _server_instance = MCPServer()
    return _server_instance
