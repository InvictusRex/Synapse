"""
Synapse CLI - Multi-Agent System Command Line Interface
Cross-platform (Windows/Linux) with Gruvbox-dark theme
"""
import os
import sys
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
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
            "run_command": {"desc": "Run a shell command", "example": "Run the command 'dir'"},
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
    }
}

# ============================================================
# INPUT WITH ESC SUPPORT
# ============================================================

def get_input(prompt_str):
    """Get input with ESC support on Windows"""
    if os.name == 'nt':
        try:
            import msvcrt
            sys.stdout.write(prompt_str)
            sys.stdout.flush()
            chars = []
            while True:
                char = msvcrt.getwch()
                if char == '\x1b':  # ESC
                    sys.stdout.write('\n')
                    return None
                elif char == '\r':  # Enter
                    sys.stdout.write('\n')
                    return ''.join(chars)
                elif char == '\x08':  # Backspace
                    if chars:
                        chars.pop()
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif char == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                else:
                    chars.append(char)
                    sys.stdout.write(char)
                    sys.stdout.flush()
        except ImportError:
            return input(prompt_str)
    else:
        # Linux/Mac - ESC harder to detect, use regular input
        try:
            result = input(prompt_str)
            return result
        except EOFError:
            return None

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
        console.print(f"[{Gruvbox.RED}]Unknown category: {category_key}[/]")
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
    
    menu.add_row("[1]", "Execute a task")
    menu.add_row("[2]", "View agent tools")
    menu.add_row("[3]", "System status")
    menu.add_row("[h]", "Help")
    menu.add_row("[q]", "Quit")
    
    console.print(menu)

def show_help():
    help_text = f"""
[{Gruvbox.ORANGE} bold]How to Use Synapse CLI[/]

[{Gruvbox.AQUA}]1. Execute Tasks[/]
   Type natural language commands describing what you want to do.
   The multi-agent system will plan and execute your request.

[{Gruvbox.AQUA}]2. Example Commands[/]
   [{Gruvbox.GREEN}]"List files on my Desktop"[/]
   [{Gruvbox.GREEN}]"What time is it?"[/]
   [{Gruvbox.GREEN}]"Create a folder called Projects on my Desktop"[/]
   [{Gruvbox.GREEN}]"Write an article about AI and save it to my Desktop"[/]
   [{Gruvbox.GREEN}]"Fetch https://example.com and summarize it"[/]

[{Gruvbox.AQUA}]3. Navigation[/]
   [{Gruvbox.GRAY}]Press ESC or type 'back' to return to previous menu[/]
   [{Gruvbox.GRAY}]Type 'clear' to clear screen[/]
"""
    console.print(Panel(help_text, title="[bold]Help[/]", border_style=Gruvbox.GRAY, box=box.ROUNDED))

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
    console.print(f"[{Gruvbox.AQUA}]A2A Bus:[/] {status['bus']['message_count']} messages\n")

def display_result(result):
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
                console.print(f"  [{Gruvbox.GREEN}]+[/] {task_id}: Completed")
            else:
                console.print(f"  [{Gruvbox.RED}]x[/] {task_id}: {state.get('error', 'Failed')}")
        console.print()
    
    final = result.get("final_output", {})
    all_outputs = final.get("all_outputs", [])
    
    for output in all_outputs:
        task_type = output.get("type", "")
        content = output.get("content", "")
        
        if task_type == "list_directory" and isinstance(content, dict):
            items = content.get("items", [])
            directory = content.get("directory", "")
            console.print(f"[{Gruvbox.AQUA}]Contents of {directory}[/] ({len(items)} items)\n")
            
            table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY)
            table.add_column("Name", style=Style(color=Gruvbox.FG))
            table.add_column("Type", style=STYLE_DIM, width=8)
            table.add_column("Size", style=STYLE_DIM, width=12)
            
            for item in items[:30]:
                prefix = "[D]" if item.get("type") == "folder" else "[F]"
                table.add_row(f"{prefix} {item.get('name', '')}", item.get("type", ""), item.get("size", "-"))
            
            console.print(table)
            if len(items) > 30:
                console.print(f"[{Gruvbox.GRAY}]... and {len(items) - 30} more items[/]")
        
        elif task_type == "get_system_info" and isinstance(content, dict):
            console.print(f"[{Gruvbox.AQUA}]System Information[/]\n")
            for key, value in content.items():
                console.print(f"  [{Gruvbox.YELLOW}]{key}:[/] {value}")
        
        elif task_type == "get_datetime":
            dt = content.get('datetime', content) if isinstance(content, dict) else content
            console.print(f"[{Gruvbox.AQUA}]Current Time:[/] {dt}")
        
        elif task_type == "calculate":
            if isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA}]Calculation:[/] {content.get('expression', '')} = [{Gruvbox.GREEN}]{content.get('result', '')}[/]")
            else:
                console.print(f"[{Gruvbox.AQUA}]Result:[/] {content}")
        
        elif task_type == "generate_text":
            console.print(f"[{Gruvbox.AQUA}]Generated Content:[/]\n")
            console.print(Panel(str(content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
        
        elif task_type in ["write_file", "create_file"]:
            fp = content.get('filepath', content) if isinstance(content, dict) else content
            console.print(f"[{Gruvbox.GREEN}]File saved:[/] {fp}")
        
        elif task_type == "read_file":
            console.print(f"[{Gruvbox.AQUA}]File Content:[/]\n")
            console.print(Panel(str(content)[:2000], border_style=Gruvbox.GRAY, box=box.ROUNDED))
        
        elif task_type == "fetch_webpage":
            if isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA}]Webpage:[/] {content.get('title', '')}")
                console.print(f"[{Gruvbox.GRAY}]URL: {content.get('url', '')}[/]")
                console.print(Panel(str(content.get('content', ''))[:1500], border_style=Gruvbox.GRAY, box=box.ROUNDED))
        
        elif task_type in ["create_folder", "move_file", "copy_file", "delete_file", "delete_folder"]:
            console.print(f"[{Gruvbox.GREEN}]{task_type.replace('_', ' ').title()} completed[/]")
            if isinstance(content, dict):
                for key, value in content.items():
                    if value:
                        console.print(f"  [{Gruvbox.GRAY}]{key}:[/] {value}")
        
        else:
            if content:
                if isinstance(content, dict):
                    for key, value in content.items():
                        console.print(f"  [{Gruvbox.YELLOW}]{key}:[/] {value}")
                else:
                    console.print(str(content)[:1000])
    
    console.print()

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
        console.print(f"[{Gruvbox.RED}]GROQ_API_KEY not set![/]")
        console.print(f"[{Gruvbox.GRAY}]Set it with:[/]")
        if os.name == 'nt':
            console.print(f'[{Gruvbox.GREEN}]$env:GROQ_API_KEY="your-key-here"[/]')
        else:
            console.print(f'[{Gruvbox.GREEN}]export GROQ_API_KEY="your-key-here"[/]')
        console.print(f"\n[{Gruvbox.GRAY}]Get a free key at: https://console.groq.com[/]\n")
        return
    
    with Progress(SpinnerColumn(style=Style(color=Gruvbox.ORANGE)), TextColumn(f"[{Gruvbox.GRAY}]Starting...[/]"), console=console, transient=True) as progress:
        progress.add_task("", total=None)
        try:
            synapse = init_synapse_silent()
        except Exception as e:
            console.print(f"[{Gruvbox.RED}]Failed to initialize: {e}[/]")
            return
    
    clear_screen()
    show_header()
    show_categories()
    show_menu()
    
    while True:
        try:
            console.print()
            choice = Prompt.ask(f"[{Gruvbox.PURPLE}]synapse[/]", default="").strip().lower()
            
            if not choice:
                continue
            
            elif choice in ['q', 'quit', 'exit']:
                console.print(f"\n[{Gruvbox.ORANGE}]Goodbye![/]\n")
                break
            
            elif choice == '1':
                console.print(f"\n[{Gruvbox.AQUA}]Task Execution Mode[/] [{Gruvbox.GRAY}](ESC or 'back' to return)[/]")
                
                while True:
                    text = get_input(f"\033[38;2;211;134;155m>\033[0m ")
                    
                    if text is None or (text and text.lower() in ['back', 'exit', 'q', 'menu']):
                        break
                    
                    if text:
                        with Progress(SpinnerColumn(style=Style(color=Gruvbox.ORANGE)), TextColumn(f"[{Gruvbox.GRAY}]Processing...[/]"), console=console, transient=True) as progress:
                            progress.add_task("", total=None)
                            result = synapse.process(text)
                        display_result(result)
            
            elif choice == '2':
                console.print(f"\n[{Gruvbox.AQUA}]Tool Browser[/] [{Gruvbox.GRAY}](ESC or 'back' to return)[/]")
                console.print(f"[{Gruvbox.GRAY}]Categories: {', '.join(CATEGORIES.keys())}[/]\n")
                
                while True:
                    text = get_input(f"\033[38;2;211;134;155mcategory>\033[0m ")
                    
                    if text is None or (text and text.lower() in ['back', 'exit', 'q', 'menu']):
                        break
                    
                    if text and text.lower() in CATEGORIES:
                        show_tools(text.lower())
                    elif text:
                        console.print(f"[{Gruvbox.RED}]Unknown category. Options: {', '.join(CATEGORIES.keys())}[/]")
            
            elif choice == '3':
                show_status(synapse)
            
            elif choice in ['h', 'help']:
                show_help()
            
            elif choice in ['clear', 'cls']:
                clear_screen()
                show_header()
                show_categories()
                show_menu()
            
            elif choice == 'menu':
                show_menu()
            
            else:
                with Progress(SpinnerColumn(style=Style(color=Gruvbox.ORANGE)), TextColumn(f"[{Gruvbox.GRAY}]Processing...[/]"), console=console, transient=True) as progress:
                    progress.add_task("", total=None)
                    result = synapse.process(choice)
                display_result(result)
                
        except KeyboardInterrupt:
            console.print(f"\n[{Gruvbox.ORANGE}]Interrupted. Type 'q' to quit.[/]")
        except Exception as e:
            console.print(f"[{Gruvbox.RED}]Error: {e}[/]")

if __name__ == "__main__":
    main()
