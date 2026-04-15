"""
File Agent
Handles all filesystem operations
"""
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class FileAgent(BaseAgent):
    """
    File Agent
    
    Responsibilities:
    - Read/write files
    - Create/delete folders
    - Move/copy files
    - Search filesystem
    - Handle JSON/CSV data files
    """
    
    def __init__(self):
        config = AgentConfig(
            name="File Agent",
            description="I handle all filesystem operations. I can read, write, create, delete, move, and search files and folders.",
            capabilities=[
                "Read file contents",
                "Write content to files",
                "Create folders",
                "Delete files and folders",
                "Move and copy files",
                "Search for files",
                "Handle JSON and CSV data"
            ],
            tool_categories=[ToolCategory.FILESYSTEM, ToolCategory.DATA]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle file operation request"""
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
