"""
Interaction Agent
Handles user input, clarifies intent, structures requests
"""
import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class InteractionAgent(BaseAgent):
    """
    Interaction Agent
    
    Responsibilities:
    - Receive and parse user input
    - Clarify ambiguous requests
    - Structure requests for the Planner
    - Return final results to user
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Interaction Agent",
            description="I handle user communication. I parse requests, clarify intent, and deliver results.",
            capabilities=[
                "Parse natural language requests",
                "Identify user intent",
                "Structure requests for planning",
                "Format and present results"
            ],
            tool_categories=[]  # No direct tool access - works through other agents
        )
        super().__init__(config)
    
    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process raw user input and structure it
        """
        prompt = f"""Parse this user request and extract structured information.

USER INPUT: {user_input}

Respond with ONLY this JSON structure:
{{
    "intent": "what the user wants to accomplish",
    "entities": {{
        "files": ["any files mentioned"],
        "paths": ["any paths mentioned"],
        "urls": ["any URLs mentioned"],
        "topics": ["any topics/subjects mentioned"]
    }},
    "task_type": "file_operation|content_generation|web_task|system_task|data_task|mixed",
    "complexity": "simple|moderate|complex",
    "structured_request": "clear, actionable description of what needs to be done"
}}

JSON ONLY:"""

        response = self.think(prompt)
        
        try:
            import re
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                parsed = json.loads(match.group())
                parsed["original_input"] = user_input
                return {"success": True, "parsed": parsed}
        except:
            pass
        
        # Fallback - pass through
        return {
            "success": True,
            "parsed": {
                "intent": user_input,
                "task_type": "mixed",
                "complexity": "moderate",
                "structured_request": user_input,
                "original_input": user_input
            }
        }
    
    def format_result(self, result: Dict) -> str:
        """Format execution result for user"""
        prompt = f"""Format this result for the user in a clear, friendly way.

RESULT: {json.dumps(result, indent=2)}

Provide a clear summary. If there's content, show it. If there's an error, explain it helpfully.
Keep it concise but informative."""

        return self.think(prompt)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a task (parse user input)"""
        if "user_input" in task:
            return self.process_user_input(task["user_input"])
        return {"success": False, "error": "No user_input provided"}
    
    def handle_message(self, message: Message) -> Optional[Dict]:
        """Handle incoming messages"""
        if message.msg_type == MessageType.TASK_REQUEST:
            return self.handle_task(message.payload)
        elif message.msg_type == MessageType.TASK_RESULT:
            # Format result for user
            formatted = self.format_result(message.payload)
            return {"formatted_result": formatted, "raw_result": message.payload}
        return None
