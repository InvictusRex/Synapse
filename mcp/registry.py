"""
MCP Tool Registry
Manages tool schemas and registration
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSchema:
    """MCP-style tool schema"""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    
    def to_dict(self) -> Dict:
        """Convert to MCP-compatible format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    def validate_args(self, args: Dict) -> bool:
        """Validate arguments against schema"""
        required = self.parameters.get("required", [])
        for req in required:
            if req not in args:
                return False
        return True


class ToolRegistry:
    """
    Central registry for all MCP tools
    """
    
    def __init__(self):
        self.tools: Dict[str, ToolSchema] = {}
    
    def register(self, 
                 name: str, 
                 description: str, 
                 parameters: Dict[str, Any],
                 handler: Callable):
        """Register a new tool"""
        schema = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )
        self.tools[name] = schema
        print(f"[MCP] Tool registered: {name}")
    
    def get_tool(self, name: str) -> Optional[ToolSchema]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict]:
        """List all available tools (MCP tools/list style)"""
        return [tool.to_dict() for tool in self.tools.values()]
    
    def get_tools_prompt(self) -> str:
        """Generate a prompt-friendly description of all tools"""
        lines = ["Available tools:"]
        for tool in self.tools.values():
            params = tool.parameters.get("properties", {})
            param_str = ", ".join(params.keys())
            lines.append(f"- {tool.name}({param_str}): {tool.description}")
        return "\n".join(lines)


# Global registry instance
_registry_instance = None

def get_registry() -> ToolRegistry:
    """Get the global tool registry"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance
