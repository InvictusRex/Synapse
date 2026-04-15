"""
Synapse CLI - Multi-Agent System Command Line Interface
Cross-platform (Windows/Linux) with Gruvbox-dark theme
"""
import os
import sys
import io
import json
import platform
from datetime import datetime

# Set working directory to where the tool is run from (not home)
WORKING_DIR = os.getcwd()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file BEFORE anything else
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.syntax import Syntax
from rich.markup import escape as rich_escape
from rich.text import Text
from rich import box

# ============================================================
# GRUVBOX DARK THEME
# ============================================================

def safe_text(content) -> str:
    """Escape content to prevent Rich markup errors"""
    if content is None:
        return ""
    return rich_escape(str(content))

class Gruvbox:
    BG = "#282828"
    FG = "#ebdbb2"
    RED = "#fb4934"
    GREEN = "#b8bb26"
    YELLOW = "#fabd2f"
    BLUE = "#83a598"
    PURPLE = "#d3869b"
    AQUA = "#8ec07c"
    ORANGE = "#fe8019"
    GRAY = "#928374"

STYLE_TITLE = Style(color=Gruvbox.ORANGE, bold=True)
STYLE_CATEGORY = Style(color=Gruvbox.AQUA, bold=True)
STYLE_TOOL = Style(color=Gruvbox.YELLOW)
STYLE_SUCCESS = Style(color=Gruvbox.GREEN)
STYLE_ERROR = Style(color=Gruvbox.RED)
STYLE_INFO = Style(color=Gruvbox.BLUE)
STYLE_DIM = Style(color=Gruvbox.GRAY)
STYLE_PROMPT = Style(color=Gruvbox.PURPLE, bold=True)

console = Console()

# On Linux, Rich's Prompt.ask() doesn't use readline, so arrow keys
# emit raw escape sequences in terminals like alacritty and xfce4.
# We use native input() on Linux (which has readline support) and
# keep Rich's Prompt.ask() on Windows where it works fine.
IS_LINUX = platform.system() != "Windows"


def prompt_input(label: str, color: str = Gruvbox.PURPLE) -> str:
    """Cross-platform prompt with arrow key support on Linux terminals."""
    if IS_LINUX:
        console.print(f"[{color}]{label}[/] ", end="")
        try:
            return input().strip()
        except EOFError:
            return ""
    else:
        return Prompt.ask(f"[{color}]{label}[/]", default="").strip()

# ============================================================
# LOGGING SYSTEM
# ============================================================
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'execution_logs.json')
MAX_LOGS = 20

os.makedirs(LOG_DIR, exist_ok=True)

# Current session data
last_log = None
last_raw_result = None
last_full_output = None  # For 'more' command

def load_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_logs(logs):
    logs = logs[-MAX_LOGS:]
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, default=str)

def create_log_entry(prompt, result):
    """Create a comprehensive log entry"""
    stages = result.get("stages", {})
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "success": result.get("success", False),
        "working_directory": WORKING_DIR,
        "stages": {
            "parsing": {},
            "planning": {},
            "execution": {}
        },
        "tasks": [],
        "task_results": {},
        "errors": [],
        "raw_output": result
    }
    
    # Parsing stage - full details
    if "parsing" in stages:
        log_entry["stages"]["parsing"] = stages["parsing"]
    
    # Planning stage - full details
    if "planning" in stages:
        plan = stages["planning"].get("plan", {})
        log_entry["stages"]["planning"] = {
            "plan_id": plan.get("plan_id", ""),
            "description": plan.get("description", ""),
            "tasks": plan.get("tasks", [])
        }
        
        for task in plan.get("tasks", []):
            log_entry["tasks"].append({
                "task_id": task.get("task_id"),
                "agent": task.get("agent"),
                "tool": task.get("tool"),
                "args": task.get("args", {}),
                "description": task.get("description", ""),
                "depends_on": task.get("depends_on", []),
                "status": "pending",
                "result": None,
                "error": None
            })
    
    # Execution stage - full details
    if "execution" in stages:
        exec_result = stages["execution"]
        log_entry["stages"]["execution"] = {
            "tasks_completed": exec_result.get("tasks_completed", 0),
            "tasks_failed": exec_result.get("tasks_failed", 0),
            "tasks_total": exec_result.get("tasks_total", 0),
            "task_states": exec_result.get("task_states", {}),
            "final_result": exec_result.get("final_result", {})
        }
        
        # Update task statuses and results
        task_states = exec_result.get("task_states", {})
        for task_id, state in task_states.items():
            for task in log_entry["tasks"]:
                if task["task_id"] == task_id:
                    task["status"] = state.get("status", "unknown")
                    task["error"] = state.get("error", None)
                    break
            
            if state.get("status") == "failed":
                log_entry["errors"].append({
                    "task_id": task_id,
                    "error": state.get("error", "Unknown error"),
                    "timestamp": datetime.now().isoformat()
                })
    
    # Final outputs
    final = result.get("final_output", {})
    log_entry["outputs"] = final.get("all_outputs", [])
    
    return log_entry

def store_log(prompt, result):
    global last_log, last_raw_result
    
    log_entry = create_log_entry(prompt, result)
    last_log = log_entry
    last_raw_result = result
    
    logs = load_logs()
    logs.append(log_entry)
    save_logs(logs)
    
    return log_entry

def display_log(log_entry):
    """Display comprehensive log entry"""
    try:
        console.print(f"\n[{Gruvbox.ORANGE} bold]EXECUTION LOG[/]\n")
        
        # Header info
        console.print(f"[{Gruvbox.AQUA} bold]Metadata[/]")
        console.print(f"  [{Gruvbox.GRAY}]Timestamp:[/]   {safe_text(log_entry.get('timestamp', 'N/A'))}")
        console.print(f"  [{Gruvbox.GRAY}]Prompt:[/]      {safe_text(log_entry.get('prompt', 'N/A'))}")
        console.print(f"  [{Gruvbox.GRAY}]Working Dir:[/] {safe_text(log_entry.get('working_directory', 'N/A'))}")
        
        success = log_entry.get('success', False)
        status_color = Gruvbox.GREEN if success else Gruvbox.RED
        console.print(f"  [{Gruvbox.GRAY}]Status:[/]      [{status_color}]{'SUCCESS' if success else 'FAILED'}[/]")
        
        # Stage 1: Parsing
        console.print(f"\n[{Gruvbox.YELLOW} bold]Stage 1: Input Parsing[/]")
        parsing = log_entry.get("stages", {}).get("parsing", {})
        if parsing:
            parsed = parsing.get("parsed", parsing)
            console.print(f"  [{Gruvbox.GRAY}]Intent:[/]     {safe_text(parsed.get('intent', 'N/A'))}")
            console.print(f"  [{Gruvbox.GRAY}]Task Type:[/]  {safe_text(parsed.get('task_type', 'N/A'))}")
            entities = parsed.get('entities', {})
            if entities:
                console.print(f"  [{Gruvbox.GRAY}]Entities:[/]")
                for key, val in entities.items():
                    console.print(f"    [{Gruvbox.PURPLE}]{safe_text(key)}:[/] {safe_text(val)}")
        
        # Stage 2: Planning
        console.print(f"\n[{Gruvbox.YELLOW} bold]Stage 2: Execution Planning[/]")
        planning = log_entry.get("stages", {}).get("planning", {})
        console.print(f"  [{Gruvbox.GRAY}]Plan ID:[/]     {safe_text(planning.get('plan_id', 'N/A'))}")
        console.print(f"  [{Gruvbox.GRAY}]Description:[/] {safe_text(planning.get('description', 'N/A'))}")
        
        # Stage 3: Task Execution
        console.print(f"\n[{Gruvbox.YELLOW} bold]Stage 3: Task Execution[/]")
        
        tasks = log_entry.get("tasks", [])
        if tasks:
            for task in tasks:
                status = task.get("status", "pending")
                if status == "completed":
                    status_str = f"[{Gruvbox.GREEN}]✓ COMPLETED[/]"
                elif status == "failed":
                    status_str = f"[{Gruvbox.RED}]✗ FAILED[/]"
                else:
                    status_str = f"[{Gruvbox.GRAY}]○ {status.upper()}[/]"
                
                console.print(f"\n  [{Gruvbox.PURPLE} bold]{safe_text(task.get('task_id', 'N/A'))}[/] {status_str}")
                console.print(f"    [{Gruvbox.GRAY}]Agent:[/]       {safe_text(task.get('agent', 'N/A'))}")
                console.print(f"    [{Gruvbox.GRAY}]Tool:[/]        {safe_text(task.get('tool', 'N/A'))}")
                console.print(f"    [{Gruvbox.GRAY}]Description:[/] {safe_text(task.get('description', 'N/A'))}")
                
                deps = task.get("depends_on", [])
                if deps:
                    console.print(f"    [{Gruvbox.GRAY}]Depends On:[/]  {', '.join(deps)}")
                
                args = task.get("args", {})
                if args:
                    console.print(f"    [{Gruvbox.GRAY}]Arguments:[/]")
                    for key, val in args.items():
                        val_str = str(val)[:80] + "..." if len(str(val)) > 80 else str(val)
                        console.print(f"      [{Gruvbox.AQUA}]{safe_text(key)}:[/] {safe_text(val_str)}")
                
                if task.get("error"):
                    console.print(f"    [{Gruvbox.RED}]Error:[/] {safe_text(task.get('error'))}")
        
        # Execution Summary
        execution = log_entry.get("stages", {}).get("execution", {})
        console.print(f"\n[{Gruvbox.YELLOW} bold]Execution Summary[/]")
        console.print(f"  [{Gruvbox.GRAY}]Total Tasks:[/]     {execution.get('tasks_total', 0)}")
        console.print(f"  [{Gruvbox.GREEN}]Completed:[/]       {execution.get('tasks_completed', 0)}")
        console.print(f"  [{Gruvbox.RED}]Failed:[/]          {execution.get('tasks_failed', 0)}")
        
        # Errors
        errors = log_entry.get("errors", [])
        if errors:
            console.print(f"\n[{Gruvbox.RED} bold]Errors[/]")
            for err in errors:
                console.print(f"  [{Gruvbox.RED}]{safe_text(err.get('task_id'))}:[/] {safe_text(err.get('error'))}")
        
        # Outputs
        outputs = log_entry.get("outputs", [])
        if outputs:
            console.print(f"\n[{Gruvbox.AQUA} bold]Outputs[/]")
            for out in outputs:
                console.print(f"  [{Gruvbox.PURPLE}]{safe_text(out.get('task'))}[/] ({safe_text(out.get('type'))})")
                content = out.get('content', '')
                if isinstance(content, dict):
                    for k, v in list(content.items())[:5]:
                        v_str = str(v)[:60] + "..." if len(str(v)) > 60 else str(v)
                        console.print(f"    [{Gruvbox.GRAY}]{safe_text(k)}:[/] {safe_text(v_str)}")
                else:
                    content_str = str(content)[:200]
                    if len(str(content)) > 200:
                        content_str += "..."
                    console.print(f"    {safe_text(content_str)}")
        
        console.print()
    except Exception as e:
        console.print(f"\n[{Gruvbox.RED}]Error displaying log: {safe_text(str(e))}[/]")
        console.print(f"[{Gruvbox.GRAY}]Try using option 5 (raw output) to view as JSON[/]\n")

def display_raw_output():
    """Display raw JSON output from last execution"""
    global last_raw_result
    
    if not last_raw_result:
        console.print(f"\n[{Gruvbox.YELLOW}]No execution results yet. Run a prompt first.[/]\n")
        return
    
    console.print(f"\n[{Gruvbox.ORANGE} bold]Raw Output (JSON)[/]\n")
    
    try:
        json_str = json.dumps(last_raw_result, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
    except:
        console.print(str(last_raw_result))
    
    console.print()

def show_log_menu():
    """Show log selection menu"""
    logs = load_logs()
    
    if not logs:
        console.print(f"\n[{Gruvbox.YELLOW}]No logs found.[/]\n")
        return
    
    console.print(f"\n[{Gruvbox.AQUA}]Log History[/] [{Gruvbox.GRAY}](type 'back' to return)[/]")
    console.print(f"[{Gruvbox.GRAY}]Last {len(logs)} prompts:[/]\n")
    
    log_table = Table(
        show_header=True,
        header_style=STYLE_TITLE,
        box=box.ROUNDED,
        border_style=Gruvbox.GRAY,
        title="[bold]Execution Logs[/]",
        title_style=STYLE_TITLE
    )
    log_table.add_column("#", style=STYLE_PROMPT, width=4)
    log_table.add_column("Time", style=STYLE_DIM, width=18)
    log_table.add_column("Prompt", style=Style(color=Gruvbox.FG), max_width=40)
    log_table.add_column("Status", width=10)
    log_table.add_column("Tasks", style=STYLE_DIM, width=8)
    
    for i, log in enumerate(reversed(logs), 1):
        timestamp = log.get("timestamp", "")[:16].replace("T", " ")
        prompt = log.get("prompt", "")[:40]
        if len(log.get("prompt", "")) > 40:
            prompt += "..."
        
        success = log.get("success", False)
        status = f"[{Gruvbox.GREEN}]OK[/]" if success else f"[{Gruvbox.RED}]FAIL[/]"
        
        exec_info = log.get("stages", {}).get("execution", {})
        tasks = f"{exec_info.get('tasks_completed', 0)}/{exec_info.get('tasks_total', 0)}"
        
        log_table.add_row(str(i), timestamp, prompt, status, tasks)
    
    console.print(log_table)
    console.print(f"\n[{Gruvbox.GRAY}]Enter log number to view details, or 'back' to return[/]\n")
    
    while True:
        text = prompt_input("log", Gruvbox.PURPLE)
        text_lower = text.lower()
        
        if text_lower in ['back', 'exit', 'q', 'menu', '']:
            break
        
        if text_lower in ['clear', 'cls']:
            clear_screen()
            console.print(f"[{Gruvbox.AQUA}]Log History[/] [{Gruvbox.GRAY}](type 'back' to return)[/]")
            console.print(log_table)
            console.print(f"\n[{Gruvbox.GRAY}]Enter log number to view details[/]\n")
            continue
        
        try:
            log_num = int(text)
            if 1 <= log_num <= len(logs):
                selected_log = logs[-(log_num)]
                display_log(selected_log)
            else:
                console.print(f"[{Gruvbox.RED}]Invalid number. Enter 1-{len(logs)}[/]")
        except ValueError:
            console.print(f"[{Gruvbox.RED}]Enter a number or 'back' to return[/]")

# ============================================================
# ASCII ART
# ============================================================
SYNAPSE_ASCII = f"""[{Gruvbox.ORANGE}]
███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗  
╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝  
███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████╗
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝[/]"""

SUBTITLE = f"[{Gruvbox.GRAY}]Multi-Agent System with A2A Communication & MCP Tools[/]"

# ============================================================
# AGENT CATEGORIES & TOOLS
# ============================================================
CATEGORIES = {
    "file": {
        "name": "File Agent",
        "description": "File system operations",
        "color": Gruvbox.GREEN,
        "tools": {
            "read_file": {"desc": "Read content from a file", "example": "Read the file notes.txt from my Desktop"},
            "write_file": {"desc": "Write content to a file", "example": "Create hello.txt on Desktop with content \"Hello!\""},
            "create_file": {"desc": "Create a new file with content", "example": "Create todo.txt in Documents"},
            "list_directory": {"desc": "List contents of a directory", "example": "List all files on my Desktop"},
            "create_folder": {"desc": "Create a new folder", "example": "Create a folder called Projects on Desktop"},
            "delete_file": {"desc": "Delete a file", "example": "Delete old_notes.txt from Desktop"},
            "delete_folder": {"desc": "Delete a folder", "example": "Delete the TempFiles folder from Desktop"},
            "move_file": {"desc": "Move a file or folder", "example": "Move reports folder from Desktop to Documents"},
            "copy_file": {"desc": "Copy a file or folder", "example": "Copy config.txt from Desktop to Downloads"},
            "search_files": {"desc": "Search for files by pattern", "example": "Search for all .txt files in Documents"},
        }
    },
    "content": {
        "name": "Content Agent",
        "description": "AI content generation",
        "color": Gruvbox.PURPLE,
        "tools": {
            "generate_text": {"desc": "Generate text content using AI", "example": "Write an article about AI"},
            "summarize_text": {"desc": "Summarize text content", "example": "Summarize my report.txt file"},
        }
    },
    "web": {
        "name": "Web Agent",
        "description": "Web operations",
        "color": Gruvbox.BLUE,
        "tools": {
            "fetch_webpage": {"desc": "Fetch and extract webpage content", "example": "Fetch https://example.com"},
            "download_file": {"desc": "Download a file from URL", "example": "Download image.jpg from URL"},
        }
    },
    "system": {
        "name": "System Agent",
        "description": "System operations",
        "color": Gruvbox.YELLOW,
        "tools": {
            "run_command": {"desc": "Run a shell command (POSIX compatible)", "example": "ls, pwd, cat file.txt"},
            "get_cwd": {"desc": "Get current working directory", "example": "What is the current directory?"},
            "get_system_info": {"desc": "Get system information", "example": "Get system information"},
            "get_datetime": {"desc": "Get current date and time", "example": "What time is it?"},
            "calculate": {"desc": "Evaluate math expressions", "example": "Calculate 256 * 4 + sqrt(144)"},
        }
    },
    "data": {
        "name": "Data Agent",
        "description": "JSON, CSV operations",
        "color": Gruvbox.AQUA,
        "tools": {
            "read_json": {"desc": "Read a JSON file", "example": "Read config.json from Desktop"},
            "write_json": {"desc": "Write data to JSON", "example": "Create settings.json on Desktop"},
            "read_csv": {"desc": "Read a CSV file", "example": "Read data.csv from Documents"},
            "write_csv": {"desc": "Write data to CSV", "example": "Create contacts.csv on Desktop"},
        }
    },
    "codegen": {
        "name": "CodeGen Agent",
        "description": "Template code generation",
        "color": Gruvbox.ORANGE,
        "tools": {
            "generate_template": {"desc": "Generate code from a template (class, function, route, etc.)", "example": "Generate a python class template called UserService"},
            "generate_code": {"desc": "Generate code using AI from a description", "example": "Generate a Python function to sort a list of dictionaries by key"},
            "list_templates": {"desc": "List all available code and project templates", "example": "Show me all available templates"},
        }
    },
    "scaffolding": {
        "name": "Scaffolding Agent",
        "description": "Project bootstrapping",
        "color": Gruvbox.PURPLE,
        "tools": {
            "scaffold_project": {"desc": "Scaffold a new project from a template", "example": "Scaffold a new React project called my-app"},
            "list_templates": {"desc": "List available project templates", "example": "What project templates are available?"},
        }
    },
    "implementation": {
        "name": "Implementation Agent",
        "description": "Sectional implementation (backend, frontend, etc.)",
        "color": Gruvbox.BLUE,
        "tools": {
            "implement_section": {"desc": "Implement a complete project section", "example": "Implement a Python backend for my-project"},
            "generate_code": {"desc": "Generate custom code using AI", "example": "Generate a REST API with user authentication"},
        }
    }
}

# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_header():
    console.print(SYNAPSE_ASCII)
    console.print(SUBTITLE)
    console.print()

def show_categories():
    table = Table(
        show_header=True,
        header_style=STYLE_TITLE,
        box=box.ROUNDED,
        border_style=Gruvbox.GRAY,
        title="[bold]Agent Categories[/]",
        title_style=STYLE_TITLE
    )
    
    table.add_column("Agent", style=STYLE_CATEGORY, width=20)
    table.add_column("Description", style=Style(color=Gruvbox.FG))
    table.add_column("Tools", style=STYLE_DIM, width=8)
    
    for key, cat in CATEGORIES.items():
        table.add_row(
            cat["name"],
            cat["description"],
            str(len(cat["tools"]))
        )
    
    console.print(table)
    console.print()

def show_tools(category_key):
    if category_key not in CATEGORIES:
        console.print(f"[{Gruvbox.RED}]Unknown category: {safe_text(category_key)}[/]")
        return
    
    cat = CATEGORIES[category_key]
    
    console.print(f"\n[{cat['color']} bold]{cat['name']}[/]")
    console.print(f"[{Gruvbox.GRAY}]{cat['description']}[/]\n")
    
    for tool_name, tool_info in cat["tools"].items():
        console.print(f"  [{Gruvbox.YELLOW}]{tool_name}[/]")
        console.print(f"    [{Gruvbox.FG}]{tool_info['desc']}[/]")
        console.print(f"    [{Gruvbox.GRAY}]Example:[/] [{Gruvbox.GREEN}]\"{tool_info['example']}\"[/]")
        console.print()

def show_menu():
    menu = Table(
        show_header=True,
        header_style=STYLE_TITLE,
        box=box.ROUNDED,
        border_style=Gruvbox.GRAY,
        title="[bold]Actions Menu[/]",
        title_style=STYLE_TITLE,
        padding=(0, 2)
    )
    menu.add_column("Key", style=STYLE_PROMPT, width=8)
    menu.add_column("Action", style=Style(color=Gruvbox.FG))
    
    menu.add_row("\\[1]", "Execute a task")
    menu.add_row("\\[2]", "View agent tools")
    menu.add_row("\\[3]", "System status")
    menu.add_row("\\[4]", "View execution logs")
    menu.add_row("\\[5]", "View raw output")
    menu.add_row("\\[6]", "Start A2A Protocol Server")
    menu.add_row("\\[h]", "Help")
    menu.add_row("\\[q]", "Quit")
    
    console.print(menu)
    console.print(f"\n[{Gruvbox.GRAY}]Tip: Type 'log' to view last log, 'more' to see full output[/]")

def show_help():
    """Show help along with categories and menu"""
    help_text = f"""
[{Gruvbox.ORANGE} bold]How to Use Synapse CLI[/]

[{Gruvbox.AQUA}]Execute Tasks[/]
Type natural language commands describing what you want to do.
The multi-agent system will plan and execute your request.

[{Gruvbox.AQUA}]Example Commands[/]
[{Gruvbox.GREEN}]"List files on my Desktop"[/]
[{Gruvbox.GREEN}]"What time is it?"[/]
[{Gruvbox.GREEN}]"Create a folder called Projects on my Desktop"[/]
[{Gruvbox.GREEN}]"Write an article about AI and save it to my Desktop"[/]
[{Gruvbox.GREEN}]"Fetch https://example.com and summarize it"[/]

[{Gruvbox.AQUA}]Development Commands[/]
[{Gruvbox.GREEN}]"Scaffold a new React project called my-app"[/]
[{Gruvbox.GREEN}]"Generate a Python class template called UserService"[/]
[{Gruvbox.GREEN}]"Implement a Python backend for my-project"[/]
[{Gruvbox.GREEN}]"Implement a React frontend for my-project"[/]
[{Gruvbox.GREEN}]"Generate a FastAPI router for handling users"[/]

[{Gruvbox.AQUA}]Viewing Logs[/]
Type 'log' to view detailed logs for the last executed prompt.
Select option [4] to browse all previous execution logs.
Select option [5] to view the raw JSON output.

[{Gruvbox.AQUA}]A2A Protocol Server[/]
Select option [6] to start the A2A HTTP server.
Exposes REST API, SSE streaming, push notifications, and agent discovery.
API docs at http://localhost:8000/docs when running.

[{Gruvbox.AQUA}]Navigation[/]
Type 'back' or press ESC to return to previous menu.
Type 'clear' to clear screen and show only prompt.
Type 'h' or 'help' for this help screen.
Type 'q' or 'quit' to exit.

[{Gruvbox.AQUA}]Working Directory[/]
[{Gruvbox.GRAY}]{WORKING_DIR}[/]
"""
    console.print(Panel(help_text, title="[bold]Help[/]", border_style=Gruvbox.GRAY, box=box.ROUNDED))
    console.print()
    show_categories()
    show_menu()

def show_status(synapse):
    status = synapse.get_status()
    
    console.print(f"\n[{Gruvbox.ORANGE} bold]System Status[/]\n")
    
    agent_table = Table(show_header=True, header_style=STYLE_TITLE, box=box.ROUNDED, border_style=Gruvbox.GRAY)
    agent_table.add_column("Agent", style=STYLE_CATEGORY)
    agent_table.add_column("Status", style=STYLE_SUCCESS)
    agent_table.add_column("Tools", style=STYLE_INFO, justify="right")
    
    for agent in status["agents"]:
        status_text = f"[{Gruvbox.GREEN}]Running[/]" if agent["running"] else f"[{Gruvbox.RED}]Stopped[/]"
        agent_table.add_row(agent["name"], status_text, str(len(agent["tools"])))
    
    console.print(agent_table)
    
    mcp = status["mcp"]
    console.print(f"\n[{Gruvbox.AQUA}]MCP Server:[/] {mcp['tools_registered']} tools | {mcp['total_executions']} executions")
    console.print(f"[{Gruvbox.AQUA}]A2A Bus:[/] {status['bus']['message_count']} messages")
    
    logs = load_logs()
    console.print(f"[{Gruvbox.AQUA}]Stored Logs:[/] {len(logs)} prompts")
    console.print(f"[{Gruvbox.AQUA}]Working Dir:[/] {WORKING_DIR}\n")

def display_result(result):
    try:
        # Handle unknown requests
        if result.get("error") == "Unknown request":
            console.print(f"\n[{Gruvbox.YELLOW}]Unknown Request.[/]")
            console.print(f"[{Gruvbox.GRAY}]Could not identify an actionable task. Try rephrasing your request.[/]\n")
            return

        exec_result = result.get("stages", {}).get("execution", {})
        tasks_completed = exec_result.get("tasks_completed", 0)
        tasks_failed = exec_result.get("tasks_failed", 0)
        tasks_total = exec_result.get("tasks_total", 0)

        if result.get("success"):
            if tasks_failed == 0:
                console.print(f"\n[{Gruvbox.GREEN}]Completed: All {tasks_total} tasks successful[/]\n")
            else:
                console.print(f"\n[{Gruvbox.YELLOW}]Completed with issues: {tasks_completed}/{tasks_total} succeeded[/]\n")
        else:
            console.print(f"\n[{Gruvbox.RED}]Failed: {tasks_failed}/{tasks_total} tasks failed[/]\n")
        
        task_states = exec_result.get("task_states", {})
        if task_states:
            console.print(f"[{Gruvbox.GRAY}]Task Execution:[/]")
            for task_id, state in task_states.items():
                if state["status"] == "completed":
                    console.print(f"  [{Gruvbox.GREEN}]+[/] {safe_text(task_id)}: Completed")
                else:
                    console.print(f"  [{Gruvbox.RED}]x[/] {safe_text(task_id)}: {safe_text(state.get('error', 'Failed'))}")
            console.print()
        
        final = result.get("final_output", {})
        all_outputs = final.get("all_outputs", [])
        
        # Store full output for 'more' command
        global last_full_output
        last_full_output = all_outputs
        
        has_truncated = False
        
        for output in all_outputs:
            task_type = output.get("type", "")
            content = output.get("content", "")
            
            if task_type == "list_directory" and isinstance(content, dict):
                items = content.get("items", [])
                directory = content.get("directory", "")
                console.print(f"[{Gruvbox.AQUA}]Contents of {safe_text(directory)}[/] ({len(items)} items)\n")
                
                table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY)
                table.add_column("Name", style=Style(color=Gruvbox.FG))
                table.add_column("Type", style=STYLE_DIM, width=8)
                table.add_column("Size", style=STYLE_DIM, width=12)
                
                for item in items[:30]:
                    prefix = "\\[D]" if item.get("type") == "folder" else "\\[F]"
                    table.add_row(f"{prefix} {safe_text(item.get('name', ''))}", item.get("type", ""), item.get("size", "-"))
                
                console.print(table)
                if len(items) > 30:
                    console.print(f"[{Gruvbox.GRAY}]... and {len(items) - 30} more items (type 'more' to see all)[/]")
                    has_truncated = True
            
            elif task_type == "get_system_info" and isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA}]System Information[/]\n")
                for key, value in content.items():
                    console.print(f"  [{Gruvbox.YELLOW}]{safe_text(key)}:[/] {safe_text(value)}")
            
            elif task_type in ["get_datetime", "get_cwd"]:
                if isinstance(content, dict):
                    for key, value in content.items():
                        if key != "success":
                            console.print(f"[{Gruvbox.AQUA}]{safe_text(key)}:[/] {safe_text(value)}")
                else:
                    console.print(f"[{Gruvbox.AQUA}]Result:[/] {safe_text(content)}")
            
            elif task_type == "calculate":
                if isinstance(content, dict):
                    console.print(f"[{Gruvbox.AQUA}]Calculation:[/] {safe_text(content.get('expression', ''))} = [{Gruvbox.GREEN}]{safe_text(content.get('result', ''))}[/]")
                else:
                    console.print(f"[{Gruvbox.AQUA}]Result:[/] {safe_text(content)}")
            
            elif task_type == "generate_text":
                text_content = str(content)
                console.print(f"[{Gruvbox.AQUA}]Generated Content:[/]\n")
                if len(text_content) > 2000:
                    # Use Text to avoid markup parsing
                    panel_content = Text(text_content[:2000] + "\n\n... (truncated, type 'more' to see full)")
                    console.print(Panel(panel_content, border_style=Gruvbox.GRAY, box=box.ROUNDED))
                    has_truncated = True
                else:
                    console.print(Panel(Text(text_content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            elif task_type in ["write_file", "create_file"]:
                fp = content.get('filepath', content) if isinstance(content, dict) else content
                console.print(f"[{Gruvbox.GREEN}]File saved:[/] {safe_text(fp)}")
            
            elif task_type == "read_file":
                text_content = str(content)
                console.print(f"[{Gruvbox.AQUA}]File Content:[/]\n")
                if len(text_content) > 2000:
                    # Use Text to avoid markup parsing
                    panel_content = Text(text_content[:2000] + "\n\n... (truncated, type 'more' to see full)")
                    console.print(Panel(panel_content, border_style=Gruvbox.GRAY, box=box.ROUNDED))
                    has_truncated = True
                else:
                    console.print(Panel(Text(text_content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            elif task_type == "fetch_webpage":
                if isinstance(content, dict):
                    console.print(f"[{Gruvbox.AQUA}]Webpage:[/] {safe_text(content.get('title', ''))}")
                    console.print(f"[{Gruvbox.GRAY}]URL: {safe_text(content.get('url', ''))}[/]")
                    web_content = str(content.get('content', ''))
                    if len(web_content) > 1500:
                        panel_content = Text(web_content[:1500] + "\n\n... (truncated, type 'more' to see full)")
                        console.print(Panel(panel_content, border_style=Gruvbox.GRAY, box=box.ROUNDED))
                        has_truncated = True
                    else:
                        console.print(Panel(Text(web_content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            elif task_type == "scaffold_project" and isinstance(content, dict):
                console.print(f"[{Gruvbox.GREEN}]Project scaffolded:[/] {safe_text(content.get('project_name', ''))}")
                console.print(f"  [{Gruvbox.GRAY}]Template:[/]  {safe_text(content.get('template', ''))}")
                console.print(f"  [{Gruvbox.GRAY}]Location:[/]  {safe_text(content.get('project_dir', ''))}")
                files = content.get('files_created', [])
                folders = content.get('folders_created', [])
                if folders:
                    console.print(f"  [{Gruvbox.AQUA}]Folders:[/]   {', '.join(folders)}")
                if files:
                    console.print(f"  [{Gruvbox.AQUA}]Files:[/]")
                    for f in files:
                        console.print(f"    [{Gruvbox.YELLOW}]+[/] {safe_text(f)}")

            elif task_type == "implement_section" and isinstance(content, dict):
                console.print(f"[{Gruvbox.GREEN}]Section implemented:[/] {safe_text(content.get('section', ''))} ({safe_text(content.get('tech', ''))})")
                console.print(f"  [{Gruvbox.GRAY}]Description:[/] {safe_text(content.get('description', ''))}")
                console.print(f"  [{Gruvbox.GRAY}]Location:[/]    {safe_text(content.get('section_dir', ''))}")
                files = content.get('files_created', [])
                folders = content.get('folders_created', [])
                if folders:
                    console.print(f"  [{Gruvbox.AQUA}]Folders:[/]     {', '.join(folders)}")
                if files:
                    console.print(f"  [{Gruvbox.AQUA}]Files:[/]")
                    for f in files:
                        console.print(f"    [{Gruvbox.YELLOW}]+[/] {safe_text(f)}")

            elif task_type == "generate_template" and isinstance(content, dict):
                console.print(f"[{Gruvbox.GREEN}]Template generated:[/] {safe_text(content.get('template_type', ''))} - {safe_text(content.get('name', ''))}")
                code = content.get('code', '')
                if code:
                    lang = content.get('language', 'text')
                    syntax = Syntax(code, lang, theme="monokai")
                    console.print(Panel(syntax, border_style=Gruvbox.GRAY, box=box.ROUNDED))

            elif task_type == "generate_code" and isinstance(content, dict):
                console.print(f"[{Gruvbox.GREEN}]Code generated:[/] {safe_text(content.get('language', 'code'))}")
                code = content.get('code', '')
                if code:
                    lang = content.get('language', 'text')
                    if len(code) > 3000:
                        display_code = code[:3000] + "\n\n... (truncated, type 'more' to see full)"
                        has_truncated = True
                    else:
                        display_code = code
                    syntax = Syntax(display_code, lang, theme="monokai")
                    console.print(Panel(syntax, border_style=Gruvbox.GRAY, box=box.ROUNDED))

            elif task_type == "list_templates" and isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA}]Available Templates[/]\n")
                code_templates = content.get('code_templates', {})
                if code_templates:
                    console.print(f"  [{Gruvbox.YELLOW}]Code Templates:[/]")
                    for lang, types in code_templates.items():
                        console.print(f"    [{Gruvbox.GREEN}]{safe_text(lang)}:[/] {', '.join(types)}")
                project_templates = content.get('project_templates', [])
                if project_templates:
                    console.print(f"\n  [{Gruvbox.YELLOW}]Project Templates:[/]")
                    console.print(f"    {', '.join(project_templates)}")
                section_templates = content.get('section_templates', {})
                if section_templates:
                    console.print(f"\n  [{Gruvbox.YELLOW}]Section Templates:[/]")
                    for section, techs in section_templates.items():
                        console.print(f"    [{Gruvbox.GREEN}]{safe_text(section)}:[/] {', '.join(techs)}")

            elif task_type in ["create_folder", "move_file", "copy_file", "delete_file", "delete_folder"]:
                console.print(f"[{Gruvbox.GREEN}]{task_type.replace('_', ' ').title()} completed[/]")
                if isinstance(content, dict):
                    for key, value in content.items():
                        if value:
                            console.print(f"  [{Gruvbox.GRAY}]{safe_text(key)}:[/] {safe_text(value)}")
            
            else:
                if content:
                    if isinstance(content, dict):
                        for key, value in content.items():
                            console.print(f"  [{Gruvbox.YELLOW}]{safe_text(key)}:[/] {safe_text(value)}")
                    else:
                        text_content = str(content)
                        if len(text_content) > 1000:
                            console.print(Text(text_content[:1000] + "\n... (truncated, type 'more' to see full)"))
                            has_truncated = True
                        else:
                            console.print(Text(text_content))
        
        console.print()
        if has_truncated:
            console.print(f"[{Gruvbox.GRAY}]Type 'more' to see full output, 'log' for execution log[/]")
        else:
            console.print(f"[{Gruvbox.GRAY}]Type 'log' to view detailed execution log[/]")
    
    except Exception as e:
        console.print(f"\n[{Gruvbox.RED}]Error displaying result: {safe_text(str(e))}[/]")
        console.print(f"[{Gruvbox.GRAY}]Try using option 5 (raw output) to view as JSON[/]\n")


def display_full_output():
    """Display full output without truncation"""
    global last_full_output
    
    if not last_full_output:
        console.print(f"\n[{Gruvbox.YELLOW}]No output to display. Run a prompt first.[/]\n")
        return
    
    try:
        console.print(f"\n[{Gruvbox.ORANGE} bold]Full Output[/]\n")
        
        for output in last_full_output:
            task_type = output.get("type", "")
            content = output.get("content", "")
            
            console.print(f"[{Gruvbox.AQUA} bold]{safe_text(task_type)}[/]")
            
            if task_type == "list_directory" and isinstance(content, dict):
                items = content.get("items", [])
                directory = content.get("directory", "")
                console.print(f"Directory: {safe_text(directory)} ({len(items)} items)\n")
                
                table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY)
                table.add_column("Name", style=Style(color=Gruvbox.FG))
                table.add_column("Type", style=STYLE_DIM, width=8)
                table.add_column("Size", style=STYLE_DIM, width=12)
                
                for item in items:  # All items, no truncation
                    prefix = "\\[D]" if item.get("type") == "folder" else "\\[F]"
                    table.add_row(f"{prefix} {safe_text(item.get('name', ''))}", item.get("type", ""), item.get("size", "-"))
                
                console.print(table)
            
            elif isinstance(content, dict):
                for key, value in content.items():
                    if key == "content" or key == "text":
                        # Use Text object for raw content to avoid markup parsing
                        console.print()
                        console.print(Text(str(value)))
                        console.print()
                    elif key != "success":
                        console.print(f"  [{Gruvbox.YELLOW}]{safe_text(key)}:[/] {safe_text(value)}")
            
            else:
                # Use Text object for raw content
                console.print()
                console.print(Text(str(content)))
                console.print()
            
            console.print()
        
        console.print()
    except Exception as e:
        console.print(f"\n[{Gruvbox.RED}]Error displaying output: {safe_text(str(e))}[/]")
        console.print(f"[{Gruvbox.GRAY}]Try using option 5 (raw output) to view as JSON[/]\n")

# ============================================================
# SILENT INITIALIZATION
# ============================================================

def start_a2a_server(synapse):
    """Start the A2A Protocol Server from within the CLI"""
    import os as _os

    host = _os.environ.get("A2A_HOST", "0.0.0.0")
    port = int(_os.environ.get("A2A_PORT", "8000"))

    console.print(f"\n[{Gruvbox.ORANGE} bold]A2A Protocol Server[/]\n")
    console.print(f"  [{Gruvbox.GRAY}]Host:[/]       [{Gruvbox.GREEN}]{host}[/]")
    console.print(f"  [{Gruvbox.GRAY}]Port:[/]       [{Gruvbox.GREEN}]{port}[/]")
    console.print(f"  [{Gruvbox.GRAY}]Agent Card:[/] [{Gruvbox.AQUA}]http://localhost:{port}/.well-known/agent.json[/]")
    console.print(f"  [{Gruvbox.GRAY}]API Docs:[/]   [{Gruvbox.AQUA}]http://localhost:{port}/docs[/]")
    console.print(f"  [{Gruvbox.GRAY}]Health:[/]     [{Gruvbox.AQUA}]http://localhost:{port}/health[/]")
    console.print(f"\n  [{Gruvbox.GRAY}]Auth:[/]       [{Gruvbox.YELLOW}]x-api-key: synapse-dev-key[/] (default)")
    console.print(f"\n[{Gruvbox.GRAY}]Press Ctrl+C to stop the server and return to CLI.[/]\n")

    try:
        import uvicorn
        from a2a.streaming import StreamManager
        from a2a.push_notifications import PushNotificationDispatcher
        from a2a.task_manager import TaskManager
        from a2a.agent_registry import AgentRegistry
        from a2a.server import create_app

        stream_manager = StreamManager()
        push_dispatcher = PushNotificationDispatcher()
        task_manager = TaskManager(
            stream_manager=stream_manager,
            push_dispatcher=push_dispatcher,
        )
        agent_registry = AgentRegistry(synapse, task_manager)

        app = create_app(
            synapse=synapse,
            task_manager=task_manager,
            agent_registry=agent_registry,
            stream_manager=stream_manager,
            push_dispatcher=push_dispatcher,
        )

        uvicorn.run(app, host=host, port=port, log_level="info")

    except KeyboardInterrupt:
        console.print(f"\n[{Gruvbox.ORANGE}]A2A server stopped. Returning to CLI.[/]\n")
    except ImportError as e:
        console.print(f"\n[{Gruvbox.RED}]Missing dependency: {safe_text(str(e))}[/]")
        console.print(f"[{Gruvbox.GRAY}]Run: pip install fastapi uvicorn httpx[/]\n")
    except Exception as e:
        console.print(f"\n[{Gruvbox.RED}]Server error: {safe_text(str(e))}[/]\n")


def init_synapse_silent():
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    
    try:
        import logging
        logging.disable(logging.CRITICAL)
        from synapse import Synapse
        synapse = Synapse()
        logging.disable(logging.NOTSET)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    return synapse

# ============================================================
# MAIN
# ============================================================

def main():
    clear_screen()
    show_header()
    
    if not os.environ.get("GROQ_API_KEY"):
        console.print(f"[{Gruvbox.RED}]GROQ_API_KEY not found![/]")
        console.print(f"[{Gruvbox.GRAY}]Please add your API key to the .env file:[/]")
        console.print(f'[{Gruvbox.GREEN}]GROQ_API_KEY=your-key-here[/]')
        console.print(f"\n[{Gruvbox.GRAY}]Get a free key at: https://console.groq.com[/]\n")
        return
    
    with Progress(SpinnerColumn(style=Style(color=Gruvbox.ORANGE)), TextColumn(f"[{Gruvbox.GRAY}]Starting...[/]"), console=console, transient=True) as progress:
        progress.add_task("", total=None)
        try:
            synapse = init_synapse_silent()
        except Exception as e:
            console.print(f"[{Gruvbox.RED}]Failed to initialize: {safe_text(str(e))}[/]")
            return
    
    clear_screen()
    show_header()
    show_categories()
    show_menu()
    
    # Set working directory on synapse
    synapse.set_working_dir(WORKING_DIR)
    
    while True:
        try:
            console.print()
            choice = prompt_input("synapse", Gruvbox.PURPLE)
            choice_lower = choice.lower()
            
            if not choice:
                continue
            
            # Quit
            elif choice_lower in ['q', 'quit', 'exit']:
                console.print(f"\n[{Gruvbox.ORANGE}]Goodbye![/]\n")
                break
            
            # Help
            elif choice_lower in ['h', 'help']:
                clear_screen()
                show_header()
                show_help()
            
            # Clear - only show prompt
            elif choice_lower in ['clear', 'cls']:
                clear_screen()
            
            # View last log
            elif choice_lower == 'log':
                if last_log:
                    display_log(last_log)
                else:
                    console.print(f"[{Gruvbox.YELLOW}]No logs yet. Execute a prompt first.[/]")
            
            # Execute task mode
            elif choice_lower == '1':
                console.print(f"\n[{Gruvbox.AQUA}]Task Execution Mode[/] [{Gruvbox.GRAY}](type 'back' to return)[/]")
                
                while True:
                    text = prompt_input(">", Gruvbox.GREEN)
                    text_lower = text.lower()
                    
                    if text_lower in ['back', 'exit', 'menu', 'q', '']:
                        break
                    
                    if text_lower == 'log':
                        if last_log:
                            display_log(last_log)
                        else:
                            console.print(f"[{Gruvbox.YELLOW}]No logs yet.[/]")
                        continue
                    
                    if text_lower == 'more':
                        display_full_output()
                        continue
                    
                    if text_lower in ['clear', 'cls']:
                        clear_screen()
                        console.print(f"[{Gruvbox.AQUA}]Task Execution Mode[/] [{Gruvbox.GRAY}](type 'back' to return)[/]")
                        continue
                    
                    with Progress(SpinnerColumn(style=Style(color=Gruvbox.ORANGE)), TextColumn(f"[{Gruvbox.GRAY}]Processing...[/]"), console=console, transient=True) as progress:
                        progress.add_task("", total=None)
                        result = synapse.process(text, WORKING_DIR)
                    
                    store_log(text, result)
                    display_result(result)
            
            # Tool browser
            elif choice_lower == '2':
                console.print(f"\n[{Gruvbox.AQUA}]Tool Browser[/] [{Gruvbox.GRAY}](type 'back' to return)[/]")
                console.print(f"[{Gruvbox.GRAY}]Categories: {', '.join(CATEGORIES.keys())}[/]\n")
                
                while True:
                    text = prompt_input("category", Gruvbox.GREEN).lower()
                    
                    if text in ['back', 'exit', 'menu', 'q', '']:
                        break
                    
                    if text in ['clear', 'cls']:
                        clear_screen()
                        console.print(f"[{Gruvbox.AQUA}]Tool Browser[/] [{Gruvbox.GRAY}](type 'back' to return)[/]")
                        console.print(f"[{Gruvbox.GRAY}]Categories: {', '.join(CATEGORIES.keys())}[/]\n")
                        continue
                    
                    if text in CATEGORIES:
                        show_tools(text)
                    else:
                        console.print(f"[{Gruvbox.RED}]Unknown category. Options: {', '.join(CATEGORIES.keys())}[/]")
            
            # System status
            elif choice_lower == '3':
                show_status(synapse)
            
            # View logs
            elif choice_lower == '4':
                show_log_menu()
            
            # View raw output
            elif choice_lower == '5':
                display_raw_output()

            # Start A2A Protocol Server
            elif choice_lower == '6':
                start_a2a_server(synapse)
            
            # View full output (more)
            elif choice_lower == 'more':
                display_full_output()
            
            # Show menu
            elif choice_lower == 'menu':
                clear_screen()
                show_header()
                show_categories()
                show_menu()
            
            # Direct task execution
            else:
                with Progress(SpinnerColumn(style=Style(color=Gruvbox.ORANGE)), TextColumn(f"[{Gruvbox.GRAY}]Processing...[/]"), console=console, transient=True) as progress:
                    progress.add_task("", total=None)
                    result = synapse.process(choice, WORKING_DIR)
                
                store_log(choice, result)
                display_result(result)
                
        except KeyboardInterrupt:
            console.print(f"\n[{Gruvbox.ORANGE}]Interrupted. Type 'q' to quit.[/]")
        except Exception as e:
            console.print(f"[{Gruvbox.RED}]Error: {safe_text(str(e))}[/]")

if __name__ == "__main__":
    main()
