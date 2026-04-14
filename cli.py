"""
Synapse CLI - Multi-Agent System Command Line Interface
Cross-platform (Windows/Linux) with Gruvbox-dark theme
"""
import os
import sys
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
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

# Styles
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
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝[/]
"""

SUBTITLE = f"[{Gruvbox.GRAY}]━━━ Multi-Agent System with A2A Communication & MCP Tools ━━━[/]"

# ============================================================
# AGENT CATEGORIES & TOOLS
# ============================================================
CATEGORIES = {
    "file": {
        "name": "📁 File Agent",
        "description": "File system operations - read, write, copy, move, delete",
        "color": Gruvbox.GREEN,
        "tools": {
            "read_file": {
                "desc": "Read content from a file",
                "example": "Read the file C:\\Users\\Me\\notes.txt"
            },
            "write_file": {
                "desc": "Write content to a file (creates if doesn't exist)",
                "example": "Create a file called hello.txt on my Desktop with content \"Hello World!\""
            },
            "create_file": {
                "desc": "Create a new file with content",
                "example": "Create a file named todo.txt in my Documents with content \"Buy groceries\""
            },
            "list_directory": {
                "desc": "List contents of a directory",
                "example": "List all files on my Desktop"
            },
            "create_folder": {
                "desc": "Create a new folder",
                "example": "Create a folder called Projects on my Desktop"
            },
            "delete_file": {
                "desc": "Delete a file",
                "example": "Delete the file old_notes.txt from my Desktop"
            },
            "delete_folder": {
                "desc": "Delete a folder",
                "example": "Delete the folder TempFiles from my Desktop"
            },
            "move_file": {
                "desc": "Move a file or folder to new location",
                "example": "Move the reports folder from Desktop to Documents"
            },
            "copy_file": {
                "desc": "Copy a file or folder",
                "example": "Copy config.txt from Desktop to Downloads"
            },
            "search_files": {
                "desc": "Search for files matching a pattern",
                "example": "Search for all .txt files in my Documents"
            },
        }
    },
    "content": {
        "name": "✍️  Content Agent",
        "description": "AI-powered content generation and summarization",
        "color": Gruvbox.PURPLE,
        "tools": {
            "generate_text": {
                "desc": "Generate text content using AI",
                "example": "Write an article about renewable energy and save it to my Desktop as energy.txt"
            },
            "summarize_text": {
                "desc": "Summarize text content",
                "example": "Read my report.txt file and summarize it"
            },
        }
    },
    "web": {
        "name": "🌐 Web Agent",
        "description": "Web operations - fetch pages, download files",
        "color": Gruvbox.BLUE,
        "tools": {
            "fetch_webpage": {
                "desc": "Fetch a webpage and extract text content",
                "example": "Fetch https://example.com and tell me what it's about"
            },
            "download_file": {
                "desc": "Download a file from URL",
                "example": "Download https://example.com/image.jpg and save it to my Desktop as photo.jpg"
            },
        }
    },
    "system": {
        "name": "💻 System Agent",
        "description": "System operations - commands, info, calculations",
        "color": Gruvbox.YELLOW,
        "tools": {
            "run_command": {
                "desc": "Run a shell/terminal command",
                "example": "Run the command 'dir' in my current directory"
            },
            "get_system_info": {
                "desc": "Get system information (OS, Python, paths)",
                "example": "Get system information"
            },
            "get_datetime": {
                "desc": "Get current date and time",
                "example": "What time is it?"
            },
            "calculate": {
                "desc": "Evaluate mathematical expressions",
                "example": "Calculate 256 * 4 + sqrt(144)"
            },
        }
    },
    "data": {
        "name": "📊 Data Agent",
        "description": "Data file operations - JSON, CSV",
        "color": Gruvbox.AQUA,
        "tools": {
            "read_json": {
                "desc": "Read a JSON file",
                "example": "Read the config.json file from my Desktop"
            },
            "write_json": {
                "desc": "Write data to JSON file",
                "example": "Create a settings.json file on my Desktop with default configuration"
            },
            "read_csv": {
                "desc": "Read a CSV file",
                "example": "Read the data.csv file from my Documents"
            },
            "write_csv": {
                "desc": "Write data to CSV file",
                "example": "Create a contacts.csv file with sample data on my Desktop"
            },
        }
    }
}

# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_header():
    """Display header with ASCII art"""
    console.print(SYNAPSE_ASCII)
    console.print(SUBTITLE, justify="center")
    console.print()

def show_categories():
    """Display all agent categories"""
    table = Table(
        show_header=True,
        header_style=STYLE_TITLE,
        box=box.ROUNDED,
        border_style=Gruvbox.GRAY,
        title="[bold]Agent Categories[/]",
        title_style=STYLE_TITLE
    )
    
    table.add_column("Key", style=STYLE_PROMPT, width=8)
    table.add_column("Agent", style=STYLE_CATEGORY, width=20)
    table.add_column("Description", style=Style(color=Gruvbox.FG))
    table.add_column("Tools", style=STYLE_DIM, width=8)
    
    for key, cat in CATEGORIES.items():
        table.add_row(
            f"[{key}]",
            cat["name"],
            cat["description"],
            str(len(cat["tools"]))
        )
    
    console.print(table)
    console.print()

def show_tools(category_key: str):
    """Display tools for a specific category"""
    if category_key not in CATEGORIES:
        console.print(f"[{Gruvbox.RED}]Unknown category: {category_key}[/]")
        return
    
    cat = CATEGORIES[category_key]
    
    console.print(f"\n[{cat['color']}]{'═' * 60}[/]")
    console.print(f"[{cat['color']} bold]{cat['name']}[/]")
    console.print(f"[{Gruvbox.GRAY}]{cat['description']}[/]")
    console.print(f"[{cat['color']}]{'═' * 60}[/]\n")
    
    for tool_name, tool_info in cat["tools"].items():
        console.print(f"  [{Gruvbox.YELLOW}]● {tool_name}[/]")
        console.print(f"    [{Gruvbox.FG}]{tool_info['desc']}[/]")
        console.print(f"    [{Gruvbox.GRAY}]Example:[/] [{Gruvbox.GREEN}]\"{tool_info['example']}\"[/]")
        console.print()

def show_menu():
    """Display main menu options"""
    menu = Table(show_header=False, box=None, padding=(0, 2))
    menu.add_column(style=STYLE_PROMPT)
    menu.add_column(style=Style(color=Gruvbox.FG))
    
    menu.add_row("[1]", "Execute a task")
    menu.add_row("[2]", "View agent tools")
    menu.add_row("[3]", "System status")
    menu.add_row("[h]", "Help")
    menu.add_row("[q]", "Quit")
    
    console.print(Panel(menu, title="[bold]Menu[/]", border_style=Gruvbox.GRAY, box=box.ROUNDED))

def show_help():
    """Display help information"""
    help_text = f"""
[{Gruvbox.ORANGE} bold]How to Use Synapse CLI[/]

[{Gruvbox.AQUA}]1. Execute Tasks[/]
   Type natural language commands describing what you want to do.
   The multi-agent system will plan and execute your request.

[{Gruvbox.AQUA}]2. Example Commands[/]
   [{Gruvbox.GREEN}]• "List files on my Desktop"[/]
   [{Gruvbox.GREEN}]• "What time is it?"[/]
   [{Gruvbox.GREEN}]• "Create a folder called Projects on my Desktop"[/]
   [{Gruvbox.GREEN}]• "Write an article about AI and save it to my Desktop"[/]
   [{Gruvbox.GREEN}]• "Fetch https://example.com and summarize it"[/]

[{Gruvbox.AQUA}]3. Multi-Agent Flow[/]
   [{Gruvbox.GRAY}]Your request → Interaction Agent → Planner Agent → Orchestrator → Worker Agents → Result[/]

[{Gruvbox.AQUA}]4. Tips[/]
   • Use full paths or relative terms like "my Desktop", "my Documents"
   • For file content, use quotes: 'with content "Hello World"'
   • Complex tasks are automatically broken into steps
"""
    console.print(Panel(help_text, title="[bold]Help[/]", border_style=Gruvbox.GRAY, box=box.ROUNDED))

def show_status(synapse):
    """Display system status"""
    status = synapse.get_status()
    
    console.print(f"\n[{Gruvbox.ORANGE} bold]System Status[/]\n")
    
    # Agents table
    agent_table = Table(
        show_header=True,
        header_style=STYLE_TITLE,
        box=box.ROUNDED,
        border_style=Gruvbox.GRAY
    )
    agent_table.add_column("Agent", style=STYLE_CATEGORY)
    agent_table.add_column("Status", style=STYLE_SUCCESS)
    agent_table.add_column("Tools", style=STYLE_INFO)
    
    for agent in status["agents"]:
        status_icon = f"[{Gruvbox.GREEN}]●[/]" if agent["running"] else f"[{Gruvbox.RED}]●[/]"
        agent_table.add_row(
            agent["name"],
            status_icon + (" Running" if agent["running"] else " Stopped"),
            str(len(agent["tools"]))
        )
    
    console.print(agent_table)
    
    # MCP stats
    mcp = status["mcp"]
    console.print(f"\n[{Gruvbox.AQUA}]MCP Server:[/] {mcp['tools_registered']} tools | {mcp['total_executions']} executions")
    console.print(f"[{Gruvbox.AQUA}]A2A Bus:[/] {status['bus']['message_count']} messages\n")

def display_result(result: dict):
    """Display execution result in a nice format"""
    exec_result = result.get("stages", {}).get("execution", {})
    tasks_completed = exec_result.get("tasks_completed", 0)
    tasks_failed = exec_result.get("tasks_failed", 0)
    tasks_total = exec_result.get("tasks_total", 0)
    
    # Status
    if result.get("success"):
        if tasks_failed == 0:
            console.print(f"\n[{Gruvbox.GREEN}]✓ All {tasks_total} tasks completed successfully![/]\n")
        else:
            console.print(f"\n[{Gruvbox.YELLOW}]⚠ Completed with issues: {tasks_completed}/{tasks_total} tasks succeeded[/]\n")
    else:
        console.print(f"\n[{Gruvbox.RED}]✗ Failed: {tasks_failed}/{tasks_total} tasks failed[/]\n")
    
    # Task breakdown
    task_states = exec_result.get("task_states", {})
    if task_states:
        console.print(f"[{Gruvbox.GRAY}]Task Execution:[/]")
        for task_id, state in task_states.items():
            if state["status"] == "completed":
                console.print(f"  [{Gruvbox.GREEN}]✓[/] {task_id}: Completed")
            else:
                console.print(f"  [{Gruvbox.RED}]✗[/] {task_id}: {state.get('error', 'Failed')}")
        console.print()
    
    # Display outputs
    final = result.get("final_output", {})
    all_outputs = final.get("all_outputs", [])
    
    for output in all_outputs:
        task_type = output.get("type", "")
        content = output.get("content", "")
        
        if task_type == "list_directory" and isinstance(content, dict):
            items = content.get("items", [])
            directory = content.get("directory", "")
            
            console.print(f"[{Gruvbox.AQUA}]📁 Contents of {directory}[/] ({len(items)} items)\n")
            
            table = Table(box=box.SIMPLE, border_style=Gruvbox.GRAY)
            table.add_column("Name", style=Style(color=Gruvbox.FG))
            table.add_column("Type", style=STYLE_DIM, width=8)
            table.add_column("Size", style=STYLE_DIM, width=12)
            
            for item in items[:30]:
                icon = "📁" if item.get("type") == "folder" else "📄"
                table.add_row(
                    f"{icon} {item.get('name', '')}",
                    item.get("type", ""),
                    item.get("size", "-")
                )
            
            console.print(table)
            if len(items) > 30:
                console.print(f"[{Gruvbox.GRAY}]... and {len(items) - 30} more items[/]")
        
        elif task_type == "get_system_info" and isinstance(content, dict):
            console.print(f"[{Gruvbox.AQUA}]💻 System Information[/]\n")
            for key, value in content.items():
                console.print(f"  [{Gruvbox.YELLOW}]{key}:[/] {value}")
        
        elif task_type == "get_datetime":
            if isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA}]🕐 Current Time:[/] {content.get('datetime', content)}")
            else:
                console.print(f"[{Gruvbox.AQUA}]🕐 Current Time:[/] {content}")
        
        elif task_type == "calculate":
            if isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA}]🔢 Calculation:[/] {content.get('expression', '')} = [{Gruvbox.GREEN}]{content.get('result', '')}[/]")
            else:
                console.print(f"[{Gruvbox.AQUA}]🔢 Result:[/] {content}")
        
        elif task_type == "generate_text":
            console.print(f"[{Gruvbox.AQUA}]📝 Generated Content:[/]\n")
            console.print(Panel(str(content), border_style=Gruvbox.GRAY, box=box.ROUNDED))
        
        elif task_type in ["write_file", "create_file"]:
            if isinstance(content, dict):
                console.print(f"[{Gruvbox.GREEN}]✓ File saved:[/] {content.get('filepath', '')}")
            else:
                console.print(f"[{Gruvbox.GREEN}]✓ File saved:[/] {content}")
        
        elif task_type == "read_file":
            console.print(f"[{Gruvbox.AQUA}]📄 File Content:[/]\n")
            console.print(Panel(str(content)[:2000], border_style=Gruvbox.GRAY, box=box.ROUNDED))
        
        elif task_type == "fetch_webpage":
            if isinstance(content, dict):
                console.print(f"[{Gruvbox.AQUA}]🌐 Webpage:[/] {content.get('title', '')}")
                console.print(f"[{Gruvbox.GRAY}]URL: {content.get('url', '')}[/]")
                console.print(Panel(str(content.get('content', ''))[:1500], border_style=Gruvbox.GRAY, box=box.ROUNDED))
        
        elif task_type in ["create_folder", "move_file", "copy_file", "delete_file", "delete_folder"]:
            console.print(f"[{Gruvbox.GREEN}]✓ {task_type.replace('_', ' ').title()} completed[/]")
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
# MAIN CLI
# ============================================================

def run_cli():
    """Main CLI loop"""
    clear_screen()
    show_header()
    
    # Check API key
    if not os.environ.get("GROQ_API_KEY"):
        console.print(f"[{Gruvbox.RED}]⚠ GROQ_API_KEY not set![/]")
        console.print(f"[{Gruvbox.GRAY}]Set it with:[/]")
        if os.name == 'nt':
            console.print(f'[{Gruvbox.GREEN}]$env:GROQ_API_KEY="your-key-here"[/]')
        else:
            console.print(f'[{Gruvbox.GREEN}]export GROQ_API_KEY="your-key-here"[/]')
        console.print(f"\n[{Gruvbox.GRAY}]Get a free key at: https://console.groq.com[/]\n")
        return
    
    # Initialize Synapse
    console.print(f"[{Gruvbox.GRAY}]Initializing Synapse...[/]")
    
    try:
        from synapse import Synapse
        synapse = Synapse()
        console.print(f"[{Gruvbox.GREEN}]✓ System ready![/]\n")
    except Exception as e:
        console.print(f"[{Gruvbox.RED}]Failed to initialize: {e}[/]")
        return
    
    show_categories()
    show_menu()
    
    # Main loop
    while True:
        try:
            console.print()
            choice = Prompt.ask(
                f"[{Gruvbox.PURPLE}]synapse[/]",
                default=""
            ).strip().lower()
            
            if not choice:
                continue
            
            elif choice == 'q' or choice == 'quit' or choice == 'exit':
                console.print(f"\n[{Gruvbox.ORANGE}]Goodbye! 👋[/]\n")
                synapse.shutdown()
                break
            
            elif choice == '1':
                # Execute task
                console.print(f"\n[{Gruvbox.AQUA}]Enter your request (or 'back' to return):[/]")
                task = Prompt.ask(f"[{Gruvbox.GREEN}]>[/]").strip()
                
                if task.lower() == 'back':
                    continue
                
                if task:
                    with Progress(
                        SpinnerColumn(style=Style(color=Gruvbox.ORANGE)),
                        TextColumn(f"[{Gruvbox.GRAY}]Processing through agents...[/]"),
                        console=console
                    ) as progress:
                        progress.add_task("", total=None)
                        result = synapse.process(task)
                    
                    display_result(result)
            
            elif choice == '2':
                # View tools
                console.print(f"\n[{Gruvbox.AQUA}]Select category:[/] {', '.join(CATEGORIES.keys())}")
                cat = Prompt.ask(f"[{Gruvbox.GREEN}]category[/]").strip().lower()
                
                if cat in CATEGORIES:
                    show_tools(cat)
                elif cat != 'back':
                    console.print(f"[{Gruvbox.RED}]Unknown category. Options: {', '.join(CATEGORIES.keys())}[/]")
            
            elif choice == '3':
                # System status
                show_status(synapse)
            
            elif choice == 'h' or choice == 'help':
                show_help()
            
            elif choice == 'clear' or choice == 'cls':
                clear_screen()
                show_header()
                show_categories()
                show_menu()
            
            elif choice == 'menu':
                show_menu()
            
            else:
                # Treat as direct task input
                with Progress(
                    SpinnerColumn(style=Style(color=Gruvbox.ORANGE)),
                    TextColumn(f"[{Gruvbox.GRAY}]Processing through agents...[/]"),
                    console=console
                ) as progress:
                    progress.add_task("", total=None)
                    result = synapse.process(choice)
                
                display_result(result)
                
        except KeyboardInterrupt:
            console.print(f"\n[{Gruvbox.ORANGE}]Interrupted. Type 'q' to quit.[/]")
        except Exception as e:
            console.print(f"[{Gruvbox.RED}]Error: {e}[/]")

if __name__ == "__main__":
    run_cli()
