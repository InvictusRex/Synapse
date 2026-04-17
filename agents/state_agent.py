"""
State Agent (Phase 1)

Owns the STATE tool category: read-only observations of system state
(active window, open windows, running processes, file/process existence).

This agent is deliberately minimal - it just relays tool requests. The
real "intelligence" happens in the planner, which now has state tools
available when building DAGs (e.g. "check Chrome is running before
trying to focus it").
"""
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class StateAgent(BaseAgent):
    """Handles state-awareness tool requests."""
    
    def __init__(self):
        config = AgentConfig(
            name="State Agent",
            description=(
                "I observe the system state. I can see what windows are "
                "open, which process is in focus, what processes are "
                "running, and whether specific files or processes exist. "
                "I never modify anything."
            ),
            capabilities=[
                "Detect active/focused window",
                "List open windows",
                "Enumerate running processes",
                "Check if a process is running",
                "Check if a file or folder exists"
            ],
            tool_categories=[ToolCategory.STATE]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Execute a tool-invocation task."""
        tool_name = task.get("tool")
        args = task.get("args", {})
        if not tool_name:
            return {"success": False, "error": "No tool specified"}
        return self.use_tool(tool_name, args)
    
    def handle_message(self, message: Message) -> Optional[Dict]:
        """Reply to A2A TASK_REQUEST messages."""
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
