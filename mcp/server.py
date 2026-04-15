"""
MCP (Model Context Protocol) Server
Tool registry and execution
"""
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ToolCategory(Enum):
    """Tool categories for agent filtering"""
    FILESYSTEM = "filesystem"
    CONTENT = "content"
    WEB = "web"
    SYSTEM = "system"
    DATA = "data"
    MEMORY = "memory"


@dataclass
class ToolDefinition:
    """Definition of a tool"""
    name: str
    description: str
    category: ToolCategory
    handler: Callable
    required_args: List[str]
    optional_args: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "required": self.required_args,
            "optional": self.optional_args or []
        }


class MCPServer:
    """
    MCP (Model Context Protocol) Server
    
    Manages tool registration, discovery, and execution.
    Provides a unified interface for all agent tools.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tools: Dict[str, ToolDefinition] = {}
        self._execution_count = 0
        self._execution_log: List[Dict] = []
        self._lock = threading.Lock()
        self._initialized = True
    
    def register_tool(self, tool: ToolDefinition):
        """Register a tool"""
        with self._lock:
            self._tools[tool.name] = tool
    
    def register_tools(self, tools: List[ToolDefinition]):
        """Register multiple tools"""
        for tool in tools:
            self.register_tool(tool)
    
    def unregister_tool(self, name: str):
        """Unregister a tool"""
        with self._lock:
            if name in self._tools:
                del self._tools[name]
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def tools_list(self, category: ToolCategory = None) -> List[Dict]:
        """List all tools, optionally filtered by category"""
        tools = []
        for tool in self._tools.values():
            if category is None or tool.category == category:
                tools.append(tool.to_dict())
        return tools
    
    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """Get tool names by category"""
        return [name for name, tool in self._tools.items() 
                if tool.category == category]
    
    def tools_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool"""
        tool = self._tools.get(name)
        
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found"}
        
        # Validate required args
        for arg in tool.required_args:
            if arg not in args:
                return {"success": False, "error": f"Missing required argument: {arg}"}
        
        try:
            self._execution_count += 1
            result = tool.handler(**args)
            
            # Log execution
            self._execution_log.append({
                "tool": name,
                "args": args,
                "success": result.get("success", True),
                "execution_id": self._execution_count
            })
            
            # Keep log limited
            if len(self._execution_log) > 100:
                self._execution_log = self._execution_log[-50:]
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_tools_for_prompt(self) -> str:
        """Get tool descriptions formatted for LLM prompt"""
        lines = []
        
        # Group by category
        by_category: Dict[ToolCategory, List[ToolDefinition]] = {}
        for tool in self._tools.values():
            if tool.category not in by_category:
                by_category[tool.category] = []
            by_category[tool.category].append(tool)
        
        for category, tools in by_category.items():
            lines.append(f"\n{category.value.upper()} TOOLS:")
            for tool in tools:
                args = ", ".join(tool.required_args)
                lines.append(f"  - {tool.name}({args}): {tool.description}")
        
        return "\n".join(lines)
    
    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        return {
            "tools_registered": len(self._tools),
            "total_executions": self._execution_count,
            "categories": list(set(t.category.value for t in self._tools.values()))
        }
    
    def get_execution_log(self, limit: int = 50) -> List[Dict]:
        """Get recent execution log"""
        return self._execution_log[-limit:]


# Global MCP server instance
_mcp_server: Optional[MCPServer] = None

def get_mcp_server() -> MCPServer:
    """Get or create the global MCP server"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server

def register_tool(name: str, description: str, category: ToolCategory,
                  handler: Callable, required_args: List[str],
                  optional_args: List[str] = None):
    """Helper to register a tool"""
    server = get_mcp_server()
    tool = ToolDefinition(
        name=name,
        description=description,
        category=category,
        handler=handler,
        required_args=required_args,
        optional_args=optional_args
    )
    server.register_tool(tool)
