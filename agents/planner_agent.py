"""
Planner Agent
Creates execution plans (DAGs) from structured requests
"""
import os
import json
from typing import Dict, Any, Optional, List

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType, get_bus
from mcp.server import ToolCategory, get_mcp_server


class PlannerAgent(BaseAgent):
    """
    Planner Agent
    
    Responsibilities:
    - Receive structured requests
    - Decompose into tasks
    - Create execution DAG
    - Assign tasks to appropriate agents
    - Handle dependencies between tasks
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Planner Agent",
            description="I create execution plans. I decompose complex requests into tasks and assign them to specialized agents.",
            capabilities=[
                "Decompose requests into tasks",
                "Create task dependency graphs (DAG)",
                "Assign tasks to appropriate agents",
                "Optimize execution order"
            ],
            tool_categories=[]  # Planner doesn't execute tools directly
        )
        super().__init__(config)
        
        # Get system paths for context
        self.home_dir = os.path.expanduser("~")
        self.desktop = os.path.join(self.home_dir, "Desktop")
        self.documents = os.path.join(self.home_dir, "Documents")
    
    def create_plan(self, request: Dict) -> Dict[str, Any]:
        """
        Create an execution plan from a structured request
        Returns a DAG of tasks with agent assignments
        """
        # Get available tools from MCP
        mcp = get_mcp_server()
        tools_desc = mcp.get_tools_for_prompt()
        
        prompt = f"""Create an execution plan for this request.

SYSTEM PATHS:
- Home: {self.home_dir}
- Desktop: {self.desktop}  
- Documents: {self.documents}

AVAILABLE TOOLS (via specialized agents):
{tools_desc}

AGENT ASSIGNMENTS:
- file_agent: filesystem tools (read_file, write_file, list_directory, etc.)
- content_agent: content tools (generate_text, summarize_text)
- web_agent: web tools (fetch_webpage, download_file)
- system_agent: system tools (run_command, get_system_info, calculate, get_datetime)

REQUEST:
{json.dumps(request, indent=2)}

IMPORTANT RULES:
1. Use ACTUAL paths from SYSTEM PATHS above
2. Keep it SIMPLE - only include tasks the user explicitly asked for
3. Do NOT add extra tasks the user didn't request (e.g., don't save results to file unless asked)
4. If a task needs output from a previous task, use {{TASK_ID.content}} in the args
5. For write_file: MUST include both "filepath" and "content" args

Create a plan as JSON:
{{
    "plan_id": "unique_id",
    "description": "what this plan accomplishes",
    "tasks": [
        {{
            "task_id": "T1",
            "agent": "which agent handles this",
            "tool": "tool_name",
            "args": {{"arg1": "value1"}},
            "description": "what this task does",
            "depends_on": []
        }}
    ]
}}

JSON ONLY:"""

        response = self.think(prompt, {"request": request})
        
        try:
            import re
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                plan = json.loads(match.group())
                plan["status"] = "created"
                return {"success": True, "plan": plan}
        except Exception as e:
            pass
        
        return {"success": False, "error": "Failed to create plan", "raw_response": response}
    
    def validate_plan(self, plan: Dict) -> Dict[str, Any]:
        """Validate a plan before execution"""
        errors = []
        warnings = []
        
        tasks = plan.get("tasks", [])
        task_ids = {t.get("task_id") for t in tasks}
        
        for task in tasks:
            # Check required fields
            if not task.get("task_id"):
                errors.append("Task missing task_id")
            if not task.get("agent"):
                errors.append(f"Task {task.get('task_id')} missing agent")
            if not task.get("tool"):
                errors.append(f"Task {task.get('task_id')} missing tool")
            
            # Check dependencies exist
            for dep in task.get("depends_on", []):
                if dep not in task_ids:
                    errors.append(f"Task {task.get('task_id')} depends on non-existent task {dep}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a planning request"""
        if "request" in task:
            result = self.create_plan(task["request"])
            if result.get("success"):
                validation = self.validate_plan(result["plan"])
                result["validation"] = validation
            return result
        return {"success": False, "error": "No request provided"}
    
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
        
        return None
