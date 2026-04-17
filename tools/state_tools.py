"""
State-Awareness Tools (Phase 1)

Read-only observations of the host machine's current state. These tools
never mutate anything, so they are NOT marked requires_confirmation.

Dependencies:
    psutil        - cross-platform, required.
    pygetwindow   - optional; falls back gracefully on platforms where
                    it doesn't work (e.g. headless Linux).

Design note: pygetwindow imports are deferred to call time so that a
missing library doesn't break Synapse startup on servers without a GUI.
"""
import os
from typing import Dict, Any, List


def _try_import_pygetwindow():
    """Deferred import so missing GUI libs don't break headless setups."""
    try:
        import pygetwindow  # noqa: F401
        return pygetwindow
    except Exception:
        return None


def _try_import_psutil():
    try:
        import psutil  # noqa: F401
        return psutil
    except Exception:
        return None


# ============================================================
# WINDOW TOOLS
# ============================================================

def get_active_window() -> Dict[str, Any]:
    """Return the title (and, when available, geometry) of the foreground window."""
    pgw = _try_import_pygetwindow()
    if pgw is None:
        return {
            "success": False,
            "error": "pygetwindow is not available on this system. "
                     "Install with: pip install pygetwindow"
        }
    try:
        win = pgw.getActiveWindow()
        if win is None:
            return {"success": True, "title": None, "note": "No active window detected"}
        # Different pygetwindow backends expose different attributes; be defensive.
        info = {"success": True, "title": getattr(win, "title", str(win))}
        for attr in ("left", "top", "width", "height"):
            if hasattr(win, attr):
                info[attr] = getattr(win, attr)
        return info
    except Exception as e:
        return {"success": False, "error": f"Could not read active window: {e}"}


def list_open_windows() -> Dict[str, Any]:
    """Return a list of all visible window titles."""
    pgw = _try_import_pygetwindow()
    if pgw is None:
        return {
            "success": False,
            "error": "pygetwindow is not available on this system."
        }
    try:
        # getAllTitles() returns many empty/duplicate strings on Windows;
        # filter those out so the LLM sees a clean list.
        raw = pgw.getAllTitles()
        titles = sorted({t for t in raw if t and t.strip()})
        return {"success": True, "windows": titles, "count": len(titles)}
    except Exception as e:
        return {"success": False, "error": f"Could not list windows: {e}"}


# ============================================================
# PROCESS TOOLS
# ============================================================

def list_running_processes(limit=50) -> Dict[str, Any]:
    """
    List currently running processes.
    
    `limit` caps the response size so we don't blow out the LLM context
    window on machines with thousands of processes. Accepts int or any
    value coercible to int - the LLM sometimes passes strings like "50".
    """
    # Coerce limit defensively. LLMs occasionally pass "50" or "all" or
    # None; we only proceed with a real int, falling back to the default.
    try:
        if limit is None or (isinstance(limit, str) and not limit.strip().isdigit()):
            limit = 50
        else:
            limit = int(limit)
        if limit <= 0:
            limit = 50
    except (ValueError, TypeError):
        limit = 50
    
    ps = _try_import_psutil()
    if ps is None:
        return {"success": False, "error": "psutil is not available"}
    try:
        procs: List[Dict[str, Any]] = []
        for p in ps.process_iter(['pid', 'name', 'username']):
            try:
                procs.append({
                    "pid": p.info.get('pid'),
                    "name": p.info.get('name'),
                    "user": p.info.get('username')
                })
            except Exception:
                # Some processes vanish mid-iteration; skip them.
                continue
        # Sort by name for deterministic output (easier to eyeball).
        procs.sort(key=lambda x: (x.get("name") or "").lower())
        return {
            "success": True,
            "processes": procs[:limit],
            "total_count": len(procs),
            "returned_count": min(limit, len(procs))
        }
    except Exception as e:
        return {"success": False, "error": f"Could not list processes: {e}"}


def check_process_running(process_name: str) -> Dict[str, Any]:
    """
    Check if a process with the given name is running.
    Match is case-insensitive and substring-based so 'chrome' matches
    'chrome.exe', 'Google Chrome', etc.
    """
    ps = _try_import_psutil()
    if ps is None:
        return {"success": False, "error": "psutil is not available"}
    if not process_name:
        return {"success": False, "error": "process_name is required"}
    try:
        needle = process_name.lower()
        matches = []
        for p in ps.process_iter(['pid', 'name']):
            try:
                name = (p.info.get('name') or "").lower()
                if needle in name:
                    matches.append({"pid": p.info.get('pid'), "name": p.info.get('name')})
            except Exception:
                continue
        return {
            "success": True,
            "process_name": process_name,
            "running": len(matches) > 0,
            "matches": matches,
            "match_count": len(matches)
        }
    except Exception as e:
        return {"success": False, "error": f"Could not check process: {e}"}


# ============================================================
# FILE EXISTENCE
# ============================================================

def check_file_exists(filepath: str) -> Dict[str, Any]:
    """Check whether a file or directory exists at the given path."""
    if not filepath:
        return {"success": False, "error": "filepath is required"}
    try:
        # Reuse the existing path resolver for consistency with other FS tools.
        from tools.all_tools import resolve_path
        resolved = resolve_path(filepath)
        exists = os.path.exists(resolved)
        result: Dict[str, Any] = {
            "success": True,
            "filepath": resolved,
            "exists": exists
        }
        if exists:
            result["is_file"] = os.path.isfile(resolved)
            result["is_directory"] = os.path.isdir(resolved)
            try:
                result["size_bytes"] = os.path.getsize(resolved) if result["is_file"] else None
            except Exception:
                result["size_bytes"] = None
        return result
    except Exception as e:
        return {"success": False, "error": f"Could not check path: {e}"}


# ============================================================
# REGISTRATION
# ============================================================

def register_state_tools(server) -> int:
    """Register all state-awareness tools with an MCP server. Returns count."""
    from mcp.server import ToolDefinition, ToolCategory
    
    tools = [
        ToolDefinition(
            "get_active_window",
            "Get the title and geometry of the currently focused window",
            ToolCategory.STATE,
            get_active_window, [], []
        ),
        ToolDefinition(
            "list_open_windows",
            "List the titles of all currently open/visible windows",
            ToolCategory.STATE,
            list_open_windows, [], []
        ),
        ToolDefinition(
            "list_running_processes",
            "List currently running processes (pid, name, user)",
            ToolCategory.STATE,
            list_running_processes, [], ["limit"]
        ),
        ToolDefinition(
            "check_process_running",
            "Check if a process matching a given name is currently running",
            ToolCategory.STATE,
            check_process_running, ["process_name"], []
        ),
        ToolDefinition(
            "check_file_exists",
            "Check whether a file or folder exists at a given path",
            ToolCategory.STATE,
            check_file_exists, ["filepath"], []
        ),
    ]
    server.register_tools(tools)
    return len(tools)
