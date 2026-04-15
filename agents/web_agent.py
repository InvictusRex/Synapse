"""
Web Agent
Handles web operations
"""
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class WebAgent(BaseAgent):
    """
    Web Agent
    
    Responsibilities:
    - Fetch web pages
    - Download files
    - Extract content from URLs
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Web Agent",
            description="I handle web operations. I can fetch web pages, download files, and extract content from URLs.",
            capabilities=[
                "Fetch web page content",
                "Download files from URLs",
                "Extract text from websites"
            ],
            tool_categories=[ToolCategory.WEB]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle web operation request"""
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
