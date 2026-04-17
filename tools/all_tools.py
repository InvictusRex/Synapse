"""
Tool Implementations
All tools that can be used by agents via MCP
"""
import os
import sys
import shutil
import json
import subprocess
import platform
import math
from datetime import datetime
from typing import Dict, Any, List

from mcp.server import get_mcp_server, ToolCategory, ToolDefinition


# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Common paths
HOME_DIR = os.path.expanduser("~")
DESKTOP = os.path.join(HOME_DIR, "Desktop")
DOCUMENTS = os.path.join(HOME_DIR, "Documents")
DOWNLOADS = os.path.join(HOME_DIR, "Downloads")


def resolve_path(filepath: str) -> str:
    """Resolve path - handles ~, relative paths, and common folder names"""
    if not filepath:
        return ""
    
    filepath = filepath.strip()
    
    # Handle common folder names at the start of path
    lower_path = filepath.lower()
    if lower_path == "desktop" or lower_path.startswith("desktop/") or lower_path.startswith("desktop\\"):
        filepath = filepath.replace(filepath[:7], DESKTOP, 1)
    elif lower_path == "documents" or lower_path.startswith("documents/") or lower_path.startswith("documents\\"):
        filepath = filepath.replace(filepath[:9], DOCUMENTS, 1)
    elif lower_path == "downloads" or lower_path.startswith("downloads/") or lower_path.startswith("downloads\\"):
        filepath = filepath.replace(filepath[:9], DOWNLOADS, 1)
    
    filepath = os.path.expanduser(filepath)
    filepath = os.path.abspath(filepath)
    filepath = os.path.normpath(filepath)
    return filepath


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# ============================================================
# FILESYSTEM TOOLS
# ============================================================

def read_file(filepath: str) -> Dict[str, Any]:
    """Read content from a file"""
    try:
        filepath = resolve_path(filepath)
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        if not os.path.isfile(filepath):
            return {"success": False, "error": f"Not a file: {filepath}"}
        
        size = os.path.getsize(filepath)
        if size > 10 * 1024 * 1024:
            return {"success": False, "error": f"File too large ({format_size(size)})"}
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return {"success": True, "filepath": filepath, "content": content, "size": format_size(size)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(filepath: str, content: str) -> Dict[str, Any]:
    """Write content to a file"""
    try:
        filepath = resolve_path(filepath)
        parent = os.path.dirname(filepath)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {"success": True, "filepath": filepath, "size": format_size(len(content))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_folder(folder_path: str) -> Dict[str, Any]:
    """Create a folder"""
    try:
        folder_path = resolve_path(folder_path)
        os.makedirs(folder_path, exist_ok=True)
        return {"success": True, "path": folder_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_directory(directory: str) -> Dict[str, Any]:
    """List contents of a directory"""
    try:
        directory = resolve_path(directory)
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        if not os.path.isdir(directory):
            return {"success": False, "error": f"Not a directory: {directory}"}
        
        items = []
        for name in os.listdir(directory):
            full_path = os.path.join(directory, name)
            is_dir = os.path.isdir(full_path)
            
            item = {
                "name": name,
                "type": "folder" if is_dir else "file",
                "path": full_path
            }
            
            if not is_dir:
                try:
                    item["size"] = format_size(os.path.getsize(full_path))
                except:
                    item["size"] = "?"
            
            items.append(item)
        
        items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
        
        return {"success": True, "directory": directory, "items": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(filepath: str) -> Dict[str, Any]:
    """Delete a file"""
    try:
        filepath = resolve_path(filepath)
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        os.remove(filepath)
        return {"success": True, "deleted": filepath}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_folder(folder_path: str) -> Dict[str, Any]:
    """Delete a folder"""
    try:
        folder_path = resolve_path(folder_path)
        if not os.path.exists(folder_path):
            return {"success": False, "error": f"Folder not found: {folder_path}"}
        
        shutil.rmtree(folder_path)
        return {"success": True, "deleted": folder_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move a file or folder"""
    try:
        source = resolve_path(source)
        destination = resolve_path(destination)
        
        if not os.path.exists(source):
            return {"success": False, "error": f"Source not found: {source}"}
        
        shutil.move(source, destination)
        return {"success": True, "source": source, "destination": destination}
    except Exception as e:
        return {"success": False, "error": str(e)}


def copy_file(source: str, destination: str) -> Dict[str, Any]:
    """Copy a file or folder"""
    try:
        source = resolve_path(source)
        destination = resolve_path(destination)
        
        if not os.path.exists(source):
            return {"success": False, "error": f"Source not found: {source}"}
        
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        
        return {"success": True, "source": source, "destination": destination}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_files(directory: str, pattern: str) -> Dict[str, Any]:
    """Search for files matching a pattern"""
    try:
        import fnmatch
        directory = resolve_path(directory)
        
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        
        matches = []
        for root, dirs, files in os.walk(directory):
            for name in files:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    matches.append(os.path.join(root, name))
            
            if len(matches) >= 100:
                break
        
        return {"success": True, "pattern": pattern, "matches": matches, "count": len(matches)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# CONTENT TOOLS
# ============================================================

def generate_text(prompt: str, max_length: str = "medium") -> Dict[str, Any]:
    """Generate text using LLM pool"""
    try:
        from llm import get_llm_pool
        pool = get_llm_pool()
        
        response = pool.generate(prompt)
        
        if response.success:
            return {"success": True, "content": response.content, "length": len(response.content)}
        else:
            return {"success": False, "error": response.error}
    except Exception as e:
        return {"success": False, "error": str(e)}


def summarize_text(text: str) -> Dict[str, Any]:
    """Summarize text"""
    prompt = f"Summarize this concisely:\n\n{text[:5000]}"
    return generate_text(prompt, "medium")


# ============================================================
# WEB TOOLS
# ============================================================

def fetch_webpage(url: str) -> Dict[str, Any]:
    """Fetch webpage and extract text"""
    try:
        import requests
        from bs4 import BeautifulSoup
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer']):
            tag.decompose()
        
        title = soup.title.string if soup.title else "No title"
        text = soup.get_text(separator='\n', strip=True)
        
        return {"success": True, "url": url, "title": title, "content": text[:10000]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_file(url: str, save_path: str) -> Dict[str, Any]:
    """Download a file from URL"""
    try:
        import requests
        
        save_path = resolve_path(save_path)
        
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        size = os.path.getsize(save_path)
        return {"success": True, "url": url, "saved_to": save_path, "size": format_size(size)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# SYSTEM TOOLS
# ============================================================

def run_command(command: str) -> Dict[str, Any]:
    """Run a shell command"""
    try:
        is_windows = platform.system() == "Windows"
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd()
        )
        
        return {
            "success": result.returncode == 0,
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_cwd() -> Dict[str, Any]:
    """Get current working directory"""
    try:
        cwd = os.getcwd()
        return {"success": True, "cwd": cwd, "path": cwd}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        import socket
        
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cwd": os.getcwd()
        }
        
        # Try to get more info
        try:
            import psutil
            info["cpu_count"] = psutil.cpu_count()
            info["memory_total"] = format_size(psutil.virtual_memory().total)
            info["memory_available"] = format_size(psutil.virtual_memory().available)
        except ImportError:
            info["cpu_count"] = os.cpu_count()
        
        return {"success": True, **info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_datetime() -> Dict[str, Any]:
    """Get current date and time"""
    now = datetime.now()
    return {
        "success": True,
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day": now.strftime("%A"),
        "timezone": str(now.astimezone().tzinfo)
    }


def calculate(expression: str) -> Dict[str, Any]:
    """Calculate a math expression"""
    try:
        allowed_chars = set('0123456789+-*/().^ ')
        expr_clean = expression.replace('^', '**')
        
        if not all(c in allowed_chars or c.isalpha() for c in expression):
            return {"success": False, "error": "Invalid characters in expression"}
        
        allowed_names = {
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow,
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'tan': math.tan, 'log': math.log, 'log10': math.log10,
            'pi': math.pi, 'e': math.e
        }
        
        result = eval(expr_clean, {"__builtins__": {}}, allowed_names)
        return {"success": True, "expression": expression, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# DATA TOOLS
# ============================================================

def read_json(filepath: str) -> Dict[str, Any]:
    """Read a JSON file"""
    try:
        filepath = resolve_path(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {"success": True, "filepath": filepath, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_json(filepath: str, data: Any) -> Dict[str, Any]:
    """Write data to a JSON file"""
    try:
        filepath = resolve_path(filepath)
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        return {"success": True, "filepath": filepath}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_csv(filepath: str) -> Dict[str, Any]:
    """Read a CSV file"""
    try:
        import csv
        filepath = resolve_path(filepath)
        
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        return {"success": True, "filepath": filepath, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_csv(filepath: str, rows: List[Dict], headers: List[str] = None) -> Dict[str, Any]:
    """Write data to a CSV file"""
    try:
        import csv
        filepath = resolve_path(filepath)
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        
        if not rows:
            return {"success": False, "error": "No data to write"}
        
        fieldnames = headers or list(rows[0].keys())
        
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        return {"success": True, "filepath": filepath, "rows_written": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# MEMORY TOOLS
# ============================================================

def memory_store(content: str, metadata: Dict = None) -> Dict[str, Any]:
    """Store content in persistent memory"""
    try:
        from memory import get_persistent_memory
        memory = get_persistent_memory()
        entry_id = memory.store(content, metadata)
        return {"success": True, "entry_id": entry_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def memory_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search persistent memory"""
    try:
        from memory import get_persistent_memory
        memory = get_persistent_memory()
        results = memory.search(query, limit)
        return {
            "success": True,
            "results": [{"id": r.id, "content": r.content, "metadata": r.metadata} for r in results],
            "count": len(results)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def memory_retrieve(entry_id: str) -> Dict[str, Any]:
    """Retrieve a memory entry by ID"""
    try:
        from memory import get_persistent_memory
        memory = get_persistent_memory()
        entry = memory.retrieve(entry_id)
        if entry:
            return {"success": True, "content": entry.content, "metadata": entry.metadata}
        return {"success": False, "error": "Entry not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# TOOL REGISTRATION
# ============================================================

def register_all_tools():
    """Register all tools with the MCP server"""
    server = get_mcp_server()
    
    # Phase 1 & 2: import observational tools. These registrations are
    # kept in their own modules to keep this file manageable and to make
    # it easy to disable them in environments without GUI libraries.
    from tools.state_tools import register_state_tools
    from tools.perception_tools import register_perception_tools
    
    tools = [
        # Filesystem tools
        ToolDefinition("read_file", "Read content from a file", ToolCategory.FILESYSTEM,
                      read_file, ["filepath"]),
        # write_file creates or overwrites but the path is always explicit -
        # low-risk enough to not warrant a prompt on every run.
        ToolDefinition("write_file", "Write content to a file", ToolCategory.FILESYSTEM,
                      write_file, ["filepath", "content"]),
        ToolDefinition("create_folder", "Create a folder", ToolCategory.FILESYSTEM,
                      create_folder, ["folder_path"]),
        ToolDefinition("list_directory", "List directory contents", ToolCategory.FILESYSTEM,
                      list_directory, ["directory"]),
        # Deletion is genuinely destructive -> always confirm.
        ToolDefinition("delete_file", "Delete a file", ToolCategory.FILESYSTEM,
                      delete_file, ["filepath"],
                      requires_confirmation=True),
        ToolDefinition("delete_folder", "Delete a folder", ToolCategory.FILESYSTEM,
                      delete_folder, ["folder_path"],
                      requires_confirmation=True),
        # Move and copy don't delete data; they just create/relocate. No prompt.
        ToolDefinition("move_file", "Move a file or folder", ToolCategory.FILESYSTEM,
                      move_file, ["source", "destination"]),
        ToolDefinition("copy_file", "Copy a file or folder", ToolCategory.FILESYSTEM,
                      copy_file, ["source", "destination"]),
        ToolDefinition("search_files", "Search for files", ToolCategory.FILESYSTEM,
                      search_files, ["directory", "pattern"]),
        
        # Content tools
        ToolDefinition("generate_text", "Generate text content", ToolCategory.CONTENT,
                      generate_text, ["prompt"], ["max_length"]),
        ToolDefinition("summarize_text", "Summarize text", ToolCategory.CONTENT,
                      summarize_text, ["text"]),
        
        # Web tools
        ToolDefinition("fetch_webpage", "Fetch and extract webpage content", ToolCategory.WEB,
                      fetch_webpage, ["url"]),
        # download_file writes to disk but the path is explicit - not sensitive.
        ToolDefinition("download_file", "Download a file from URL", ToolCategory.WEB,
                      download_file, ["url", "save_path"]),
        
        # System tools
        # run_command can do ANYTHING (including "rm -rf /") -> always confirm.
        ToolDefinition("run_command", "Run a shell command", ToolCategory.SYSTEM,
                      run_command, ["command"],
                      requires_confirmation=True),
        ToolDefinition("get_cwd", "Get current working directory", ToolCategory.SYSTEM,
                      get_cwd, []),
        ToolDefinition("get_system_info", "Get system information", ToolCategory.SYSTEM,
                      get_system_info, []),
        ToolDefinition("get_datetime", "Get current date and time", ToolCategory.SYSTEM,
                      get_datetime, []),
        ToolDefinition("calculate", "Calculate a math expression", ToolCategory.SYSTEM,
                      calculate, ["expression"]),
        
        # Data tools
        ToolDefinition("read_json", "Read a JSON file", ToolCategory.DATA,
                      read_json, ["filepath"]),
        ToolDefinition("write_json", "Write data to JSON file", ToolCategory.DATA,
                      write_json, ["filepath", "data"]),
        ToolDefinition("read_csv", "Read a CSV file", ToolCategory.DATA,
                      read_csv, ["filepath"]),
        ToolDefinition("write_csv", "Write data to CSV file", ToolCategory.DATA,
                      write_csv, ["filepath", "rows"], ["headers"]),
        
        # Memory tools
        ToolDefinition("memory_store", "Store content in memory", ToolCategory.MEMORY,
                      memory_store, ["content"], ["metadata"]),
        ToolDefinition("memory_search", "Search memory", ToolCategory.MEMORY,
                      memory_search, ["query"], ["limit"]),
        ToolDefinition("memory_retrieve", "Retrieve memory by ID", ToolCategory.MEMORY,
                      memory_retrieve, ["entry_id"]),
    ]
    
    server.register_tools(tools)
    
    # Register observational tools from their own modules. Count them
    # so the caller knows the total tool inventory.
    state_count = register_state_tools(server)
    perception_count = register_perception_tools(server)
    
    return len(tools) + state_count + perception_count
