"""
MCP (Model Context Protocol) Server
Handles tool registration, discovery, and execution
"""
import json
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Categories of tools"""
    FILESYSTEM = "filesystem"
    CONTENT = "content"
    WEB = "web"
    SYSTEM = "system"
    DATA = "data"


@dataclass
class ToolSchema:
    """MCP Tool Schema"""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Any]  # JSON Schema format
    required_params: List[str]
    handler: Callable
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "required": self.required_params
        }
    
    def validate_args(self, args: Dict) -> tuple[bool, str]:
        """Validate arguments against schema"""
        for param in self.required_params:
            if param not in args:
                return False, f"Missing required parameter: {param}"
        return True, ""


class MCPServer:
    """
    MCP Server - Tool Abstraction Layer
    
    Responsibilities:
    - Tool registration and discovery
    - Schema validation
    - Tool execution routing
    - Standardized interface
    """
    
    def __init__(self):
        self.tools: Dict[str, ToolSchema] = {}
        self.execution_count = 0
        self.execution_log: List[Dict] = []
    
    # ==================== MCP Protocol Methods ====================
    
    def tools_list(self, category: ToolCategory = None) -> List[Dict]:
        """
        MCP: tools/list
        List all available tools, optionally filtered by category
        """
        tools = []
        for tool in self.tools.values():
            if category is None or tool.category == category:
                tools.append(tool.to_dict())
        return tools
    
    def tools_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP: tools/call
        Execute a tool with given arguments
        """
        self.execution_count += 1
        
        # Get tool
        tool = self.tools.get(tool_name)
        if not tool:
            result = {
                "success": False,
                "error": f"Tool not found: {tool_name}",
                "available_tools": list(self.tools.keys())
            }
            self._log_execution(tool_name, arguments, result)
            return result
        
        # Validate arguments
        valid, error = tool.validate_args(arguments)
        if not valid:
            result = {
                "success": False,
                "error": error,
                "tool": tool_name,
                "required_params": tool.required_params
            }
            self._log_execution(tool_name, arguments, result)
            return result
        
        # Execute
        try:
            result = tool.handler(**arguments)
            if not isinstance(result, dict):
                result = {"success": True, "result": result}
            self._log_execution(tool_name, arguments, result)
            return result
        except Exception as e:
            result = {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "tool": tool_name
            }
            self._log_execution(tool_name, arguments, result)
            return result
    
    def tools_describe(self, tool_name: str) -> Optional[Dict]:
        """
        MCP: tools/describe
        Get detailed information about a specific tool
        """
        tool = self.tools.get(tool_name)
        if tool:
            return tool.to_dict()
        return None
    
    # ==================== Registration Methods ====================
    
    def register_tool(self, 
                      name: str,
                      description: str,
                      category: ToolCategory,
                      parameters: Dict[str, Any],
                      required_params: List[str],
                      handler: Callable) -> bool:
        """Register a tool with the MCP server"""
        if name in self.tools:
            return False
        
        self.tools[name] = ToolSchema(
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            required_params=required_params,
            handler=handler
        )
        print(f"[MCP] Tool registered: {name} ({category.value})")
        return True
    
    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool"""
        if name in self.tools:
            del self.tools[name]
            return True
        return False
    
    # ==================== Helper Methods ====================
    
    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get tool names by category"""
        return [name for name, tool in self.tools.items() 
                if tool.category == category]
    
    def get_tools_for_prompt(self) -> str:
        """Get a prompt-friendly description of all tools"""
        lines = []
        for category in ToolCategory:
            tools = self.get_tools_by_category(category)
            if tools:
                lines.append(f"\n{category.value.upper()} TOOLS:")
                for name in tools:
                    tool = self.tools[name]
                    params = ", ".join(tool.required_params) if tool.required_params else "none"
                    lines.append(f"  - {name}({params}): {tool.description}")
        return "\n".join(lines)
    
    def _log_execution(self, tool: str, args: Dict, result: Dict):
        """Log tool execution"""
        self.execution_log.append({
            "tool": tool,
            "args": args,
            "success": result.get("success", False),
            "error": result.get("error")
        })
    
    def get_execution_stats(self) -> Dict:
        """Get execution statistics"""
        success_count = sum(1 for e in self.execution_log if e["success"])
        return {
            "total_executions": self.execution_count,
            "successful": success_count,
            "failed": self.execution_count - success_count,
            "tools_registered": len(self.tools)
        }


# Global MCP server instance
_mcp_instance = None

def get_mcp_server() -> MCPServer:
    """Get the global MCP server instance"""
    global _mcp_instance
    if _mcp_instance is None:
        _mcp_instance = MCPServer()
    return _mcp_instance
