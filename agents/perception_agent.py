"""
Perception Agent (Phase 2)

Owns the PERCEPTION tool category. Currently minimal - just screenshot
capture - but this is the agent that will grow substantially in Phase 7
when CV enters the picture (OCR, element detection, vision-LLM queries).

Keeping it as a separate agent from StateAgent even though both are
observational because:
  - PERCEPTION tools talk to display/GUI subsystems (fragile on servers)
  - STATE tools talk to OS process/window APIs (work almost everywhere)
  - In Phase 7 the planner will want to distinguish "does the file exist"
    (cheap, reliable) from "does the button I need show up on screen"
    (expensive, requires a running display).
"""
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class PerceptionAgent(BaseAgent):
    """Handles visual/screen observation tool requests."""
    
    def __init__(self):
        config = AgentConfig(
            name="Perception Agent",
            description=(
                "I observe the visual state of the screen. I can capture "
                "screenshots of what the user currently sees. In the "
                "future I will also read text from the screen and find "
                "UI elements. I never modify anything visually - I only "
                "observe."
            ),
            capabilities=[
                "Capture screenshots to disk"
            ],
            tool_categories=[ToolCategory.PERCEPTION]
        )
        super().__init__(config)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        tool_name = task.get("tool")
        args = task.get("args", {})
        if not tool_name:
            return {"success": False, "error": "No tool specified"}
        return self.use_tool(tool_name, args)
    
    def handle_message(self, message: Message) -> Optional[Dict]:
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
