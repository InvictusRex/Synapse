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
        tools_desc = mcp.get_tools_for_prompt()
        
        prompt = f"""Create an execution plan for this request.

SYSTEM PATHS:
- Current Directory (DEFAULT for new files): {self.working_dir}
- Home: {self.home_dir}
- Desktop: {self.desktop}  
- Documents: {self.documents}
- Downloads: {self.downloads}

AVAILABLE TOOLS (via specialized agents):
{tools_desc}

AGENT ASSIGNMENTS:
- file_agent: filesystem tools (read_file, write_file, create_file, list_directory, move_file, copy_file, etc.)
- content_agent: content tools (generate_text, summarize_text) - ONLY for generating NEW text content (articles, reports)
- web_agent: web tools (fetch_webpage, download_file)
- system_agent: system tools (run_command, get_cwd, get_system_info, calculate, get_datetime)
- codegen_agent: code generation tools (generate_template, list_templates, generate_code) - for generating CODE from templates or AI
- scaffolding_agent: project scaffolding tools (scaffold_project, list_templates) - for bootstrapping NEW projects
- implementation_agent: section implementation tools (implement_section, generate_code) - for implementing complete project sections (backend, frontend, database, api, testing)

REQUEST:
{json.dumps(request, indent=2)}

CRITICAL RULES:
1. DEFAULT LOCATION: Create files/folders in Current Directory ({self.working_dir}) unless user specifies otherwise
2. Only use Desktop/Documents/Downloads if user explicitly mentions them
3. For "current directory" or "here" or "cwd" → use {self.working_dir}
4. For "pwd" or "what directory" → use get_cwd tool
5. Parse names correctly:
   - "the templates folder" means folder named "templates" (NOT "templates folder")
   - "a file called test.txt" means filename "test.txt"
   - "move X from A to B" means source is A/X, destination is B/X

WHEN TO USE WHICH TOOL:
- User provides EXACT content (e.g., "with content 'Hello'") → write_file directly
- User wants NEW content created (e.g., "write article about X") → generate_text then write_file
- User wants to list/read files → file_agent only
- User asks for pwd/cwd/current directory → system_agent.get_cwd
- move_file: source=full path to file/folder, destination=full path where it should go

SAVING FILES - CRITICAL:
- When the user says "save to", "save in", "save as", or specifies a folder/filename, you MUST create a write_file task using file_agent
- If a folder doesn't exist yet (e.g., "outputs"), create it first with create_folder, then write the file
- The write_file task MUST use {{TASK_ID.content}} to reference generated content from a previous task
- NEVER use content_agent to save files. content_agent ONLY generates text. file_agent saves files.

EXAMPLE - "generate a report on X and save it in outputs folder":
  T1: file_agent → create_folder → {{"folder_path": "{self.working_dir}/outputs"}}
  T2: content_agent → generate_text → {{"prompt": "Write a detailed report on X"}}
  T3: file_agent → write_file → {{"filepath": "{self.working_dir}/outputs/report.txt", "content": "{{T2.content}}"}} depends_on: [T1, T2]

For write_file/create_file: ALWAYS include "filepath" and "content" arguments
For move_file: include "source" (full path) and "destination" (full path)
For tasks needing previous output: use {{TASK_ID.content}} in args

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
