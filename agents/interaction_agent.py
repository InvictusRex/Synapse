"""
Interaction Agent
Handles user input interpretation and response formatting
"""
import json
import re
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class InteractionAgent(BaseAgent):
    """
    Interaction Agent
    
    Responsibilities:
    - Interpret natural language input
    - Detect intent and extract entities
    - Format responses for users
    - Handle conversational flow
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Interaction Agent",
            description="I interpret user requests and format responses. I'm the interface between humans and the system.",
            capabilities=[
                "Natural language understanding",
                "Intent detection",
                "Entity extraction",
                "Response formatting",
                "Conversation management"
            ],
            tool_categories=[]
        )
        super().__init__(config)
    
    def interpret_input(self, user_input: str) -> Dict[str, Any]:
        """
        Interpret user input and extract structured information
        """
        prompt = f"""Analyze this user request and extract structured information.

USER INPUT: "{user_input}"

Respond with ONLY a JSON object:
{{
    "intent": "create_file|read_file|list_directory|search|generate_content|web_fetch|system_info|calculate|greeting|other",
    "entities": {{
        "paths": ["list of file/folder paths mentioned"],
        "filenames": ["list of filenames"],
        "urls": ["list of URLs"],
        "content_type": "poem|story|code|text|summary|etc if content generation",
        "topic": "main topic or subject"
    }},
    "requires_content_generation": true/false,
    "requires_file_operation": true/false,
    "requires_web_access": true/false,
    "requires_system_access": true/false,
    "original_input": "{user_input}"
}}

JSON ONLY:"""

        response = self.think(prompt)
        
        # Use the shared tolerant parser from planner_agent - same logic,
        # same trailing-comma handling, same balanced-brace fallback.
        try:
            from agents.planner_agent import _parse_plan_response
            parsed, _err, _raw = _parse_plan_response(response)
            if parsed is not None:
                parsed["original_input"] = user_input
                return {"success": True, "interpretation": parsed}
        except Exception:
            pass
        
        # Fallback: basic interpretation
        return {
            "success": True,
            "interpretation": {
                "intent": "other",
                "entities": {},
                "requires_content_generation": True,
                "requires_file_operation": False,
                "requires_web_access": False,
                "requires_system_access": False,
                "original_input": user_input
            }
        }
    
    def format_response(self, result: Dict, original_request: str = "") -> str:
        """Format execution result for user display"""
        if not result.get("success", False):
            error = result.get("error", "Unknown error occurred")
            return f"Failed: {error}"
        
        parts = []
        
        # Task summary
        completed = result.get("tasks_completed", 0)
        total = result.get("tasks_total", 0)
        
        if total > 0:
            parts.append(f"Completed {completed}/{total} tasks")
        
        # Content outputs
        outputs = result.get("all_outputs", [])
        for output in outputs:
            content = output.get("content")
            if content:
                if isinstance(content, dict):
                    # Handle dict content
                    if "content" in content:
                        parts.append(str(content["content"]))
                    elif "result" in content:
                        parts.append(str(content["result"]))
                    else:
                        parts.append(json.dumps(content, indent=2))
                else:
                    parts.append(str(content))
        
        # File operations
        task_states = result.get("task_states", {})
        for task_id, state in task_states.items():
            if state.get("status") == "completed":
                task_result = state.get("result", {})
                if task_result.get("filepath"):
                    parts.append(f"File: {task_result['filepath']}")
        
        return "\n".join(parts) if parts else "Task completed"
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle interpretation request"""
        if "input" in task:
            return self.interpret_input(task["input"])
        if "format" in task:
            formatted = self.format_response(task["format"], task.get("original", ""))
            return {"success": True, "formatted": formatted}
        return {"success": False, "error": "No input provided"}
    
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
