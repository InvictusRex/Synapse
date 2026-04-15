"""
Planner Agent
Creates execution plans (DAGs) from structured requests
"""
import os
import json
import re
from typing import Dict, Any, Optional, List

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from core.dag import DAG, DAGTask
from mcp.server import ToolCategory


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
                "Optimize execution order",
                "Identify parallelizable tasks"
            ],
            tool_categories=[]
        )
        super().__init__(config)
        
        # System paths
        self.home_dir = os.path.expanduser("~")
        self.desktop = os.path.join(self.home_dir, "Desktop")
        self.documents = os.path.join(self.home_dir, "Documents")
        self.downloads = os.path.join(self.home_dir, "Downloads")
        self.working_dir = os.getcwd()
    
    def set_working_dir(self, working_dir: str):
        """Set the working directory for file operations"""
        self.working_dir = working_dir
    
    def create_plan(self, request: Dict) -> Dict[str, Any]:
        """Create an execution plan (DAG) from a structured request"""
        original_input = request.get("original_input", "")
        
        prompt = f"""Create a JSON execution plan for this user request.

USER REQUEST: "{original_input}"

PATHS:
- DEFAULT (when no path specified): {self.working_dir}
- Desktop: {self.desktop}
- Documents: {self.documents}
- Downloads: {self.downloads}

AGENTS AND THEIR TOOLS:
- file_agent: read_file, write_file, create_folder, list_directory, move_file, copy_file, delete_file, search_files
- content_agent: generate_text, summarize_text
- web_agent: fetch_webpage, download_file
- system_agent: get_system_info, get_datetime, calculate, get_cwd, run_command

EXAMPLES:

Example 1: "get system info and save to info.txt"
{{
  "plan_id": "p001",
  "description": "Get system info and save to file",
  "tasks": [
    {{"task_id": "T1", "agent": "system_agent", "tool": "get_system_info", "args": {{}}, "description": "Get system information", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.working_dir}/info.txt", "content": "{{{{T1.result}}}}"}}, "description": "Save to file", "depends_on": ["T1"]}}
  ]
}}

Example 2: "write a poem about stars and save as stars.txt on Desktop"
{{
  "plan_id": "p002",
  "description": "Generate poem and save to Desktop",
  "tasks": [
    {{"task_id": "T1", "agent": "content_agent", "tool": "generate_text", "args": {{"prompt": "Write a short poem about stars"}}, "description": "Generate poem", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.desktop}/stars.txt", "content": "{{{{T1.content}}}}"}}, "description": "Save to Desktop", "depends_on": ["T1"]}}
  ]
}}

Example 3: "create folder Projects on Desktop with readme.txt inside"
{{
  "plan_id": "p003",
  "description": "Create folder and file",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "create_folder", "args": {{"folder_path": "{self.desktop}/Projects"}}, "description": "Create Projects folder", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.desktop}/Projects/readme.txt", "content": "Project folder created"}}, "description": "Create readme", "depends_on": ["T1"]}}
  ]
}}

Example 4: "what time is it"
{{
  "plan_id": "p004",
  "description": "Get current time",
  "tasks": [
    {{"task_id": "T1", "agent": "system_agent", "tool": "get_datetime", "args": {{}}, "description": "Get date and time", "depends_on": []}}
  ]
}}

Example 5: "hello" or "hi" or greeting
{{
  "plan_id": "p005",
  "description": "Respond to greeting",
  "tasks": [
    {{"task_id": "T1", "agent": "content_agent", "tool": "generate_text", "args": {{"prompt": "Respond to a friendly greeting briefly"}}, "description": "Generate greeting response", "depends_on": []}}
  ]
}}

Example 6: "fetch example.com and summarize it" (PARALLEL CAPABLE)
{{
  "plan_id": "p006",
  "description": "Fetch and summarize webpage",
  "tasks": [
    {{"task_id": "T1", "agent": "web_agent", "tool": "fetch_webpage", "args": {{"url": "https://example.com"}}, "description": "Fetch webpage", "depends_on": []}},
    {{"task_id": "T2", "agent": "content_agent", "tool": "summarize_text", "args": {{"text": "{{{{T1.content}}}}"}}, "description": "Summarize content", "depends_on": ["T1"]}}
  ]
}}

RULES:
1. If NO path mentioned -> use: {self.working_dir}
2. If "Desktop" mentioned -> use: {self.desktop}
3. If "Documents" mentioned -> use: {self.documents}
4. Use {{{{T1.content}}}} or {{{{T1.result}}}} to reference previous task output
5. Create folder BEFORE creating files inside it
6. Tasks with no dependencies can run in PARALLEL
7. For greetings/simple questions, use generate_text

Now create a plan for: "{original_input}"

Respond with ONLY valid JSON:"""

        response = self.think(prompt)
        
        try:
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                json_str = match.group()
                # Fix common JSON escape issues from LLM
                json_str = json_str.replace('\\_', '_')
                json_str = json_str.replace('\\n', ' ')
                json_str = json_str.replace('\\"', '"')
                # Fix invalid escapes by removing backslashes before non-escape chars
                json_str = re.sub(r'\\([^"\\\/bfnrtu])', r'\1', json_str)
                
                plan = json.loads(json_str)
                plan["status"] = "created"
                return {"success": True, "plan": plan}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}", "raw": response}
        except Exception as e:
            return {"success": False, "error": str(e), "raw": response}
        
        return {"success": False, "error": "No valid JSON found", "raw": response}
    
    def create_dag(self, plan: Dict) -> DAG:
        """Convert a plan to a DAG for parallel execution"""
        dag = DAG.from_plan(plan)
        return dag
    
    def validate_plan(self, plan: Dict) -> Dict[str, Any]:
        """Validate a plan before execution"""
        errors = []
        warnings = []
        
        tasks = plan.get("tasks", [])
        task_ids = {t.get("task_id") for t in tasks}
        
        for task in tasks:
            if not task.get("task_id"):
                errors.append("Task missing task_id")
            if not task.get("agent"):
                errors.append(f"Task {task.get('task_id')} missing agent")
            if not task.get("tool"):
                errors.append(f"Task {task.get('task_id')} missing tool")
            
            for dep in task.get("depends_on", []):
                if dep not in task_ids:
                    errors.append(f"Task {task.get('task_id')} depends on non-existent task {dep}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_parallel_groups(self, plan: Dict) -> List:
        """Identify tasks that can run in parallel"""
        dag = self.create_dag(plan)
        return dag.get_parallel_groups()
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a planning request"""
        if "request" in task:
            result = self.create_plan(task["request"])
            if result.get("success"):
                validation = self.validate_plan(result["plan"])
                result["validation"] = validation
                
                # Add parallelization info
                dag = self.create_dag(result["plan"])
                groups = dag.get_parallel_groups()
                result["parallel_groups"] = len(groups)
                result["can_parallelize"] = len(groups) > 1 or any(len(g) > 1 for g in groups)
            return result
        return {"success": False, "error": "No request provided"}
    
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
