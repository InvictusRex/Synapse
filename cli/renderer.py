"""
CLI Renderer - All terminal UI formatting and display logic.
Yellow banner, white headings, soft blue-gray body text.
"""
import json
import os
from typing import Any, Dict, List

# -- Palette ----------------------------------------------------------------
_Y      = "\033[38;2;250;189;47m"    # yellow #fabd2f  — banner + prompt
_W      = "\033[38;2;235;219;178m"   # warm white #ebdbb2  — headings
_T      = "\033[38;2;131;165;152m"   # muted teal #83a598  — body text
_DIM    = "\033[38;2;102;92;84m"     # dim brown #665c54  — secondary/hints
_ERR    = "\033[38;2;251;73;52m"     # red #fb4934  — errors
_OK     = "\033[38;2;184;187;38m"    # green #b8bb26  — success
_RESET  = "\033[0m"

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
    return f"{_DIM}{char * width}{_RESET}"


def render_banner():
    from mcp.registry import get_registry
    reg = get_registry()
    cats = reg.get_categorized_tools()
    total = len(reg.tools)
    cat_line = ", ".join(f"{len(v)} {k}" for k, v in sorted(cats.items()))

    print(f"""{_Y}
   .d8888b.  Y88b   d88P 888b    888        d8888 8888888b.   .d8888b.  8888888888
  d88P  Y88b  Y88b d88P  8888b   888       d88888 888   Y88b d88P  Y88b 888
  Y88b.        Y88o88P   88888b  888      d88P888 888    888 Y88b.      888
   "Y888b.      Y888P    888Y88b 888     d88P 888 888   d88P  "Y888b.   8888888
      "Y88b.     888     888 Y88b888    d88P  888 8888888P"      "Y88b. 888
        "888     888     888  Y88888   d88P   888 888              "888 888
  Y88b  d88P     888     888   Y8888  d8888888888 888        Y88b  d88P 888
   "Y8888P"      888     888    Y888 d88P     888 888         "Y8888P"  8888888888
{_RESET}
{_W}  Tools: {total}    Categories: {len(cats)}{_RESET}
{_DIM}  {cat_line}{_RESET}
""")


def render_breadcrumb(path: List[str]):
    parts = [f"{_DIM}Home{_RESET}"] + [f"{_T}{p}{_RESET}" for p in path]
    print(f"  {' > '.join(parts)}")
    print()


def render_categories(categories: List[str], tool_counts: Dict[str, int]):
    print(f"  {_W}Select a category:{_RESET}")
    print()
    for i, cat in enumerate(categories, 1):
        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        count = tool_counts.get(cat, 0)
        print(f"    {_W}{i:>2}{_RESET})  {_T}{label}{_RESET}  {_DIM}({count} tools){_RESET}")
    print()
    print(f"    {_DIM} q) Quit    h) Help{_RESET}")
    print()


def render_tool_list(category: str, tools: list):
    label = CATEGORY_LABELS.get(category, category.replace("_", " ").title())
    print(f"  {_W}{label}{_RESET}  {_DIM}--  {len(tools)} tools{_RESET}")
    print()
    for i, tool in enumerate(tools, 1):
        print(f"    {_W}{i:>2}{_RESET})  {_T}{tool.name}{_RESET}")
        print(f"        {_DIM}{tool.description}{_RESET}")
    print()
    print(f"    {_DIM} b) Back    q) Quit{_RESET}")
    print()


def render_tool_detail(tool):
    print(f"  {_W}{tool.name}{_RESET}")
    print(f"  {_DIM}{tool.description}{_RESET}")
    print()
    print(f"  {_T}Type your prompt in plain english. Output auto-saves to outputs/.{_RESET}")
    print(f"  {_DIM}To save elsewhere: ...save to D:/docs/report.txt{_RESET}")
    print()
    print(f"    {_DIM} b) Back    q) Quit{_RESET}")
    print()


def render_execution_start(tool_name: str, args: Dict):
    print()
    print("  " + _hr("="))
    print(f"  {_W}Executing: {tool_name}{_RESET}")
    if args:
        for k, v in args.items():
            display = str(v)
            if len(display) > 80:
                display = display[:77] + "..."
            print(f"    {_T}{k}{_RESET} = {_T}{display}{_RESET}")
    print("  " + _hr("="))
    print()


def render_result(result: Dict[str, Any]):
    if result.get("success"):
        print(f"  {_OK}[OK]{_RESET}")
        print()
        payload = result.get("result")
        if payload is not None:
            if isinstance(payload, (dict, list)):
                formatted = json.dumps(payload, indent=2, default=str)
                for line in formatted.split("\n"):
                    print(f"    {_T}{line}{_RESET}")
            else:
                text = str(payload)
                for line in text.split("\n"):
                    print(f"    {_T}{line}{_RESET}")
    else:
        print(f"  {_ERR}[FAILED]{_RESET}")
        print(f"    {_ERR}{result.get('error', 'Unknown error')}{_RESET}")
    print()


def render_help():
    print(f"""
  {_W}Synapse CLI -- Quick Reference{_RESET}

  {_W}Navigation{_RESET}
    {_T}Number keys   Select an item from the list{_RESET}
    {_T}b             Go back one level{_RESET}
    {_T}q             Quit the CLI{_RESET}
    {_T}h             Show this help{_RESET}

  {_W}Tool Execution{_RESET}
    {_T}Just type in plain english on the tool screen{_RESET}
    {_T}Output is auto-saved to outputs/{_RESET}

  {_W}Search{_RESET}
    {_T}/keyword      Search tools by name or description{_RESET}

  {_DIM}All tools are loaded dynamically from the MCP registry.{_RESET}
  {_DIM}Adding a new tool requires zero changes to the CLI.{_RESET}
""")


def render_search_results(matches: list, query: str):
    print(f"  {_W}Search results for '{query}':{_RESET}  {_DIM}({len(matches)} found){_RESET}")
    print()
    if not matches:
        print(f"    {_DIM}No tools matched.{_RESET}")
        print()
        return
    for i, tool in enumerate(matches, 1):
        print(f"    {_W}{i:>2}{_RESET})  {_T}{tool.name}{_RESET}  {_DIM}[{tool.category}]{_RESET}")
        print(f"        {_DIM}{tool.description}{_RESET}")
    print()
    print(f"    {_DIM} b) Back    q) Quit{_RESET}")
    print()


def render_error(msg: str):
    print(f"  {_ERR}Error: {msg}{_RESET}")
    print()


def prompt(text: str = "synapse") -> str:
    try:
        return input(f"  {_Y}{text} >{_RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        return "q"
