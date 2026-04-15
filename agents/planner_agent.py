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
        self.downloads = os.path.join(self.home_dir, "Downloads")
        self.working_dir = os.getcwd()  # Default, can be overridden
    
    def set_working_dir(self, working_dir: str):
        """Set the working directory for file operations"""
        self.working_dir = working_dir
    
    def create_plan(self, request: Dict) -> Dict[str, Any]:
        """
        Create an execution plan from a structured request
        Returns a DAG of tasks with agent assignments
        """
        # Get available tools from MCP
        mcp = get_mcp_server()
        
        # Extract key info from request
        original_input = request.get("original_input", "")
        intent = request.get("intent", "")
        
        prompt = f"""Create a JSON execution plan for this user request.

USER REQUEST: "{original_input}"

PATHS:
- DEFAULT (no path mentioned): {self.working_dir}
- Desktop: {self.desktop}
- Documents: {self.documents}
- Downloads: {self.downloads}

AGENTS AND TOOLS:
- file_agent: read_file, write_file, create_folder, list_directory, move_file, copy_file, delete_file, search_files
- content_agent: generate_text, summarize_text
- web_agent: fetch_webpage, download_file  
- system_agent: get_system_info, get_datetime, calculate, get_cwd, run_command

EXAMPLES:

Example 1: "get system info and save to info.txt"
{{
  "plan_id": "plan_001",
  "description": "Get system info and save to file",
  "tasks": [
    {{"task_id": "T1", "agent": "system_agent", "tool": "get_system_info", "args": {{}}, "description": "Get system information", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.working_dir}/info.txt", "content": "{{{{T1.result}}}}"}}, "description": "Save system info to file", "depends_on": ["T1"]}}
  ]
}}

Example 2: "write a poem about stars and save as stars.txt"
{{
  "plan_id": "plan_002", 
  "description": "Generate poem and save to file",
  "tasks": [
    {{"task_id": "T1", "agent": "content_agent", "tool": "generate_text", "args": {{"prompt": "Write a short poem about stars"}}, "description": "Generate poem about stars", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.working_dir}/stars.txt", "content": "{{{{T1.content}}}}"}}, "description": "Save poem to file", "depends_on": ["T1"]}}
  ]
}}

Example 3: "create folder called Projects on Desktop"
{{
  "plan_id": "plan_003",
  "description": "Create Projects folder on Desktop",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "create_folder", "args": {{"folder_path": "{self.desktop}/Projects"}}, "description": "Create Projects folder on Desktop", "depends_on": []}}
  ]
}}

Example 4: "what time is it"
{{
  "plan_id": "plan_004",
  "description": "Get current date and time",
  "tasks": [
    {{"task_id": "T1", "agent": "system_agent", "tool": "get_datetime", "args": {{}}, "description": "Get current date and time", "depends_on": []}}
  ]
}}

Example 5: "list files in Documents"
{{
  "plan_id": "plan_005",
  "description": "List files in Documents folder",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "list_directory", "args": {{"directory": "{self.documents}"}}, "description": "List contents of Documents", "depends_on": []}}
  ]
}}

RULES:
1. If NO path mentioned, use: {self.working_dir}
2. If "Desktop" mentioned, use: {self.desktop}
3. If "Documents" mentioned, use: {self.documents}
4. For chained tasks, use {{{{T1.content}}}} or {{{{T1.result}}}} to reference previous output
5. Create folder BEFORE writing file inside it
6. For greetings like "hello", use content_agent generate_text

Now create a plan for: "{original_input}"

Respond with ONLY valid JSON, no other text:"""

        response = self.think(prompt, {"request": request})
        
        try:
            import re
            # Try to find JSON in response
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                plan = json.loads(match.group())
                plan["status"] = "created"
                return {"success": True, "plan": plan}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}", "raw_response": response}
        except Exception as e:
            return {"success": False, "error": str(e), "raw_response": response}
        
        return {"success": False, "error": "Failed to create plan - no valid JSON found", "raw_response": response}
    
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
