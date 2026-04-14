"""
CLI Renderer - All terminal UI formatting and display logic.
No tool logic, no execution — purely visual.
Plain text output, no colors, no emojis, no ANSI codes.
"""
import json
import os
from typing import Any, Dict, List

CATEGORY_LABELS = {
    "ai":          "AI Generation",
    "filesystem":  "File System",
    "data_files":  "Data Files",
    "web":         "Web & HTTP",
    "database":    "Database",
    "system":      "System",
    "general":     "General",
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _hr(char="-", width=60):
    return char * width


def render_banner():
    print()
    print("  " + _hr("="))
    print("  SYNAPSE CLI")
    print("  Dynamic MCP Tool Interface")
    print("  " + _hr("="))
    print()


def render_breadcrumb(path: List[str]):
    parts = ["Home"] + path
    print("  " + " > ".join(parts))
    print()


def render_categories(categories: List[str], tool_counts: Dict[str, int]):
    print("  Select a category:")
    print()
    for i, cat in enumerate(categories, 1):
        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        count = tool_counts.get(cat, 0)
        print(f"    {i:>2})  {label}  ({count} tools)")
    print()
    print("     q) Quit    h) Help")
    print()


def render_tool_list(category: str, tools: list):
    label = CATEGORY_LABELS.get(category, category.replace("_", " ").title())
    print(f"  {label}  --  {len(tools)} tools")
    print()
    for i, tool in enumerate(tools, 1):
        print(f"    {i:>2})  {tool.name}")
        print(f"        {tool.description}")
    print()
    print("     b) Back    q) Quit")
    print()


def render_tool_detail(tool):
    print(f"  {tool.name}")
    print(f"  {tool.description}")
    print()
    print("  Type your prompt in plain english. Output auto-saves to outputs/.")
    print("  To save elsewhere: ...save to D:/docs/report.txt")
    print()
    print("     b) Back    q) Quit")
    print()


def render_param_prompt(pname: str, pinfo: Dict, is_required: bool):
    ptype = pinfo.get("type", "any")
    pdesc = pinfo.get("description", "")
    req   = "*" if is_required else "(optional, Enter to skip)"
    print(f"  {pname} <{ptype}> {req}")
    if pdesc:
        print(f"    {pdesc}")


def render_execution_start(tool_name: str, args: Dict):
    print()
    print("  " + _hr("="))
    print(f"  Executing: {tool_name}")
    if args:
        for k, v in args.items():
            display = str(v)
            if len(display) > 80:
                display = display[:77] + "..."
            print(f"    {k} = {display}")
    print("  " + _hr("="))
    print()


def render_result(result: Dict[str, Any]):
    if result.get("success"):
        print("  [OK]")
        print()
        payload = result.get("result")
        if payload is not None:
            if isinstance(payload, (dict, list)):
                formatted = json.dumps(payload, indent=2, default=str)
                for line in formatted.split("\n"):
                    print(f"    {line}")
            else:
                text = str(payload)
                for line in text.split("\n"):
                    print(f"    {line}")
    else:
        print("  [FAILED]")
        print(f"    {result.get('error', 'Unknown error')}")
    print()


def render_help():
    print("""
  Synapse CLI -- Quick Reference

  Navigation
    Number keys   Select an item from the list
    b             Go back one level
    q             Quit the CLI
    h             Show this help

  Tool Execution
    r             Run the currently-viewed tool (interactive prompts)
    <bare text>   Direct input for single-param tools
    key=value     Inline arguments

  Search
    /keyword      Search tools by name or description

  All tools are loaded dynamically from the MCP registry.
  Adding a new tool requires zero changes to the CLI.
""")


def render_search_results(matches: list, query: str):
    print(f"  Search results for '{query}':  ({len(matches)} found)")
    print()
    if not matches:
        print("    No tools matched.")
        print()
        return
    for i, tool in enumerate(matches, 1):
        print(f"    {i:>2})  {tool.name}  [{tool.category}]")
        print(f"        {tool.description}")
    print()
    print("     b) Back    q) Quit")
    print()


def render_error(msg: str):
    print(f"  Error: {msg}")
    print()


def prompt(text: str = "synapse") -> str:
    try:
        return input(f"  {text} > ").strip()
    except (EOFError, KeyboardInterrupt):
        return "q"
