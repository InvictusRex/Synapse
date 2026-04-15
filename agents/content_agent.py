"""
Content Agent
Handles text generation and summarization
"""
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class ContentAgent(BaseAgent):
    """
    Content Agent
    
    Responsibilities:
    - Generate text content (poems, stories, code, etc.)
    - Summarize text
    - Transform content
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Content Agent",
            description="I generate and transform text content. I can write poems, stories, code, summaries, and more.",
            capabilities=[
                "Generate creative text",
                "Summarize documents",
                "Transform content formats",
                "Write various text types"
            ],
            tool_categories=[ToolCategory.CONTENT]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle content generation request"""
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
