#!/usr/bin/env python3
"""
Synapse CLI
Multi-Agent AI System Command Line Interface
Gruvbox Dark Theme
"""
import os
import sys
import json
import time
import threading
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markup import escape as rich_escape
from rich.progress import Progress, SpinnerColumn, TextColumn

from synapse import Synapse, create_synapse


# ============================================================
# GRUVBOX THEME
# ============================================================

COLORS = {
    "orange": "#fe8019",
    "aqua": "#8ec07c",
    "purple": "#d3869b",
    "yellow": "#fabd2f",
    "green": "#b8bb26",
    "blue": "#83a598",
    "red": "#fb4934",
    "gray": "#928374",
    "fg": "#ebdbb2",
    "bg": "#282828"
}

console = Console()


# ============================================================
# GLOBALS
# ============================================================

WORKING_DIR = os.getcwd()
synapse: Synapse = None
last_result = None
last_log = None
task_interrupted = False
test_results = []


# ============================================================
# TEST CASES
# ============================================================

TEST_CASES = [
    {
        "id": "T01",
        "name": "System - Get DateTime",
        "prompt": "what time is it",
        "category": "system",
        "expects": "datetime"
    },
    {
        "id": "T02", 
        "name": "System - Get System Info",
        "prompt": "get system information",
        "category": "system",
        "expects": "system_info"
    },
    {
        "id": "T03",
        "name": "System - Calculator",
        "prompt": "calculate 25 * 4 + 100",
        "category": "system",
        "expects": "result"
    },
    {
        "id": "T04",
        "name": "Content - Generate Haiku",
        "prompt": "write a haiku about coding",
        "category": "content",
        "expects": "content"
    },
    {
        "id": "T05",
        "name": "Content - Greeting Response",
        "prompt": "hello how are you",
        "category": "content",
        "expects": "content"
    },
    {
        "id": "T06",
        "name": "File - Create Simple File",
        "prompt": "create a file called synapse_test.txt with content: Test successful!",
        "category": "file",
        "expects": "filepath"
    },
    {
        "id": "T07",
        "name": "File - List Directory",
        "prompt": "list all files in the current directory",
        "category": "file",
        "expects": "items"
    },
    {
        "id": "T08",
        "name": "File - Create Folder",
        "prompt": "create a folder called SynapseTestFolder",
        "category": "file",
        "expects": "path"
    },
    {
        "id": "T09",
        "name": "Chain - Generate and Save",
        "prompt": "write a short poem about AI and save it to ai_poem.txt",
        "category": "chain",
        "expects": "filepath"
    },
    {
        "id": "T10",
        "name": "Web - Fetch Webpage",
        "prompt": "fetch https://example.com",
        "category": "web",
        "expects": "content"
    },
]


# ============================================================
# HELPERS
# ============================================================

def safe_text(content) -> str:
    """Escape text for Rich markup safety"""
    return rich_escape(str(content)) if content else ""


def clear_screen():
    """Clear the terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print Synapse header"""
    ascii_art = """
███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗  
╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝  
███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████╗
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝
    """
    console.print(ascii_art, style=f"bold {COLORS['orange']}")
    console.print("Multi-Agent AI System with Parallel DAG Execution", style=COLORS['gray'])
    console.print(f"[{COLORS['aqua']}]Groq[/] + [{COLORS['purple']}]Gemini[/] | Parallel Tasks | Persistent Memory | A2A Server\n")


def get_agent_table():
    """Get agent categories table"""
    table = Table(
        show_header=True,
        header_style=f"bold {COLORS['aqua']}",
        border_style=COLORS['gray'],
        title="Agent Categories",
        title_style=f"bold {COLORS['orange']}"
    )
    table.add_column("Agent", style=COLORS['aqua'])
    table.add_column("Capabilities", style=COLORS['fg'])
    
    table.add_row("[D] Interaction", "Interprets requests, formats responses")
    table.add_row("[D] Planner", "Creates DAG execution plans")
    table.add_row("[D] Orchestrator", "Parallel task execution")
    table.add_row("[F] File Agent", "File operations, JSON/CSV")
    table.add_row("[F] Content Agent", "Text generation, summarization")
    table.add_row("[F] Web Agent", "Web fetching, downloads")
    table.add_row("[F] System Agent", "System info, commands, math")
    
    return table


def get_menu_table(server_running: bool = False):
    """Get actions menu table with split columns"""
    table = Table(
        show_header=True,
        header_style=f"bold {COLORS['purple']}",
        border_style=COLORS['gray'],
        title="Actions Menu",
        title_style=f"bold {COLORS['orange']}"
    )
    table.add_column("Key", style=COLORS['purple'], width=5)
    table.add_column("Command", style=COLORS['yellow'], width=10)
    table.add_column("Description", style=COLORS['fg'])
    
    table.add_row("1", "tools", "View agent tools")
    table.add_row("2", "status", "System status")
    table.add_row("3", "llm", "LLM Pool status")
    table.add_row("4", "memory", "Memory search")
    table.add_row("5", "log", "View last execution log")
    table.add_row("6", "raw", "View raw output")
    
    server_status = f"[{COLORS['green']}]running[/]" if server_running else f"[{COLORS['gray']}]stopped[/]"
    table.add_row("7", "server", f"Toggle A2A Server ({server_status})")
    
    table.add_row("8", "test", "Run system tests")
    table.add_row("9", "results", "View test results")
    
    table.add_row("h", "help", "Show help")
    table.add_row("c", "clear", "Clear screen")
    table.add_row("q", "quit", "Exit Synapse")
    
    return table


def print_main_ui():
    """Print main UI with agent categories and menu"""
    global synapse
    console.print(get_agent_table())
    console.print()
    server_running = synapse.is_server_running() if synapse else False
    console.print(get_menu_table(server_running))
    console.print()


# ============================================================
# TESTING SYSTEM
# ============================================================

def run_single_test(test_case: dict) -> dict:
    """Run a single test case and return result"""
    global synapse
    
    test_id = test_case["id"]
    test_name = test_case["name"]
    prompt = test_case["prompt"]
    expects = test_case["expects"]
    
    start_time = time.time()
    
    try:
        result = synapse.process(prompt)
        elapsed = time.time() - start_time
        
        success = result.get("success", False)
        tasks_completed = result.get("tasks_completed", 0)
        tasks_total = result.get("tasks_total", 0)
        
        # Check if expected output type is present
        found_expected = False
        if success:
            all_outputs = result.get("all_outputs", [])
            task_states = result.get("task_states", {})
            
            for output in all_outputs:
                content = output.get("content", {})
                if isinstance(content, dict):
                    if expects in content or "content" in content or "result" in content:
                        found_expected = True
                        break
                elif content:
                    found_expected = True
                    break
            
            for state in task_states.values():
                if state.get("status") == "completed":
                    task_result = state.get("result", {})
                    if isinstance(task_result, dict):
                        if expects in task_result or task_result.get("success"):
                            found_expected = True
                            break
        
        return {
            "id": test_id,
            "name": test_name,
            "prompt": prompt,
            "success": success,
            "found_expected": found_expected,
            "tasks": f"{tasks_completed}/{tasks_total}",
            "time_ms": round(elapsed * 1000),
            "error": result.get("error") if not success else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "id": test_id,
            "name": test_name,
            "prompt": prompt,
            "success": False,
            "found_expected": False,
            "tasks": "0/0",
            "time_ms": round(elapsed * 1000),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def run_tests():
    """Run all tests interactively"""
    global test_results, synapse
    
    clear_screen()
    print_header()
    
    console.print(f"[bold {COLORS['orange']}]System Tests[/]\n")
    console.print(f"[{COLORS['gray']}]This will run {len(TEST_CASES)} tests to verify system functionality.[/]")
    console.print(f"[{COLORS['gray']}]Press Enter to start, or 'q' to cancel.[/]\n")
    
    try:
        choice = console.input(f"[{COLORS['purple']}]> [/]").strip().lower()
        if choice == 'q':
            return
    except KeyboardInterrupt:
        return
    
    test_results = []
    passed = 0
    failed = 0
    
    console.print()
    
    for i, test_case in enumerate(TEST_CASES):
        test_id = test_case["id"]
        test_name = test_case["name"]
        
        # Show progress
        console.print(f"[{COLORS['aqua']}][{i+1}/{len(TEST_CASES)}][/] {test_id}: {test_name}...", end=" ")
        
        try:
            result = run_single_test(test_case)
            test_results.append(result)
            
            if result["success"]:
                passed += 1
                console.print(f"[{COLORS['green']}]PASS[/] ({result['time_ms']}ms)")
            else:
                failed += 1
                error_msg = result.get("error", "Unknown error")[:50]
                console.print(f"[{COLORS['red']}]FAIL[/] - {safe_text(error_msg)}")
        
        except KeyboardInterrupt:
            console.print(f"[{COLORS['yellow']}]CANCELLED[/]")
            break
    
    # Summary
    console.print()
    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    summary_color = COLORS['green'] if pass_rate >= 80 else COLORS['yellow'] if pass_rate >= 50 else COLORS['red']
    
    console.print(Panel(
        f"[bold]Tests: {total}[/]  |  [{COLORS['green']}]Passed: {passed}[/]  |  [{COLORS['red']}]Failed: {failed}[/]  |  Pass Rate: [{summary_color}]{pass_rate:.0f}%[/]",
        title=f"[bold {COLORS['orange']}]Test Summary[/]",
        border_style=COLORS['gray']
    ))
    
    console.print(f"\n[{COLORS['gray']}]Type 'results' or '9' to view detailed results.[/]")
    console.print(f"[{COLORS['gray']}]Press Enter to continue...[/]")
    
    try:
        input()
    except:
        pass


def view_test_results():
    """View detailed test results"""
    global test_results
    
    clear_screen()
    print_header()
    
    if not test_results:
        console.print(f"[{COLORS['gray']}]No test results available. Run tests first (option 8).[/]")
        console.print(f"\n[{COLORS['gray']}]Press Enter to continue...[/]")
        input()
        return
    
    console.print(f"[bold {COLORS['orange']}]Test Results[/]\n")
    
    # Results table
    table = Table(
        show_header=True,
        header_style=f"bold {COLORS['aqua']}",
        border_style=COLORS['gray']
    )
    table.add_column("ID", style=COLORS['purple'], width=4)
    table.add_column("Test Name", style=COLORS['fg'], width=25)
    table.add_column("Status", width=8)
    table.add_column("Tasks", style=COLORS['gray'], width=6)
    table.add_column("Time", style=COLORS['gray'], width=8)
    table.add_column("Error", style=COLORS['red'], width=30)
    
    for result in test_results:
        status = f"[{COLORS['green']}]PASS[/]" if result["success"] else f"[{COLORS['red']}]FAIL[/]"
        error = safe_text(result.get("error", "")[:30]) if result.get("error") else ""
        
        table.add_row(
            result["id"],
            result["name"],
            status,
            result["tasks"],
            f"{result['time_ms']}ms",
            error
        )
    
    console.print(table)
    
    # Summary stats
    passed = sum(1 for r in test_results if r["success"])
    failed = len(test_results) - passed
    total_time = sum(r["time_ms"] for r in test_results)
    avg_time = total_time / len(test_results) if test_results else 0
    
    console.print(f"\n[{COLORS['aqua']}]Statistics:[/]")
    console.print(f"  Total tests: {len(test_results)}")
    console.print(f"  Passed: [{COLORS['green']}]{passed}[/]")
    console.print(f"  Failed: [{COLORS['red']}]{failed}[/]")
    console.print(f"  Total time: {total_time}ms")
    console.print(f"  Avg time: {avg_time:.0f}ms")
    
    if test_results:
        console.print(f"  Last run: {test_results[0]['timestamp'][:19]}")
    
    console.print(f"\n[{COLORS['gray']}]Press Enter to continue...[/]")
    
    try:
        input()
    except:
        pass


# ============================================================
# RESULT DISPLAY
# ============================================================

def display_result(result: dict, show_full: bool = False):
    """Display execution result"""
    global last_result, last_log
    last_result = result
    last_log = result
    
    success = result.get("success", False)
    tasks_completed = result.get("tasks_completed", 0)
    tasks_failed = result.get("tasks_failed", 0)
    tasks_total = result.get("tasks_total", 0)
    parallel = result.get("parallel_execution", False)
    
    # Status panel
    if success:
        status_text = f"+ Completed {tasks_completed} tasks successfully"
        if parallel:
            status_text += " (parallel)"
        panel = Panel(
            Text(status_text, style=f"bold {COLORS['green']}"),
            border_style=COLORS['green']
        )
    else:
        error = result.get("error", "Unknown error")
        status_text = f"x Failed: {safe_text(error)}"
        panel = Panel(
            Text(status_text, style=f"bold {COLORS['red']}"),
            border_style=COLORS['red']
        )
    
    console.print(panel)
    
    # Task descriptions
    if tasks_total > 0:
        console.print()
        task_states = result.get("task_states", {})
        plan = result.get("plan", {})
        tasks = plan.get("tasks", [])
        
        for task in tasks:
            task_id = task.get("task_id", "?")
            desc = task.get("description", task.get("tool", ""))
            state = task_states.get(task_id, {})
            status = state.get("status", "unknown")
            
            if status == "completed":
                icon = "+"
                style = COLORS['green']
            elif status == "failed":
                icon = "x"
                style = COLORS['red']
            elif status == "skipped":
                icon = "-"
                style = COLORS['gray']
            else:
                icon = "*"
                style = COLORS['yellow']
            
            console.print(f"  [{style}]{icon}[/] {task_id} - {safe_text(desc)}")
    
    # Generated content
    all_outputs = result.get("all_outputs", [])
    for output in all_outputs:
        content = output.get("content")
        output_type = output.get("type", "")
        
        if content:
            console.print()
            console.print("Generated Content", style=f"bold {COLORS['aqua']}")
            
            if isinstance(content, dict):
                display_content = content.get("content", content.get("result", json.dumps(content, indent=2)))
            else:
                display_content = str(content)
            
            # Truncate if too long
            if not show_full and len(display_content) > 500:
                display_content = display_content[:500] + "\n... (type 'more' to see full output)"
            
            console.print(Panel(
                Text(display_content),
                border_style=COLORS['gray']
            ))
    
    # File operations
    for task_id, state in result.get("task_states", {}).items():
        if state.get("status") == "completed":
            task_result = state.get("result", {})
            if isinstance(task_result, dict):
                filepath = task_result.get("filepath") or task_result.get("path")
                if filepath:
                    console.print(f"[{COLORS['green']}]+ File saved:[/] {safe_text(filepath)}")


def show_log():
    """Show last execution log"""
    global last_log
    if not last_log:
        console.print(f"[{COLORS['gray']}]No execution log available[/]")
        return
    
    console.print(f"\n[bold {COLORS['orange']}]Last Execution Log[/]\n")
    
    # Plan info
    plan = last_log.get("plan", {})
    if plan:
        console.print(f"[{COLORS['aqua']}]Plan ID:[/] {plan.get('plan_id', 'N/A')}")
        console.print(f"[{COLORS['aqua']}]Description:[/] {plan.get('description', 'N/A')}")
    
    # Task details
    task_states = last_log.get("task_states", {})
    if task_states:
        console.print(f"\n[{COLORS['aqua']}]Task Details:[/]")
        for task_id, state in task_states.items():
            status = state.get("status", "unknown")
            status_color = COLORS['green'] if status == "completed" else COLORS['red']
            console.print(f"  [{status_color}]{task_id}[/]: {status}")
            
            result = state.get("result", {})
            if isinstance(result, dict):
                if result.get("error"):
                    console.print(f"    Error: {safe_text(result['error'])}")
                elif result.get("filepath"):
                    console.print(f"    File: {result['filepath']}")
            
            error = state.get("error")
            if error:
                console.print(f"    Error: {safe_text(error)}")
    
    # Stats
    console.print(f"\n[{COLORS['aqua']}]Summary:[/]")
    console.print(f"  Tasks: {last_log.get('tasks_completed', 0)}/{last_log.get('tasks_total', 0)} completed")
    console.print(f"  Parallel: {last_log.get('parallel_execution', False)}")


def show_raw():
    """Show raw output"""
    global last_result
    if not last_result:
        console.print(f"[{COLORS['gray']}]No result available[/]")
        return
    
    console.print(f"\n[bold {COLORS['orange']}]Raw Output[/]\n")
    console.print(Panel(
        Text(json.dumps(last_result, indent=2, default=str)),
        border_style=COLORS['gray']
    ))


# ============================================================
# VIEW TOOLS
# ============================================================

def view_tools():
    """View available tools"""
    global synapse
    clear_screen()
    print_header()
    
    tools = synapse.get_tools()
    
    # Group by category
    by_category = {}
    for tool in tools:
        cat = tool.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool)
    
    console.print(f"[bold {COLORS['orange']}]Available Tools[/]\n")
    
    for category, cat_tools in sorted(by_category.items()):
        console.print(f"[{COLORS['aqua']}]{category.upper()}[/]")
        
        table = Table(show_header=True, header_style=COLORS['yellow'], border_style=COLORS['gray'])
        table.add_column("Tool", style=COLORS['yellow'])
        table.add_column("Arguments", style=COLORS['purple'])
        table.add_column("Description", style=COLORS['fg'])
        
        for tool in cat_tools:
            args = ", ".join(tool.get("required", []))
            table.add_row(tool["name"], args, tool["description"])
        
        console.print(table)
        console.print()
    
    console.print(f"[{COLORS['gray']}]Press Enter to continue...[/]")
    input()


# ============================================================
# SYSTEM STATUS
# ============================================================

def system_status():
    """Show system status"""
    global synapse
    clear_screen()
    print_header()
    
    status = synapse.get_status()
    
    console.print(f"[bold {COLORS['orange']}]System Status[/]\n")
    
    # General
    table = Table(show_header=False, border_style=COLORS['gray'])
    table.add_column("Property", style=COLORS['aqua'])
    table.add_column("Value", style=COLORS['fg'])
    
    table.add_row("Initialized", str(status.get("initialized", False)))
    table.add_row("Working Directory", safe_text(status.get("working_dir", "")))
    table.add_row("Parallel Execution", str(status.get("parallel_enabled", False)))
    table.add_row("Max Workers", str(status.get("max_workers", 0)))
    
    console.print(table)
    
    # MCP
    mcp = status.get("mcp", {})
    if mcp:
        console.print(f"\n[{COLORS['aqua']}]MCP Server[/]")
        console.print(f"  Tools registered: {mcp.get('tools_registered', 0)}")
        console.print(f"  Total executions: {mcp.get('total_executions', 0)}")
    
    # Memory
    mem = status.get("memory", {})
    if mem:
        console.print(f"\n[{COLORS['aqua']}]Persistent Memory[/]")
        console.print(f"  Entries: {mem.get('total_entries', 0)}/{mem.get('max_entries', 0)}")
    
    # A2A Bus
    bus = status.get("a2a_bus", {})
    if bus:
        console.print(f"\n[{COLORS['aqua']}]A2A Message Bus[/]")
        console.print(f"  Agents: {bus.get('agent_count', 0)}")
        console.print(f"  Messages sent: {bus.get('messages_sent', 0)}")
    
    # A2A Server
    server = status.get("a2a_server", {})
    if server:
        console.print(f"\n[{COLORS['aqua']}]A2A HTTP Server[/]")
        running = server.get("running", False)
        console.print(f"  Status: [{'green' if running else 'red'}]{'Running' if running else 'Stopped'}[/]")
        if running:
            console.print(f"  URL: {server.get('url', 'N/A')}")
    
    console.print(f"\n[{COLORS['gray']}]Press Enter to continue...[/]")
    input()


# ============================================================
# LLM POOL STATUS
# ============================================================

def llm_status():
    """Show LLM pool status"""
    global synapse
    clear_screen()
    print_header()
    
    if not synapse.llm_pool:
        console.print("LLM Pool not initialized", style=COLORS['red'])
        input()
        return
    
    stats = synapse.llm_pool.get_stats()
    
    console.print(f"[bold {COLORS['orange']}]LLM Pool Status[/]\n")
    
    # Pool stats
    pool = stats.get("pool_stats", {})
    console.print(f"[{COLORS['aqua']}]Pool Statistics[/]")
    console.print(f"  Total requests: {pool.get('total_requests', 0)}")
    console.print(f"  Successful: {pool.get('successful_requests', 0)}")
    console.print(f"  Failed: {pool.get('failed_requests', 0)}")
    console.print(f"  Fallbacks used: {pool.get('fallback_count', 0)}")
    console.print(f"  Priority order: {stats.get('priority_order', [])}")
    
    # Per-LLM stats
    console.print(f"\n[{COLORS['aqua']}]LLM Providers[/]")
    
    llm_details = stats.get("llm_details", {})
    if not llm_details:
        console.print(f"  [{COLORS['gray']}]No LLMs registered[/]")
    
    for name, details in llm_details.items():
        status_color = COLORS['green'] if details.get("status") == "available" else COLORS['red']
        console.print(f"\n  [{COLORS['yellow']}]{name}[/]")
        console.print(f"    Model: {details.get('model', 'N/A')}")
        console.print(f"    Status: [{status_color}]{details.get('status', 'unknown')}[/]")
        console.print(f"    Requests: {details.get('request_count', 0)}")
        console.print(f"    Errors: {details.get('error_count', 0)}")
        console.print(f"    Avg latency: {details.get('avg_latency_ms', 0):.0f}ms")
        if details.get("last_error"):
            console.print(f"    Last error: {safe_text(details['last_error'][:80])}")
    
    console.print(f"\n[{COLORS['gray']}]Press Enter to continue...[/]")
    input()


# ============================================================
# MEMORY SEARCH
# ============================================================

def memory_search():
    """Search memory"""
    global synapse
    clear_screen()
    print_header()
    
    console.print(f"[bold {COLORS['orange']}]Memory Search[/]\n")
    console.print(f"[{COLORS['gray']}]Enter search query or 'back' to return[/]\n")
    
    while True:
        try:
            query = console.input(f"[{COLORS['purple']}]Search> [/]").strip()
        except KeyboardInterrupt:
            console.print()
            break
        
        if not query or query.lower() in ['back', 'exit', 'q', 'quit']:
            break
        
        # Search persistent memory
        results = synapse.search_memory(query, limit=5)
        
        if results:
            console.print(f"\n[{COLORS['aqua']}]Found {len(results)} results:[/]\n")
            for r in results:
                console.print(f"  * {safe_text(r.content[:100])}...")
                if r.metadata:
                    console.print(f"    [{COLORS['gray']}]{r.metadata}[/]")
        else:
            console.print(f"[{COLORS['gray']}]No results found[/]")
        
        console.print()


# ============================================================
# A2A SERVER CONTROL
# ============================================================

def toggle_server():
    """Toggle A2A server on/off"""
    global synapse
    
    if synapse.is_server_running():
        console.print(f"[{COLORS['yellow']}]Stopping A2A Server...[/]")
        
        # Stop in a separate thread to avoid blocking
        def stop_server():
            synapse.stop_server()
        
        stop_thread = threading.Thread(target=stop_server, daemon=True)
        stop_thread.start()
        stop_thread.join(timeout=2.0)
        
        time.sleep(0.3)
        console.print(f"[{COLORS['yellow']}]A2A Server stopped[/]")
    else:
        if synapse.start_server():
            url = synapse.get_server_url()
            console.print(f"[{COLORS['green']}]A2A Server started at {url}[/]")
            console.print(f"\n[{COLORS['aqua']}]PowerShell Commands:[/]")
            console.print(f"  # Health check")
            console.print(f"  Invoke-RestMethod -Uri '{url}/health'")
            console.print(f"\n  # Get status")
            console.print(f"  Invoke-RestMethod -Uri '{url}/status'")
            console.print(f"\n  # Submit task")
            console.print(f"  Invoke-RestMethod -Uri '{url}/task' -Method Post -ContentType 'application/json' -Body '{{\"task\": \"what time is it\"}}'")
        else:
            console.print(f"[{COLORS['red']}]Failed to start A2A Server[/]")
    
    console.print()
    # Show updated menu with server status
    console.print(get_menu_table(synapse.is_server_running()))
    console.print()


# ============================================================
# HELP
# ============================================================

def show_help():
    """Show help"""
    clear_screen()
    print_header()
    
    # Overview
    overview = """[bold]Synapse[/] is a multi-agent AI system with:
  * Multi-LLM support (Groq + Gemini) with automatic fallback
  * Parallel DAG execution for complex tasks
  * Persistent memory for context retention
  * A2A HTTP server for external integration

[bold]Task Examples:[/]
  write a poem about the ocean and save it to poem.txt
  get system info and save to Desktop/sysinfo.txt
  create folder Projects on Desktop with readme.txt inside
  fetch https://example.com and summarize it
  list all files in Documents
  what time is it
  calculate 25 * 4 + 100

[bold]Tips:[/]
  * Press Ctrl+C during task execution to cancel
  * Type 'more' to see full output after a task
  * Type 'log' to see detailed execution log
  * Type 'test' to run system tests"""
    
    console.print(Panel(
        overview,
        title=f"[bold {COLORS['orange']}]Synapse Help[/]",
        border_style=COLORS['gray']
    ))
    
    console.print()
    
    # Agent categories
    console.print(get_agent_table())
    
    console.print()
    
    # Commands menu
    server_running = synapse.is_server_running() if synapse else False
    console.print(get_menu_table(server_running))
    
    console.print(f"\n[{COLORS['gray']}]Press Enter to continue...[/]")
    input()


# ============================================================
# MAIN TASK LOOP
# ============================================================

def process_command(cmd: str) -> bool:
    """
    Process a command. Returns True if should continue in task mode, False to exit.
    """
    global synapse, last_result, task_interrupted
    
    cmd_lower = cmd.lower().strip()
    
    # Exit commands
    if cmd_lower in ['quit', 'exit', 'q']:
        return False
    
    # Clear screen
    if cmd_lower in ['clear', 'cls', 'c']:
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # Help
    if cmd_lower in ['help', 'h', '?']:
        show_help()
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # Tools (1 or tools)
    if cmd_lower in ['1', 'tools']:
        view_tools()
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # Status (2 or status)
    if cmd_lower in ['2', 'status']:
        system_status()
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # LLM status (3 or llm)
    if cmd_lower in ['3', 'llm']:
        llm_status()
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # Memory (4 or memory)
    if cmd_lower in ['4', 'memory']:
        memory_search()
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # Log (5 or log)
    if cmd_lower in ['5', 'log']:
        show_log()
        return True
    
    # Raw output (6 or raw)
    if cmd_lower in ['6', 'raw']:
        show_raw()
        return True
    
    # Server toggle (7 or server)
    if cmd_lower in ['7', 'server']:
        toggle_server()
        return True
    
    # Test (8 or test)
    if cmd_lower in ['8', 'test']:
        run_tests()
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # View test results (9 or results)
    if cmd_lower in ['9', 'results']:
        view_test_results()
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # More (full output)
    if cmd_lower == 'more':
        if last_result:
            display_result(last_result, show_full=True)
        else:
            console.print(f"[{COLORS['gray']}]No previous result[/]")
        return True
    
    # Menu (just show UI again)
    if cmd_lower == 'menu':
        clear_screen()
        print_header()
        print_main_ui()
        return True
    
    # Empty command
    if not cmd:
        return True
    
    # Otherwise, treat as a task
    console.print()
    task_interrupted = False
    
    try:
        with console.status(f"[{COLORS['aqua']}]Processing... (Ctrl+C to cancel)", spinner="dots"):
            result = synapse.process(cmd)
        
        if not task_interrupted:
            console.print()
            display_result(result)
            console.print()
    
    except KeyboardInterrupt:
        task_interrupted = True
        console.print(f"\n[{COLORS['yellow']}]Task cancelled[/]\n")
    
    return True


def main():
    """Main entry point"""
    global synapse, WORKING_DIR
    
    clear_screen()
    print_header()
    
    # Get working directory
    WORKING_DIR = os.getcwd()
    
    # Initialize Synapse (silently)
    try:
        synapse = Synapse(working_dir=WORKING_DIR, parallel=True, max_workers=4)
        
        with console.status(f"[{COLORS['aqua']}]Loading...", spinner="dots"):
            if not synapse.initialize():
                console.print(f"[{COLORS['red']}]Failed to initialize[/]")
                console.print(f"[{COLORS['gray']}]Make sure GROQ_API_KEY or GEMINI_API_KEY is set in .env[/]")
                return
        
    except Exception as e:
        console.print(f"[{COLORS['red']}]Error: {safe_text(str(e))}[/]")
        return
    
    # Show main UI
    print_main_ui()
    console.print(f"[{COLORS['gray']}]Enter tasks directly, or type 'help' for commands[/]\n")
    
    # Main loop - task mode by default
    while True:
        try:
            user_input = console.input(f"[{COLORS['purple']}]Task> [/]").strip()
            
            if not process_command(user_input):
                break
            
        except KeyboardInterrupt:
            # Ctrl+C at prompt - just show new line, don't exit
            console.print()
            continue
        
        except EOFError:
            # Handle Ctrl+D / EOF - exit
            break
        
        except Exception as e:
            console.print(f"[{COLORS['red']}]Error: {safe_text(str(e))}[/]")
    
    # Cleanup
    console.print(f"\n[{COLORS['aqua']}]Goodbye![/]")
    if synapse:
        synapse.shutdown()


if __name__ == "__main__":
    main()
