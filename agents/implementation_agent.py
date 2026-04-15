"""
Implementation Agent
Handles complete sectional implementation (backend, frontend, database, API, testing)
"""
import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class ImplementationAgent(BaseAgent):
    """
    Implementation Agent

    Responsibilities:
    - Implement complete project sections (backend, frontend, database, API, testing)
    - Generate full directory structures with production-ready code
    - Support multiple tech stacks per section
    - Create interconnected code files (routes, models, services, components)
    """

    def __init__(self):
        config = AgentConfig(
            name="Implementation Agent",
            description="I implement complete project sections. I can generate full backend (Flask/Express), frontend (React/HTML), database (SQL), API (REST), and testing structures with production-ready code.",
            capabilities=[
                "Implement complete backend sections (Python Flask, Node.js Express)",
                "Implement complete frontend sections (React, HTML/CSS/JS)",
                "Implement database schemas and migrations (SQL)",
                "Implement REST API structures with routes and middleware",
                "Implement testing frameworks (Python unittest, JavaScript Jest)",
                "Generate AI-powered custom code implementations"
            ],
            tool_categories=[ToolCategory.DEVELOPMENT, ToolCategory.FILESYSTEM, ToolCategory.CONTENT]
        )
        super().__init__(config)

    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """
        Handle an implementation task
        Routes to the appropriate tool based on the task
        """
        tool = task.get("tool")
        args = task.get("args", {})

        if tool:
            # Direct tool execution
            result = self.use_tool(tool, args)

            if isinstance(result, dict):
                return {
                    "success": result.get("success", False),
                    "tool": tool,
                    "error": result.get("error"),
                    **{k: v for k, v in result.items() if k not in ["success", "error"]}
                }
            return {"success": False, "error": "Invalid result from tool", "result": result}

        # Autonomous decision
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

        if decision.get("response"):
            return {
                "success": True,
                "content": decision.get("response"),
                "reasoning": decision.get("reasoning")
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

        return None
