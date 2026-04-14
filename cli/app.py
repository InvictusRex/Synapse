"""
CLI App - Main event loop.
Wires Navigator (state) -> Renderer (display) -> InputHandler (args) -> Executor (run).
Contains no tool logic whatsoever.
"""
import json
import os
import re

from mcp.registry import get_registry
from mcp.tool_loader import register_all_tools

from .navigator import Navigator, State
from .executor import ToolExecutor
from .input_handler import try_inline_execution, extract_save_path
from . import renderer

DEFAULT_OUTPUT_DIR = "outputs"


def _make_filename_from_args(args):
    """
    Derive a human-readable filename from tool arguments.
    Picks the first string arg that looks like a topic/prompt/query,
    slugifies it, and caps at 50 chars.
    """
    # Priority order for picking the "title" value
    for key in ("topic", "prompt", "query", "subject", "expression"):
        if key in args and isinstance(args[key], str):
            raw = args[key]
            break
    else:
        # Fall back to the first string value
        raw = next((v for v in args.values() if isinstance(v, str)), "output")

    # Slugify: lowercase, replace non-alphanum with underscores, collapse
    slug = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    if len(slug) > 50:
        slug = slug[:50].rstrip("_")
    return slug + ".txt"


def _resolve_save_path(save_path, tool_name, args):
    """
    Turn a raw save_path from the parser into an actual file path.
      None  -> no save
      ""    -> outputs/<slug_from_args>.txt
      "dir/" -> dir/<slug_from_args>.txt
      "file.txt" -> outputs/file.txt  (if no directory part)
      "D:/docs/file.txt" -> as-is
    """
    if save_path is None:
        return None

    auto_name = _make_filename_from_args(args)

    if save_path == "":
        return os.path.join(DEFAULT_OUTPUT_DIR, auto_name)

    if save_path.endswith("/"):
        return os.path.join(save_path.rstrip("/"), auto_name)

    # If no directory component, default to outputs/
    if os.sep not in save_path and "/" not in save_path:
        return os.path.join(DEFAULT_OUTPUT_DIR, save_path)

    return save_path


def _save_result(result, filepath, executor):
    """Save tool result to a file via the MCP write_file tool."""
    payload = result.get("result")
    if isinstance(payload, (dict, list)):
        content = json.dumps(payload, indent=2, default=str)
    else:
        content = str(payload)

    # Ensure parent directory exists
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)

    save_result = executor.execute("write_file", {
        "filepath": filepath,
        "content": content,
    })
    if save_result.get("success"):
        print(f"\n  Saved to {filepath}")
    else:
        print(f"\n  Could not save: {save_result.get('error')}")
    print()


def _run_tool(tool, executor, args, save_path):
    """
    Execute a tool, display result, auto-save.
    save_path=None means user explicitly said 'save to <path>'.
    If save_path is missing (no save instruction), we still auto-save
    to outputs/<topic_slug>.txt by default.
    """
    renderer.render_execution_start(tool.name, args)
    result = executor.execute(tool.name, args)
    renderer.render_result(result)

    if result.get("success") and result.get("result") is not None:
        # If user didn't mention saving at all, default to auto-save
        effective_path = save_path if save_path is not None else ""
        filepath = _resolve_save_path(effective_path, tool.name, args)
        if filepath:
            _save_result(result, filepath, executor)

    renderer.prompt("Press Enter to continue")
    renderer.clear_screen()
    renderer.render_banner()


def run():
    """Entry point for the interactive CLI."""
    # -- bootstrap --
    register_all_tools()
    registry = get_registry()
    nav      = Navigator(registry)
    executor = ToolExecutor()

    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

    renderer.clear_screen()
    renderer.render_banner()

    # -- main loop --
    while True:
        renderer.render_breadcrumb(nav.breadcrumb)

        # Display current state
        if nav.state == State.CATEGORIES:
            renderer.render_categories(nav.categories, nav.tool_counts)
        elif nav.state == State.TOOLS:
            renderer.render_tool_list(nav.current_category, nav.current_tools)
        elif nav.state == State.DETAIL:
            renderer.render_tool_detail(nav.current_tool)
        elif nav.state == State.SEARCH:
            renderer.render_search_results(nav.search_results, nav.search_query)

        # Get user input
        raw = renderer.prompt()

        if raw in ("q", "quit", "exit"):
            print("\n  Goodbye!\n")
            break

        if raw in ("b", "back"):
            nav.go_back()
            renderer.clear_screen()
            renderer.render_banner()
            continue

        if raw in ("h", "help"):
            renderer.render_help()
            continue

        # Search: /keyword
        if raw.startswith("/"):
            query = raw[1:].strip()
            if query:
                nav.search(query)
                renderer.clear_screen()
                renderer.render_banner()
            continue

        # Numeric selection (categories / tool list / search results)
        if raw.isdigit() and nav.state != State.DETAIL:
            idx = int(raw)
            if nav.state == State.CATEGORIES:
                if nav.select_category(idx):
                    renderer.clear_screen()
                    renderer.render_banner()
                else:
                    renderer.render_error(f"Invalid selection: {idx}")
            elif nav.state in (State.TOOLS, State.SEARCH):
                if nav.select_tool(idx):
                    renderer.clear_screen()
                    renderer.render_banner()
                else:
                    renderer.render_error(f"Invalid selection: {idx}")
            continue

        # Detail screen: everything the user types is a prompt for the tool
        if raw and nav.state == State.DETAIL:
            tool = nav.current_tool
            args, save_path = try_inline_execution(raw, tool)
            if args is not None:
                _run_tool(tool, executor, args, save_path)
            else:
                renderer.render_error("Could not parse input. Try: topic text here")
            continue

        # Unrecognized (only on non-detail screens)
        if raw:
            renderer.render_error(f"Unknown command: '{raw}'.  Type 'h' for help.")
