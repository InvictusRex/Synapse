"""
System Agent
Handles system operations
"""
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class SystemAgent(BaseAgent):
    """
    System Agent
    
    Responsibilities:
    - Get system information
    - Run shell commands
    - Perform calculations
    - Get date/time
    """
    
    def __init__(self):
        config = AgentConfig(
            name="System Agent",
            description="I handle system operations. I can get system info, run commands, perform calculations, and more.",
            capabilities=[
                "Get system information",
                "Run shell commands",
                "Perform calculations",
                "Get current date/time",
                "Get working directory"
            ],
            tool_categories=[ToolCategory.SYSTEM]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle system operation request"""
        tool = task.get("tool")
        args = task.get("args", {})
        
        if not tool:
            return {"success": False, "error": "No tool specified"}
        
        return self.use_tool(tool, args)
    
    def handle_message(self, message: Message) -> Optional[Dict]:
        """Handle incoming messages"""
        if message.msg_type == MessageType.TASK_REQUEST:
            result = self.handle_task(message.payload)
            self.send_message(
                message.sender,
                MessageType.TASK_RESULT,
                result,
                message.id
            )
            return result
        return None
