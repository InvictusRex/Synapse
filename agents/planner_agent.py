"""
Planner Agent
Creates execution plans (DAGs) from structured requests
"""
import os
import json
import re
from typing import Dict, Any, Optional, List, Tuple

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from core.dag import DAG, DAGTask
from mcp.server import ToolCategory


# ============================================================
# JSON EXTRACTION & CLEANUP
# ============================================================
#
# LLMs are not reliable JSON emitters. Common problems we see in real
# responses from Gemini, Groq, and friends:
#
#   1. Markdown fences:   ```json ... ```
#   2. Chatty preamble:   "Sure! Here's the plan: { ... }"
#   3. Trailing commas:   {"a": 1, "b": 2,}  (valid Python, invalid JSON)
#   4. Unescaped Windows paths: "C:\Users\TheKi"
#   5. Single quotes:     {'a': 1}
#   6. Truncation:        response cut off mid-object
#
# We use a tolerant cleanup pipeline plus a balanced-brace fallback so
# that ONE bad character doesn't torpedo the whole plan.


def _clean_json_string(s: str) -> str:
    """Apply all the common cleanups LLM-generated JSON needs."""
    # 1. Strip markdown fences anywhere in the string.
    s = re.sub(r'```(?:json|JSON)?\s*', '', s)
    s = re.sub(r'```\s*', '', s)
    
    # 2. Windows paths: \\ -> / , and single \ after drive letters.
    s = re.sub(r'([A-Za-z]):\\\\', r'\1:/', s)
    s = re.sub(r'\\\\', '/', s)
    s = re.sub(r'([A-Za-z]):\\([^\\"])', r'\1:/\2', s)
    
    # 3. Hand-coded invalid escape sequences we've seen in practice.
    for bad, good in (('\\_', '_'), ('\\:', ':'),
                       ('\\(', '('), ('\\)', ')')):
        s = s.replace(bad, good)
    
    # (step 4 removed - the old regex converted valid \n escapes inside
    # JSON string values into spaces, which mangled content. If the LLM
    # emits literal unescaped newlines inside strings, json.loads will
    # give "Invalid control character" - a different error we can't paper
    # over here without a full tokenizer.)
    
    # 5. Any leftover stray backslash that isn't a valid JSON escape
    # becomes a forward slash. Preserves path separators when the LLM
    # forgets to double-backslash ("C:\U" -> "C:/U", not "C:U").
    s = re.sub(r'\\([^"\\/bfnrtu])', r'/\1', s)
    
    # 6. ** Trailing commas **. LLMs emit these constantly. JSON forbids
    # them, and the error you see is "Expecting property name enclosed
    # in double quotes". Strip any comma immediately before } or ].
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    
    # 7. Collapse double/triple commas that sometimes appear when the
    # LLM tries to "fix itself" mid-generation.
    s = re.sub(r',\s*,+', ',', s)
    
    # 8. ** Leading commas **. The OTHER half of the same bug: LLMs
    # sometimes emit `{, "key": ...}` or `[, "x"]`. Strip any comma
    # immediately after { or [. Same error signature: "Expecting
    # property name enclosed in double quotes: line 1 column 2".
    s = re.sub(r'([{\[])\s*,+', r'\1', s)
    
    # 9. ** Unquoted object keys **. Gemini and Groq occasionally emit
    # Python-style dicts like {plan_id: "p001"} without quoting keys.
    # json.loads reports this as "Expecting property name enclosed in
    # double quotes" too - the SAME error signature the user is seeing.
    #
    # We accept any identifier that appears right after `{`, `,`, or a
    # line start (with optional whitespace) and is followed by `:`. This
    # catches both multi-line pretty-printed JSON and single-line JSON,
    # without false-positiving on identifier-looking text inside string
    # values (which would be preceded by `"`, not by `{` / `,`).
    s = re.sub(
        r'([{,])(\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)',
        r'\1\2"\3"\4',
        s
    )
    # Also cover the case where the JSON starts with an unquoted key
    # (no preceding `{` on the same line in a multi-line response).
    s = re.sub(
        r'(^|\n)(\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)',
        r'\1\2"\3"\4',
        s
    )
    
    return s


def _extract_balanced_braces(s: str, start: int = 0) -> Optional[str]:
    """
    Find the first balanced `{...}` substring starting at or after
    position `start`. Properly tracks strings (so braces inside "..."
    don't count) and escape sequences. Returns the substring or None.
    """
    # Find the first opening brace
    idx = s.find('{', start)
    if idx < 0:
        return None
    
    depth = 0
    in_string = False
    escape = False
    for i in range(idx, len(s)):
        ch = s[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return s[idx:i+1]
    return None  # Unbalanced - LLM truncated mid-object


def _parse_plan_response(response: str) -> Tuple[Optional[Dict], Optional[str], str]:
    """
    Try hard to get a plan dict out of an LLM response.
    
    Returns (plan_dict, error_message, raw_response). Exactly one of
    plan_dict / error_message will be non-None. raw_response is always
    included so callers can surface it for debugging.
    """
    if not response:
        return None, "Empty LLM response", ""
    
    raw = response
    
    # Strategy A: greedy match from first { to last }.
    # This handles the common case of a single JSON blob with optional
    # chatty preamble or afterword.
    greedy = re.search(r'\{[\s\S]*\}', response)
    greedy_result = None
    if greedy:
        candidate = greedy.group()
        cleaned = _clean_json_string(candidate)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                greedy_result = parsed
                # If it's already plan-shaped, use it immediately.
                if "tasks" in parsed:
                    return parsed, None, raw
        except json.JSONDecodeError as e1:
            first_err = f"Invalid JSON: {e1}"
        except Exception as e1:
            first_err = f"Parse error: {e1}"
        else:
            first_err = None
    else:
        first_err = "No JSON object found in response"
    
    # Strategy B: balanced-brace extraction from the first '{'.
    # Useful when the LLM appended trailing text that greedy would swallow.
    balanced = _extract_balanced_braces(response)
    if balanced:
        cleaned = _clean_json_string(balanced)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "tasks" in parsed:
                return parsed, None, raw
            # Keep this as a second-choice result in case nothing better
            # turns up.
            if greedy_result is None and isinstance(parsed, dict):
                greedy_result = parsed
        except json.JSONDecodeError:
            pass
    
    # Strategy C: scan for multiple `{...}` blocks. Prefer a plan-shaped
    # one (has "tasks"); fall back to anything parseable.
    pos = 0
    while pos < len(response):
        blob = _extract_balanced_braces(response, pos)
        if not blob:
            break
        cleaned = _clean_json_string(blob)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "tasks" in parsed:
                return parsed, None, raw
        except Exception:
            pass
        # Advance past this blob
        blob_idx = response.find(blob, pos)
        pos = (blob_idx + len(blob)) if blob_idx >= 0 else pos + 1
    
    # Last resort: return the greedy/balanced result even if it doesn't
    # have "tasks" - it still might be a partial plan or something the
    # caller can work with.
    if greedy_result is not None:
        return greedy_result, None, raw
    
    return None, first_err or "Could not extract a parseable JSON object", raw


# ============================================================


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
        # NOTE: normalize to forward slashes. On Windows, os.path.join gives
        # backslashes ("C:\Users\TheKi\Desktop") which embed badly into the
        # JSON examples shown to the LLM - the resulting JSON is invalid
        # unless every backslash is escaped, and partial escape-stripping
        # in the cleanup regex below used to collapse the path into
        # "C:\UsersTheKiDesktop". Forward slashes work fine on all platforms
        # and make the prompt examples unambiguous.
        self.home_dir = os.path.expanduser("~").replace("\\", "/")
        self.desktop = os.path.join(self.home_dir, "Desktop").replace("\\", "/")
        self.documents = os.path.join(self.home_dir, "Documents").replace("\\", "/")
        self.downloads = os.path.join(self.home_dir, "Downloads").replace("\\", "/")
        self.working_dir = os.getcwd().replace("\\", "/")
    
    def set_working_dir(self, working_dir: str):
        """Set the working directory for file operations"""
        self.working_dir = working_dir.replace("\\", "/")
    
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

AGENTS AND THEIR TOOLS (each tool belongs to exactly ONE agent -
when you pick a tool, you MUST set "agent" to the owner listed here):

file_agent  (filesystem operations - reading, writing, and moving files on disk):
  - list_directory     REQUIRES "directory" (full path)
  - read_file          REQUIRES "filepath"
  - write_file         REQUIRES "filepath", "content"
  - create_folder      REQUIRES "folder_path"
  - delete_file        REQUIRES "filepath"
  - delete_folder      REQUIRES "folder_path"
  - move_file          REQUIRES "source", "destination"
  - copy_file          REQUIRES "source", "destination"
  - search_files       REQUIRES "directory", "pattern"

content_agent  (AI-generated text):
  - generate_text      REQUIRES "prompt"
  - summarize_text     REQUIRES "text"

web_agent  (internet operations):
  - fetch_webpage      REQUIRES "url" (must start with https://)
  - download_file      REQUIRES "url", "save_path"

system_agent  (system information and commands):
  - get_system_info    no args
  - get_datetime       no args
  - calculate          REQUIRES "expression"
  - get_cwd            no args
  - run_command        REQUIRES "command"

state_agent  (READ-ONLY observations of system state - notice that
check_file_exists belongs HERE, not to file_agent, because it just
checks; it never reads the file):
  - get_active_window        no args (foreground window)
  - list_open_windows        no args (all visible window titles)
  - list_running_processes   OPTIONAL "limit" (default 50)
  - check_process_running    REQUIRES "process_name"  e.g. "chrome"
  - check_file_exists        REQUIRES "filepath"   <-- NOT file_agent

perception_agent  (visual capture):
  - take_screenshot    OPTIONAL "save_path", OPTIONAL "window_title"
                       If "window_title" is provided, the tool will
                       find that window by substring match, bring it
                       to focus, then capture only that window's area.
                       Without it, captures the full screen.

EXAMPLES:

Example 1: "list files in Desktop" or "list all files on Desktop"
{{
  "plan_id": "p001",
  "description": "List Desktop files",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "list_directory", "args": {{"directory": "{self.desktop}"}}, "description": "List Desktop files", "depends_on": []}}
  ]
}}

Example 2: "list files in Documents"
{{
  "plan_id": "p002",
  "description": "List Documents files",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "list_directory", "args": {{"directory": "{self.documents}"}}, "description": "List Documents files", "depends_on": []}}
  ]
}}

Example 3: "list files in current directory"
{{
  "plan_id": "p003",
  "description": "List current directory files",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "list_directory", "args": {{"directory": "{self.working_dir}"}}, "description": "List current directory", "depends_on": []}}
  ]
}}

Example 4: "get system info and save to info.txt"
{{
  "plan_id": "p004",
  "description": "Get system info and save to file",
  "tasks": [
    {{"task_id": "T1", "agent": "system_agent", "tool": "get_system_info", "args": {{}}, "description": "Get system information", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.working_dir}/info.txt", "content": "{{{{T1.result}}}}"}}, "description": "Save to file", "depends_on": ["T1"]}}
  ]
}}

Example 5: "write a poem about stars and save as stars.txt on Desktop"
{{
  "plan_id": "p005",
  "description": "Generate poem and save to Desktop",
  "tasks": [
    {{"task_id": "T1", "agent": "content_agent", "tool": "generate_text", "args": {{"prompt": "Write a short poem about stars"}}, "description": "Generate poem", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.desktop}/stars.txt", "content": "{{{{T1.content}}}}"}}, "description": "Save to Desktop", "depends_on": ["T1"]}}
  ]
}}

Example 6: "create folder Projects on Desktop with readme.txt inside"
{{
  "plan_id": "p006",
  "description": "Create folder and file",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "create_folder", "args": {{"folder_path": "{self.desktop}/Projects"}}, "description": "Create Projects folder", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.desktop}/Projects/readme.txt", "content": "Project folder created"}}, "description": "Create readme", "depends_on": ["T1"]}}
  ]
}}

Example 7: "what time is it"
{{
  "plan_id": "p007",
  "description": "Get current time",
  "tasks": [
    {{"task_id": "T1", "agent": "system_agent", "tool": "get_datetime", "args": {{}}, "description": "Get date and time", "depends_on": []}}
  ]
}}

Example 8: "hello" or "hi" or greeting
{{
  "plan_id": "p008",
  "description": "Respond to greeting",
  "tasks": [
    {{"task_id": "T1", "agent": "content_agent", "tool": "generate_text", "args": {{"prompt": "Respond to a friendly greeting briefly"}}, "description": "Generate greeting response", "depends_on": []}}
  ]
}}

Example 9: "fetch example.com and summarize it"
{{
  "plan_id": "p009",
  "description": "Fetch and summarize webpage",
  "tasks": [
    {{"task_id": "T1", "agent": "web_agent", "tool": "fetch_webpage", "args": {{"url": "https://example.com"}}, "description": "Fetch webpage", "depends_on": []}},
    {{"task_id": "T2", "agent": "content_agent", "tool": "summarize_text", "args": {{"text": "{{{{T1.content}}}}"}}, "description": "Summarize content", "depends_on": ["T1"]}}
  ]
}}

Example 10: "create a file called test.txt with Hello World"
{{
  "plan_id": "p010",
  "description": "Create test file",
  "tasks": [
    {{"task_id": "T1", "agent": "file_agent", "tool": "write_file", "args": {{"filepath": "{self.working_dir}/test.txt", "content": "Hello World"}}, "description": "Create test.txt", "depends_on": []}}
  ]
}}

Example 11: "calculate 25 * 4 + 100"
{{
  "plan_id": "p011",
  "description": "Calculate expression",
  "tasks": [
    {{"task_id": "T1", "agent": "system_agent", "tool": "calculate", "args": {{"expression": "25 * 4 + 100"}}, "description": "Calculate", "depends_on": []}}
  ]
}}

Example 12: "what window is currently focused" or "what am I looking at"
{{
  "plan_id": "p012",
  "description": "Get active window",
  "tasks": [
    {{"task_id": "T1", "agent": "state_agent", "tool": "get_active_window", "args": {{}}, "description": "Get active window", "depends_on": []}}
  ]
}}

Example 13: "what windows do I have open" or "list my open windows"
{{
  "plan_id": "p013",
  "description": "List open windows",
  "tasks": [
    {{"task_id": "T1", "agent": "state_agent", "tool": "list_open_windows", "args": {{}}, "description": "List visible windows", "depends_on": []}}
  ]
}}

Example 14: "is chrome running"
{{
  "plan_id": "p014",
  "description": "Check if Chrome is running",
  "tasks": [
    {{"task_id": "T1", "agent": "state_agent", "tool": "check_process_running", "args": {{"process_name": "chrome"}}, "description": "Check chrome", "depends_on": []}}
  ]
}}

Example 15: "take a screenshot"
{{
  "plan_id": "p015",
  "description": "Capture a screenshot",
  "tasks": [
    {{"task_id": "T1", "agent": "perception_agent", "tool": "take_screenshot", "args": {{}}, "description": "Take screenshot (auto-named)", "depends_on": []}}
  ]
}}

Example 16: "take a screenshot and save it to Desktop/shot.png"
{{
  "plan_id": "p016",
  "description": "Capture screenshot to specific path",
  "tasks": [
    {{"task_id": "T1", "agent": "perception_agent", "tool": "take_screenshot", "args": {{"save_path": "{self.desktop}/shot.png"}}, "description": "Take screenshot to Desktop", "depends_on": []}}
  ]
}}

Example 17: "does the file report.txt exist on Desktop"
{{
  "plan_id": "p017",
  "description": "Check file existence",
  "tasks": [
    {{"task_id": "T1", "agent": "state_agent", "tool": "check_file_exists", "args": {{"filepath": "{self.desktop}/report.txt"}}, "description": "Check file", "depends_on": []}}
  ]
}}

Example 18: "delete the file shot.png from Desktop"
Note: the "check first, then delete" pattern. check_file_exists is
on state_agent, delete_file is on file_agent. Do NOT route
check_file_exists to file_agent.
{{
  "plan_id": "p018",
  "description": "Delete file with existence check",
  "tasks": [
    {{"task_id": "T1", "agent": "state_agent", "tool": "check_file_exists", "args": {{"filepath": "{self.desktop}/shot.png"}}, "description": "Check file exists", "depends_on": []}},
    {{"task_id": "T2", "agent": "file_agent", "tool": "delete_file", "args": {{"filepath": "{self.desktop}/shot.png"}}, "description": "Delete file", "depends_on": ["T1"]}}
  ]
}}

Example 19: "take a screenshot of the chrome window and save it to Desktop/chrome.png"
Note: one task. "window_title" focuses the target window first, so
the capture shows Chrome rather than the Synapse window.
{{
  "plan_id": "p019",
  "description": "Screenshot of Chrome window",
  "tasks": [
    {{"task_id": "T1", "agent": "perception_agent", "tool": "take_screenshot", "args": {{"window_title": "chrome", "save_path": "{self.desktop}/chrome.png"}}, "description": "Capture chrome", "depends_on": []}}
  ]
}}

RULES:
1. ALWAYS include ALL required arguments for each tool
2. For list_directory, ALWAYS include "directory" with FULL PATH
3. If NO path mentioned -> use: {self.working_dir}
4. If "Desktop" mentioned -> use: {self.desktop}
5. If "Documents" mentioned -> use: {self.documents}
6. If "Downloads" mentioned -> use: {self.downloads}
7. Use {{{{T1.content}}}} or {{{{T1.result}}}} to reference previous task output
8. Create folder BEFORE creating files inside it
9. Tasks with no dependencies can run in PARALLEL
10. For greetings/simple questions, use generate_text
11. For "is X running / open / focused / on screen" questions, prefer state_agent tools over filesystem tools
12. For "what does the screen look like" / "capture screen" requests, use perception_agent.take_screenshot
13. If the user asks for a screenshot of a specific window or app (e.g. "chrome window", "notepad", "the browser"), pass "window_title" so the tool focuses that window and captures only its area
14. check_file_exists is a STATE tool (state_agent), NOT a filesystem tool - never route it to file_agent

Now create a plan for: "{original_input}"

Respond with ONLY valid JSON (no markdown, no explanation):"""

        response = self.think(prompt)
        plan, err, raw = _parse_plan_response(response)
        
        if plan is not None:
            plan["status"] = "created"
            return {"success": True, "plan": plan}
        
        # Parse failed. Include a snippet of the raw LLM response so
        # the caller can see exactly what the model returned - far
        # more useful than a bare "Invalid JSON" error.
        snippet = (raw or "")[:300]
        return {
            "success": False,
            "error": f"{err}. LLM response (first 300 chars): {snippet!r}",
            "raw": raw
        }
    
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
