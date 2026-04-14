"""
System Agent  
Handles system operations - commands, info, calculations
"""
import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class SystemAgent(BaseAgent):
    """
    System Agent
    
    Responsibilities:
    - Run shell commands
    - Get system information
    - Perform calculations
    - Get date/time
    """
    
    def __init__(self):
        config = AgentConfig(
            name="System Agent",
            description="I handle system operations. I can run commands, get system info, perform calculations, and check date/time.",
            capabilities=[
                "Run shell/terminal commands",
                "Get system information",
                "Perform mathematical calculations",
                "Get current date and time"
            ],
            tool_categories=[ToolCategory.SYSTEM]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a system task"""
        tool = task.get("tool")
        args = task.get("args", {})
        
        if tool:
            # Safety check for commands
            if tool == "run_command":
                command = args.get("command", "")
                # Basic safety - could be expanded
                dangerous = ["rm -rf /", "format", "del /f /s /q"]
                if any(d in command.lower() for d in dangerous):
                    return {
                        "success": False,
                        "error": "Command blocked for safety reasons"
                    }
            
            result = self.use_tool(tool, args)
            return {
                "success": result.get("success", False),
                "tool": tool,
                "result": result
            }
        
        # Autonomous decision
        decision = self.decide_action(task)
        
        if decision.get("action") == "use_tool":
            return self.use_tool(
                decision.get("tool_name"),
                decision.get("tool_args", {})
            )
        
        if decision.get("response"):
            return {
                "success": True,
                "response": decision.get("response")
            }
        
        return {"success": False, "error": "Could not handle task", "decision": decision}
    
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
        
        elif message.msg_type == MessageType.TOOL_REQUEST:
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
        
        elif message.msg_type == MessageType.INFO_REQUEST:
            # Request for system info
            info_type = message.payload.get("type")
            
            if info_type == "system":
                result = self.use_tool("get_system_info", {})
            elif info_type == "datetime":
                result = self.use_tool("get_datetime", {})
            else:
                result = {"success": False, "error": f"Unknown info type: {info_type}"}
            
            self.send_message(
                message.sender,
                MessageType.INFO_RESPONSE,
                result,
                message.id
            )
            return result
        
        return None
