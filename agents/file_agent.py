"""
File Agent
Handles all file system operations
"""
import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class FileAgent(BaseAgent):
    """
    File Agent
    
    Responsibilities:
    - Execute file system operations
    - Read, write, copy, move, delete files
    - Manage directories
    - Search for files
    """
    
    def __init__(self):
        config = AgentConfig(
            name="File Agent",
            description="I handle all file system operations. I can read, write, copy, move, delete files and manage directories.",
            capabilities=[
                "Read file contents",
                "Write content to files",
                "Create and delete folders",
                "Copy and move files",
                "List directory contents",
                "Search for files"
            ],
            tool_categories=[ToolCategory.FILESYSTEM, ToolCategory.DATA]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """
        Handle a file operation task
        Uses LLM to decide how to accomplish the task if not explicit
        """
        tool = task.get("tool")
        args = task.get("args", {})
        
        if tool:
            # Validate required args for write_file
            if tool == "write_file" and "content" not in args:
                return {
                    "success": False,
                    "error": f"write_file requires 'content' argument. Got: {list(args.keys())}"
                }
            
            # Direct tool execution
            result = self.use_tool(tool, args)
            
            # Make sure we propagate the error properly
            if isinstance(result, dict):
                return {
                    "success": result.get("success", False),
                    "tool": tool,
                    "error": result.get("error"),
                    **{k: v for k, v in result.items() if k not in ["success", "error"]}
                }
            return {"success": False, "error": "Invalid result from tool", "result": result}
        
        # Need to decide what to do
        decision = self.decide_action(task)
        
        if decision.get("action") == "use_tool":
            result = self.use_tool(
                decision.get("tool_name"),
                decision.get("tool_args", {})
            )
            return {
                "success": result.get("success", False),
                "reasoning": decision.get("reasoning"),
                "tool": decision.get("tool_name"),
                "error": result.get("error"),
                **{k: v for k, v in result.items() if k not in ["success", "error"]}
            }
        
        return {
            "success": False,
            "error": "Could not determine appropriate action",
            "decision": decision
        }
    
    def handle_message(self, message: Message) -> Optional[Dict]:
        """Handle incoming messages"""
        if message.msg_type == MessageType.TASK_REQUEST:
            result = self.handle_task(message.payload)
            
            # Send result back
            self.send_message(
                message.sender,
                MessageType.TASK_RESULT,
                result,
                message.id
            )
            return result
        
        elif message.msg_type == MessageType.TOOL_REQUEST:
            # Direct tool request
            tool = message.payload.get("tool")
            args = message.payload.get("args", {})
            result = self.use_tool(tool, args)
            
            self.send_message(
                message.sender,
                MessageType.TOOL_RESULT,
                result,
                message.id
            )
            return result
        
        return None
