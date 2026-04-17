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
    # Phase 1 - State awareness: read-only observations of system state
    # (active window, processes, file/process existence checks)
    STATE = "state"
    # Phase 2 - Perception: read-only observations of visual state
    # (screenshots; future: OCR, element detection, vision-LLM queries)
    PERCEPTION = "perception"


@dataclass
class ToolDefinition:
    """Definition of a tool"""
    name: str
    description: str
    category: ToolCategory
    handler: Callable
    required_args: List[str]
    optional_args: List[str] = None
    # Phase 0 - Safety: when True, the MCP server will consult the permission
    # gate before executing this tool. Tools that modify filesystem state,
    # drive the mouse/keyboard, or run arbitrary commands should set this.
    requires_confirmation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "required": self.required_args,
            "optional": self.optional_args or [],
            "requires_confirmation": self.requires_confirmation
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
        # Phase 0 - Safety: callback the CLI registers to prompt the user
        # when a sensitive tool is about to execute. Signature:
        #   callback(tool_name: str, args: Dict) -> bool   # True = approved
        # If unset, sensitive tools fail safely (deny).
        self._confirmation_callback: Optional[Callable] = None
        self._initialized = True
    
    def set_confirmation_callback(self, callback: Callable):
        """Register a callback to be invoked when a sensitive tool needs confirmation."""
        self._confirmation_callback = callback
    
    def _check_permission(self, tool_name: str, tool: ToolDefinition) -> str:
        """
        Consult the permission policy.
        
        Returns one of: 'allow', 'block', 'confirm'.
        
        Order of precedence:
          1. SENSITIVE_TOOLS_BLOCK list wins over everything.
          2. SENSITIVE_TOOLS_ALLOW list bypasses confirmation.
          3. UNATTENDED_MODE bypasses confirmation (use with care).
          4. requires_confirmation flag on the tool -> 'confirm'.
          5. Otherwise -> 'allow'.
        """
        # Late import to avoid circular dependency at module load time.
        try:
            import config
            block_list = getattr(config, 'SENSITIVE_TOOLS_BLOCK', [])
            allow_list = getattr(config, 'SENSITIVE_TOOLS_ALLOW', [])
            unattended = getattr(config, 'UNATTENDED_MODE', False)
        except Exception:
            block_list, allow_list, unattended = [], [], False
        
        if tool_name in block_list:
            return 'block'
        if tool_name in allow_list:
            return 'allow'
        if unattended:
            return 'allow'
        if tool.requires_confirmation:
            return 'confirm'
        return 'allow'
    
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
        
        # Phase 0 - Safety: permission gate for sensitive tools.
        permission = self._check_permission(name, tool)
        if permission == 'block':
            return {
                "success": False,
                "error": f"Tool '{name}' is blocked by permissions policy",
                "blocked": True
            }
        if permission == 'confirm':
            if self._confirmation_callback is None:
                # No way to ask the user -> fail safely.
                return {
                    "success": False,
                    "error": (
                        f"Tool '{name}' requires confirmation but no "
                        "confirmation handler is configured. Either enable "
                        "UNATTENDED_MODE, add the tool to SENSITIVE_TOOLS_ALLOW, "
                        "or run through the interactive CLI."
                    ),
                    "requires_confirmation": True
                }
            try:
                approved = bool(self._confirmation_callback(name, args))
            except Exception as e:
                return {"success": False, "error": f"Confirmation handler failed: {e}"}
            if not approved:
                return {
                    "success": False,
                    "error": f"User denied permission to run '{name}'",
                    "denied": True
                }
        
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
