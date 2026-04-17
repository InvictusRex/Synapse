"""
Perception Tools (Phase 2)

Read-only observations of the visual state of the screen. Currently just
screenshot capture; Phase 7 will add OCR, template matching, and
vision-LLM queries to this module.

Dependencies:
    pyautogui - cross-platform screenshot capture. Falls back gracefully
                on headless systems where the capture call raises.
    pygetwindow - optional; only needed for window-scoped screenshots.

Screenshots are treated as read-only (they don't mutate system state),
so the tool is NOT marked requires_confirmation. Saving the screenshot
to disk uses the user-provided save_path and inherits that risk; if you
want to gate it, add "take_screenshot" to SENSITIVE_TOOLS_BLOCK or make
the tool confirmation-required in its registration.
"""
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional


def _try_import_pyautogui():
    try:
        import pyautogui  # noqa: F401
        return pyautogui
    except Exception:
        return None


def _try_import_pygetwindow():
    try:
        import pygetwindow  # noqa: F401
        return pygetwindow
    except Exception:
        return None


def _safe_int(val, default=0):
    """Coerce a value to int; return default on None/garbage."""
    try:
        if val is None:
            return default
        return int(val)
    except (TypeError, ValueError):
        return default


def _find_and_focus_window(window_title: str):
    """
    Find a window by substring match on its title, bring it to the
    foreground, and return (left, top, width, height, title). Returns
    (None, error_message) if pygetwindow isn't available or no window
    matches.
    
    We do substring matching because window titles typically include
    more than just the app name (e.g. "Inbox - user@domain - Google
    Chrome" when the user just says "chrome").
    
    Heavy defensive handling: pygetwindow on Windows can return window
    objects whose attributes blow up unexpectedly (None titles, access
    denied errors, weird handle states). We wrap every attribute access
    so one bad window doesn't crash the whole lookup.
    """
    pgw = _try_import_pygetwindow()
    if pgw is None:
        return None, "pygetwindow is not available"
    
    try:
        needle = (window_title or "").lower().strip()
        if not needle:
            return None, "window_title is empty"
        
        # Collect candidate windows. Two fallback paths because
        # getAllWindows() sometimes throws on Windows for reasons
        # unrelated to our query (shell extensions, protected processes).
        all_windows = []
        try:
            raw = pgw.getAllWindows()
            if raw:
                all_windows = list(raw)
        except Exception:
            all_windows = []
        
        if not all_windows:
            # Fallback: iterate by title
            try:
                for t in (pgw.getAllTitles() or []):
                    if not t:
                        continue
                    try:
                        for w in (pgw.getWindowsWithTitle(t) or []):
                            if w is not None:
                                all_windows.append(w)
                    except Exception:
                        continue
            except Exception:
                pass
        
        # Match loop - swallow per-window errors so a single bad handle
        # doesn't abort the whole search.
        matches = []
        for w in all_windows:
            if w is None:
                continue
            try:
                title_raw = getattr(w, "title", None)
                title = str(title_raw).lower() if title_raw else ""
                if not title.strip():
                    continue
                if needle in title:
                    matches.append(w)
            except Exception:
                continue
        
        if not matches:
            return None, f"No window found matching '{window_title}'"
        
        # Pick the best candidate: non-minimized + largest area.
        def score(w):
            try:
                minimized = bool(getattr(w, "isMinimized", False))
            except Exception:
                minimized = False
            area = _safe_int(getattr(w, "width", 0)) * _safe_int(getattr(w, "height", 0))
            return (0 if minimized else 1, area)
        try:
            matches.sort(key=score, reverse=True)
        except Exception:
            pass
        win = matches[0]
        
        # Restore if minimized.
        try:
            if getattr(win, "isMinimized", False):
                win.restore()
                time.sleep(0.1)
        except Exception:
            pass
        
        # Bring to foreground (best-effort - sometimes Windows only
        # flashes the taskbar icon instead of actually focusing).
        try:
            win.activate()
        except Exception:
            pass
        
        # Let the OS finish redrawing / re-stacking.
        time.sleep(0.25)
        
        # Geometry - every read is defensive because some window types
        # expose None for some attributes on certain Windows versions.
        l = _safe_int(getattr(win, "left", 0))
        t = _safe_int(getattr(win, "top", 0))
        w = _safe_int(getattr(win, "width", 0))
        h = _safe_int(getattr(win, "height", 0))
        
        # Title for display (string, may be None on weird windows)
        try:
            matched_title = str(getattr(win, "title", "") or "")
        except Exception:
            matched_title = ""
        
        if w <= 0 or h <= 0:
            return None, (
                f"Window '{matched_title or window_title}' has invalid "
                f"dimensions ({w}x{h}) - might be minimized or off-screen"
            )
        
        # Clamp negatives - on Windows, minimized windows report
        # coordinates like (-32000, -32000) which break pyautogui.
        if l < 0: l = 0
        if t < 0: t = 0
        
        return (l, t, w, h, matched_title), None
    except Exception as e:
        return None, f"Could not locate window: {e}"


def take_screenshot(save_path: Optional[str] = None,
                    window_title: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture the screen and save it to disk.
    
    Args:
        save_path:    Where to save the PNG. If omitted, saves to the
                      memory_store/screenshots/ folder with a
                      timestamped name.
        window_title: If provided, find the window whose title contains
                      this string, focus it, and capture only its area.
                      If omitted, captures the full screen.
    
    Returns:
        dict with success, filepath, and image dimensions (also
        "window_title" when a window-scoped capture succeeded).
    """
    # Blanket guard - anything that goes wrong (library bugs, missing
    # display, surprise None values from Windows window objects, etc.)
    # becomes a clean error dict instead of crashing the caller.
    try:
        return _take_screenshot_inner(save_path, window_title)
    except Exception as e:
        return {
            "success": False,
            "error": f"take_screenshot crashed: {type(e).__name__}: {e}"
        }


def _take_screenshot_inner(save_path: Optional[str],
                           window_title: Optional[str]) -> Dict[str, Any]:
    """Actual implementation - wrapped by take_screenshot for safety."""
    pag = _try_import_pyautogui()
    if pag is None:
        return {
            "success": False,
            "error": "pyautogui is not available. Install with: pip install pyautogui"
        }
    
    try:
        # Decide where to save
        if save_path:
            from tools.all_tools import resolve_path
            filepath = resolve_path(save_path)
        else:
            project_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            screenshots_dir = os.path.join(project_root, "memory_store", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
        
        # Ensure parent folder exists (matches write_file behavior)
        parent = os.path.dirname(filepath)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        
        # Default extension if user didn't specify an image format
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            filepath = filepath + '.png'
        
        # Window-scoped capture path
        matched_title = None
        region = None
        if window_title:
            info, err = _find_and_focus_window(window_title)
            if info is None:
                # Soft fallback: take a full-screen screenshot but SURFACE
                # the window-lookup error so the caller/LLM knows the
                # specific window couldn't be found.
                return {
                    "success": False,
                    "error": f"Window-scoped screenshot failed: {err}",
                    "attempted_window_title": window_title
                }
            l, t, w, h, matched_title = info
            region = (l, t, w, h)
        
        if region:
            img = pag.screenshot(region=region)
        else:
            img = pag.screenshot()
        img.save(filepath)
        
        result = {
            "success": True,
            "filepath": filepath,
            "width": img.width,
            "height": img.height,
            "format": "PNG"
        }
        if matched_title:
            result["window_title"] = matched_title
        return result
    except Exception as e:
        msg = str(e)
        if "DISPLAY" in msg.upper() or "display" in msg:
            msg = ("Screenshot failed: no display available. "
                   "Screenshots require a graphical session.")
        return {"success": False, "error": msg}


def register_perception_tools(server) -> int:
    """Register perception tools with an MCP server. Returns count."""
    from mcp.server import ToolDefinition, ToolCategory
    
    tools = [
        ToolDefinition(
            "take_screenshot",
            "Capture a screenshot of the full screen, or of a specific "
            "window when window_title is provided",
            ToolCategory.PERCEPTION,
            take_screenshot, [], ["save_path", "window_title"]
        ),
    ]
    server.register_tools(tools)
    return len(tools)
