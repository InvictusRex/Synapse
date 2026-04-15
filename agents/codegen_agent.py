"""
CodeGen Agent
Handles template-based code generation and AI-powered code creation
"""
import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class CodeGenAgent(BaseAgent):
    """
    CodeGen Agent

    Responsibilities:
    - Generate code from predefined templates
    - Generate code using AI from natural language descriptions
    - List available templates
    - Produce boilerplate code for various languages and frameworks
    """

    def __init__(self):
        config = AgentConfig(
            name="CodeGen Agent",
            description="I generate code from templates and AI prompts. I can create classes, functions, components, API routes, and more for Python, JavaScript, and HTML.",
            capabilities=[
                "Generate code from templates (classes, functions, tests, routes)",
                "Generate code using AI from natural language descriptions",
                "List available code templates",
                "Support Python, JavaScript, and HTML templates",
                "Create framework-specific code (Flask, FastAPI, Express, React)"
            ],
            tool_categories=[ToolCategory.DEVELOPMENT, ToolCategory.FILESYSTEM]
        )
        super().__init__(config)

    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """
        Handle a code generation task
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
