"""
Synapse CLI - Multi-Agent System Command Line Interface
Cross-platform (Windows/Linux) with Gruvbox-dark theme
"""
import os
import sys
import io
import json
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
from rich.text import Text
from rich.markup import escape as rich_escape
from rich import box

# ============================================================
# GRUVBOX DARK THEME
# ============================================================
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

# ============================================================
# SAFE TEXT HELPER - Prevents Rich markup errors
# ============================================================
def safe_text(content):
    """Escape content to prevent Rich markup interpretation errors"""
    if content is None:
        return ""
    return rich_escape(str(content))

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
            task_table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY)
            task_table.add_column("Task", style=STYLE_INFO, width=6)
            task_table.add_column("Agent", style=STYLE_CATEGORY, width=14)
            task_table.add_column("Tool", style=STYLE_TOOL, width=16)
            task_table.add_column("Status", width=10)
            
            for task in tasks:
                status = task.get("status", "unknown")
                if status == "completed":
                    status_str = f"[{Gruvbox.GREEN}]+ Done[/]"
                elif status == "failed":
                    status_str = f"[{Gruvbox.RED}]x Failed[/]"
                else:
                    status_str = f"[{Gruvbox.GRAY}]{safe_text(status)}[/]"
                
                task_table.add_row(
                    safe_text(task.get("task_id", "")),
                    safe_text(task.get("agent", "")),
                    safe_text(task.get("tool", "")),
                    status_str
                )
            
            console.print(task_table)
        
        # Errors
        errors = log_entry.get("errors", [])
        if errors:
            console.print(f"\n[{Gruvbox.RED} bold]Errors[/]")
            for err in errors:
                console.print(f"  [{Gruvbox.RED}]* {safe_text(err.get('task_id', 'Unknown'))}:[/] {safe_text(err.get('error', 'Unknown error'))}")
        
        console.print()
    except Exception as e:
        console.print(f"[{Gruvbox.RED}]Error displaying log: {safe_text(str(e))}[/]")

# ============================================================
# TOOL DEFINITIONS
# ============================================================
CATEGORIES = {
    "files": {
        "name": "File Agent",
        "description": "File and folder operations",
        "color": Gruvbox.GREEN,
        "tools": {
            "read_file": {"desc": "Read content from a file", "example": "read the file notes.txt"},
            "write_file": {"desc": "Write content to a file", "example": "write 'hello' to greeting.txt"},
            "create_file": {"desc": "Create a new file", "example": "create a file called test.txt"},
            "create_folder": {"desc": "Create a folder", "example": "create a folder called Projects"},
            "list_directory": {"desc": "List folder contents", "example": "list files in my Documents"},
            "delete_file": {"desc": "Delete a file", "example": "delete old_file.txt"},
            "delete_folder": {"desc": "Delete a folder", "example": "delete the temp folder"},
            "move_file": {"desc": "Move file/folder", "example": "move report.txt to Documents"},
            "copy_file": {"desc": "Copy file/folder", "example": "copy config.txt to backup"},
            "search_files": {"desc": "Search for files", "example": "find all .py files in my project"},
        }
    },
    "content": {
        "name": "Content Agent",
        "description": "Text generation and summarization",
        "color": Gruvbox.PURPLE,
        "tools": {
            "generate_text": {"desc": "Generate text content", "example": "write an article about AI"},
            "summarize_text": {"desc": "Summarize text", "example": "summarize this document"},
        }
    },
    "web": {
        "name": "Web Agent",
        "description": "Web fetching and downloading",
        "color": Gruvbox.BLUE,
        "tools": {
            "fetch_webpage": {"desc": "Fetch and extract webpage content", "example": "fetch https://example.com"},
            "download_file": {"desc": "Download a file from URL", "example": "download file from https://..."},
        }
    },
    "system": {
        "name": "System Agent",
        "description": "System operations and utilities",
        "color": Gruvbox.ORANGE,
        "tools": {
            "run_command": {"desc": "Run shell command", "example": "run 'dir' command"},
            "get_cwd": {"desc": "Get current directory", "example": "what is the current directory"},
            "get_system_info": {"desc": "Get system information", "example": "show system info"},
            "get_datetime": {"desc": "Get current date/time", "example": "what time is it"},
            "calculate": {"desc": "Calculate math expression", "example": "calculate 25 * 4"},
        }
    },
    "data": {
        "name": "Data Tools",
        "description": "JSON and CSV handling",
        "color": Gruvbox.AQUA,
        "tools": {
            "read_json": {"desc": "Read JSON file", "example": "read data.json"},
            "write_json": {"desc": "Write JSON file", "example": "save data to output.json"},
            "read_csv": {"desc": "Read CSV file", "example": "read users.csv"},
            "write_csv": {"desc": "Write CSV file", "example": "save to report.csv"},
        }
    }
}

# ============================================================
# ASCII ART HEADER
# ============================================================
HEADER = f"""[{Gruvbox.ORANGE}]
███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗  
╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝  
███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████╗
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝[/]
[{Gruvbox.GRAY}]Multi-Agent System with MCP + A2A Communication[/]
"""

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_header():
    console.print(HEADER)

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
    
    # Use escaped brackets for Rich markup
    menu.add_row("\\[1]", "Execute a task")
    menu.add_row("\\[2]", "View agent tools")
    menu.add_row("\\[3]", "System status")
    menu.add_row("\\[4]", "View execution logs")
    menu.add_row("\\[5]", "View raw output")
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

[{Gruvbox.AQUA}]Viewing Logs[/]
Type 'log' to view detailed logs for the last executed prompt.
Select option [4] to browse all previous execution logs.
Select option [5] to view the raw JSON output.

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
    try:
        status = synapse.get_status()
        
        console.print(f"\n[{Gruvbox.ORANGE} bold]System Status[/]\n")
        
        agent_table = Table(show_header=True, header_style=STYLE_TITLE, box=box.ROUNDED, border_style=Gruvbox.GRAY)
        agent_table.add_column("Agent", style=STYLE_CATEGORY)
        agent_table.add_column("Status", style=STYLE_SUCCESS)
        agent_table.add_column("Tools", style=STYLE_INFO, justify="right")
        
        for agent in status["agents"]:
            status_text = f"[{Gruvbox.GREEN}]Running[/]" if agent["running"] else f"[{Gruvbox.RED}]Stopped[/]"
            agent_table.add_row(safe_text(agent["name"]), status_text, str(len(agent["tools"])))
        
        console.print(agent_table)
        
        mcp = status["mcp"]
        console.print(f"\n[{Gruvbox.AQUA}]MCP Server:[/] {mcp['tools_registered']} tools | {mcp['total_executions']} executions")
        console.print(f"[{Gruvbox.AQUA}]A2A Bus:[/] {status['bus']['message_count']} messages")
        
        logs = load_logs()
        console.print(f"[{Gruvbox.AQUA}]Stored Logs:[/] {len(logs)} prompts")
        console.print(f"[{Gruvbox.AQUA}]Working Dir:[/] {WORKING_DIR}\n")
    except Exception as e:
        console.print(f"[{Gruvbox.RED}]Error getting status: {safe_text(str(e))}[/]")

def display_result(result):
    """Display execution result in a clean, formatted way"""
    try:
        exec_result = result.get("stages", {}).get("execution", {})
        tasks_completed = exec_result.get("tasks_completed", 0)
        tasks_failed = exec_result.get("tasks_failed", 0)
        tasks_total = exec_result.get("tasks_total", 0)
        
        # Get task info from planning stage
        planning = result.get("stages", {}).get("planning", {})
        plan = planning.get("plan", {})
        tasks_info = plan.get("tasks", [])
        
        # Show compact status bar
        console.print()
        if result.get("success"):
            if tasks_failed == 0:
                console.print(Panel(
                    f"[{Gruvbox.GREEN}]+[/] [{Gruvbox.FG}]Completed {tasks_total} task{'s' if tasks_total != 1 else ''} successfully[/]",
                    border_style=Gruvbox.GREEN,
                    box=box.ROUNDED,
                    padding=(0, 1)
                ))
            else:
                console.print(Panel(
                    f"[{Gruvbox.YELLOW}]![/] [{Gruvbox.FG}]Completed with issues: {tasks_completed}/{tasks_total} succeeded[/]",
                    border_style=Gruvbox.YELLOW,
                    box=box.ROUNDED,
                    padding=(0, 1)
                ))
        else:
            console.print(Panel(
                f"[{Gruvbox.RED}]x[/] [{Gruvbox.FG}]Failed: {tasks_failed}/{tasks_total} tasks failed[/]",
                border_style=Gruvbox.RED,
                box=box.ROUNDED,
                padding=(0, 1)
            ))
        
        # Show task descriptions
        if tasks_info:
            console.print()
            for task in tasks_info:
                task_id = task.get("task_id", "")
                description = task.get("description", "")
                tool = task.get("tool", "")
                if description:
                    console.print(f"  [{Gruvbox.AQUA}]{task_id}[/] [{Gruvbox.GRAY}]-[/] [{Gruvbox.FG}]{safe_text(description)}[/]")
                elif tool:
                    console.print(f"  [{Gruvbox.AQUA}]{task_id}[/] [{Gruvbox.GRAY}]-[/] [{Gruvbox.FG}]{safe_text(tool)}[/]")
        
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
            
            # Skip outputs that look like internal/debug data
            if task_type == "run_command" and isinstance(content, dict):
                cmd = content.get("command", "")
                # Skip echo commands that look like debug output
                if "echo" in cmd.lower() and ("{" in cmd or "original_input" in cmd or "structured_request" in cmd):
                    continue
            
            if task_type == "list_directory" and isinstance(content, dict):
                items = content.get("items", [])
                directory = content.get("directory", "")
                console.print(f"[{Gruvbox.AQUA} bold]Contents of {safe_text(directory)}[/] [{Gruvbox.GRAY}]({len(items)} items)[/]\n")
                
                table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY)
                table.add_column("Name", style=Style(color=Gruvbox.FG))
                table.add_column("Type", style=STYLE_DIM, width=8)
                table.add_column("Size", style=STYLE_DIM, width=12)
                
                for item in items[:30]:
                    name = safe_text(item.get('name', ''))
                    item_type = item.get("type", "")
                    if item_type == "folder":
                        name = f"[{Gruvbox.BLUE}][D] {name}[/]"
                    else:
                        name = f"[F] {name}"
                    table.add_row(name, safe_text(item_type), safe_text(item.get("size", "-")))
                
                console.print(table)
                if len(items) > 30:
                    console.print(f"[{Gruvbox.GRAY}]... and {len(items) - 30} more items (type 'more' to see all)[/]")
                    has_truncated = True
            
            elif task_type == "get_system_info" and isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA} bold]System Information[/]\n")
                info_table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY, show_header=False)
                info_table.add_column("Key", style=Style(color=Gruvbox.YELLOW), width=20)
                info_table.add_column("Value", style=Style(color=Gruvbox.FG))
                for key, value in content.items():
                    info_table.add_row(safe_text(key), safe_text(value))
                console.print(info_table)
            
            elif task_type in ["get_datetime", "get_cwd"]:
                if isinstance(content, dict):
                    for key, value in content.items():
                        if key != "success":
                            console.print(f"[{Gruvbox.AQUA}]{safe_text(key)}:[/] [{Gruvbox.FG}]{safe_text(value)}[/]")
                else:
                    console.print(f"[{Gruvbox.AQUA}]Result:[/] [{Gruvbox.FG}]{safe_text(content)}[/]")
            
            elif task_type == "calculate":
                if isinstance(content, dict):
                    expr = safe_text(content.get('expression', ''))
                    res = safe_text(content.get('result', ''))
                    console.print(f"[{Gruvbox.AQUA}]Calculation:[/] [{Gruvbox.FG}]{expr}[/] = [{Gruvbox.GREEN} bold]{res}[/]")
                else:
                    console.print(f"[{Gruvbox.AQUA}]Result:[/] [{Gruvbox.FG}]{safe_text(content)}[/]")
            
            elif task_type == "generate_text":
                text_content = str(content) if content else ""
                # No empty line - print header and panel together
                console.print(f"[{Gruvbox.AQUA} bold]Generated Content[/]")
                if len(text_content) > 2000:
                    console.print(Panel(Text(text_content[:2000] + "\n\n... (truncated, type 'more' to see full)"), border_style=Gruvbox.GRAY, box=box.ROUNDED))
                    has_truncated = True
                else:
                    console.print(Panel(Text(text_content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            elif task_type in ["write_file", "create_file"]:
                if isinstance(content, dict):
                    fp = safe_text(content.get('filepath', ''))
                else:
                    fp = safe_text(content)
                console.print(f"[{Gruvbox.GREEN}]+ File saved:[/] [{Gruvbox.FG}]{fp}[/]")
            
            elif task_type == "read_file":
                text_content = str(content) if content else ""
                console.print(f"[{Gruvbox.AQUA} bold]File Content[/]")
                if len(text_content) > 2000:
                    console.print(Panel(Text(text_content[:2000] + "\n\n... (truncated, type 'more' to see full)"), border_style=Gruvbox.GRAY, box=box.ROUNDED))
                    has_truncated = True
                else:
                    console.print(Panel(Text(text_content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            elif task_type == "fetch_webpage":
                if isinstance(content, dict):
                    console.print(f"[{Gruvbox.AQUA} bold]Webpage:[/] [{Gruvbox.FG}]{safe_text(content.get('title', ''))}[/]")
                    console.print(f"[{Gruvbox.GRAY}]URL: {safe_text(content.get('url', ''))}[/]")
                    web_content = str(content.get('content', ''))
                    if len(web_content) > 1500:
                        console.print(Panel(Text(web_content[:1500] + "\n\n... (truncated, type 'more' to see full)"), border_style=Gruvbox.GRAY, box=box.ROUNDED))
                        has_truncated = True
                    else:
                        console.print(Panel(Text(web_content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            elif task_type in ["create_folder", "move_file", "copy_file", "delete_file", "delete_folder"]:
                action_name = task_type.replace('_', ' ').title()
                console.print(f"[{Gruvbox.GREEN}]+ {action_name} completed[/]")
                if isinstance(content, dict):
                    for key, value in content.items():
                        if value and key != "success":
                            console.print(f"  [{Gruvbox.GRAY}]{safe_text(key)}:[/] [{Gruvbox.FG}]{safe_text(value)}[/]")
            
            elif task_type == "run_command":
                if isinstance(content, dict):
                    stdout = content.get("stdout", "")
                    stderr = content.get("stderr", "")
                    return_code = content.get("return_code", 0)
                    
                    # Only show if there's actual output
                    if stdout and stdout.strip():
                        console.print(f"[{Gruvbox.AQUA} bold]Command Output[/]")
                        console.print(Panel(Text(str(stdout).strip()), border_style=Gruvbox.GRAY, box=box.ROUNDED))
                    if stderr and stderr.strip():
                        console.print(f"[{Gruvbox.RED}]Error Output:[/]")
                        console.print(Panel(Text(str(stderr).strip()), border_style=Gruvbox.RED, box=box.ROUNDED))
                else:
                    if content:
                        console.print(Panel(Text(str(content)), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            else:
                # Generic handler for other types
                if content:
                    if isinstance(content, dict):
                        # Filter out internal keys and display nicely
                        display_content = {k: v for k, v in content.items() if k not in ["success", "tool"] and v}
                        if display_content:
                            console.print(f"[{Gruvbox.AQUA} bold]Result[/]")
                            result_table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY, show_header=False)
                            result_table.add_column("Key", style=Style(color=Gruvbox.YELLOW), width=20)
                            result_table.add_column("Value", style=Style(color=Gruvbox.FG))
                            for key, value in display_content.items():
                                result_table.add_row(safe_text(key), safe_text(str(value)[:100]))
                            console.print(result_table)
                    else:
                        text_content = str(content)
                        if len(text_content) > 1000:
                            console.print(Panel(Text(text_content[:1000] + "\n... (truncated, type 'more' to see full)"), border_style=Gruvbox.GRAY, box=box.ROUNDED))
                            has_truncated = True
                        else:
                            console.print(Panel(Text(text_content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
        
        console.print()
        if has_truncated:
            console.print(f"[{Gruvbox.GRAY}]Type 'more' to see full output, 'log' for execution details[/]")
        else:
            console.print(f"[{Gruvbox.GRAY}]Type 'log' for execution details[/]")
    
    except Exception as e:
        console.print(f"[{Gruvbox.RED}]Error displaying result: {safe_text(str(e))}[/]")


def display_full_output():
    """Display full output without truncation"""
    global last_full_output
    
    if not last_full_output:
        console.print(f"\n[{Gruvbox.YELLOW}]No output to display. Run a prompt first.[/]\n")
        return
    
    console.print(f"\n[{Gruvbox.ORANGE} bold]Full Output[/]\n")
    
    try:
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
                    name = safe_text(item.get('name', ''))
                    item_type = item.get("type", "")
                    if item_type == "folder":
                        name = f"[{Gruvbox.BLUE}][D] {name}[/]"
                    else:
                        name = f"[F] {name}"
                    table.add_row(name, safe_text(item_type), safe_text(item.get("size", "-")))
                
                console.print(table)
            
            elif isinstance(content, dict):
                for key, value in content.items():
                    if key == "content" or key == "text":
                        console.print(Panel(Text(str(value)), border_style=Gruvbox.GRAY, box=box.ROUNDED))
                    elif key != "success":
                        console.print(f"  [{Gruvbox.YELLOW}]{safe_text(key)}:[/] {safe_text(value)}")
            
            else:
                console.print(Panel(Text(str(content)), border_style=Gruvbox.GRAY, box=box.ROUNDED))
            
            console.print()
        
        console.print()
    except Exception as e:
        console.print(f"[{Gruvbox.RED}]Error displaying full output: {safe_text(str(e))}[/]")


def display_raw_output():
    """Display raw JSON output"""
    global last_raw_result
    
    if not last_raw_result:
        console.print(f"\n[{Gruvbox.YELLOW}]No output to display. Run a prompt first.[/]\n")
        return
    
    console.print(f"\n[{Gruvbox.ORANGE} bold]Raw JSON Output[/]\n")
    
    try:
        json_str = json.dumps(last_raw_result, indent=2, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
    except Exception as e:
        console.print(f"[{Gruvbox.RED}]Error displaying raw output: {safe_text(str(e))}[/]")
    
    console.print()


def show_log_menu():
    """Show log browser"""
    logs = load_logs()
    
    if not logs:
        console.print(f"\n[{Gruvbox.YELLOW}]No logs yet. Execute some prompts first.[/]\n")
        return
    
    console.print(f"\n[{Gruvbox.ORANGE} bold]Execution Logs[/] [{Gruvbox.GRAY}]({len(logs)} entries)[/]\n")
    
    table = Table(box=box.ROUNDED, border_style=Gruvbox.GRAY)
    table.add_column("#", style=STYLE_INFO, width=4)
    table.add_column("Time", style=STYLE_DIM, width=20)
    table.add_column("Prompt", style=Style(color=Gruvbox.FG))
    table.add_column("Status", width=10)
    
    for i, log in enumerate(reversed(logs[-10:]), 1):
        timestamp = log.get("timestamp", "")[:19].replace("T", " ")
        prompt = safe_text(log.get("prompt", "")[:40])
        if len(log.get("prompt", "")) > 40:
            prompt += "..."
        success = log.get("success", False)
        status = f"[{Gruvbox.GREEN}]+ OK[/]" if success else f"[{Gruvbox.RED}]x Fail[/]"
        table.add_row(str(i), timestamp, prompt, status)
    
    console.print(table)
    console.print(f"\n[{Gruvbox.GRAY}]Enter number to view details, or 'back' to return[/]")
    
    while True:
        choice = Prompt.ask(f"[{Gruvbox.GREEN}]log #[/]", default="").strip()
        
        if choice.lower() in ['back', 'exit', 'q', '']:
            break
        
        if choice.lower() in ['clear', 'cls']:
            clear_screen()
            console.print(f"[{Gruvbox.ORANGE} bold]Execution Logs[/]\n")
            console.print(table)
            continue
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < min(10, len(logs)):
                log_entry = list(reversed(logs[-10:]))[idx]
                display_log(log_entry)
            else:
                console.print(f"[{Gruvbox.RED}]Invalid number[/]")
        except ValueError:
            console.print(f"[{Gruvbox.RED}]Enter a number or 'back'[/]")


# ============================================================
# SILENT INITIALIZATION
# ============================================================

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
            choice = Prompt.ask(f"[{Gruvbox.PURPLE}]synapse[/]", default="").strip()
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
                    text = Prompt.ask(f"[{Gruvbox.GREEN}]>[/]", default="").strip()
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
                    text = Prompt.ask(f"[{Gruvbox.GREEN}]category[/]", default="").strip().lower()
                    
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
