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

from mcp.server import get_mcp_server, ToolCategory


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def resolve_path(filepath: str) -> str:
    """Resolve path - handles ~, relative paths"""
    if not filepath:
        return ""
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
            path = os.path.join(directory, name)
            try:
                stat = os.stat(path)
                items.append({
                    "name": name,
                    "type": "folder" if os.path.isdir(path) else "file",
                    "size": format_size(stat.st_size) if os.path.isfile(path) else "-"
                })
            except:
                items.append({"name": name, "type": "unknown", "size": "-"})
        
        items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
        return {"success": True, "directory": directory, "items": items, "count": len(items)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(filepath: str) -> Dict[str, Any]:
    """Delete a file"""
    try:
        filepath = resolve_path(filepath)
        if not os.path.exists(filepath):
            return {"success": False, "error": f"Not found: {filepath}"}
        if os.path.isdir(filepath):
            return {"success": False, "error": "Use delete_folder for directories"}
        os.remove(filepath)
        return {"success": True, "deleted": filepath}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_folder(folder_path: str, recursive: bool = False) -> Dict[str, Any]:
    """Delete a folder"""
    try:
        folder_path = resolve_path(folder_path)
        if not os.path.exists(folder_path):
            return {"success": False, "error": f"Not found: {folder_path}"}
        if recursive:
            shutil.rmtree(folder_path)
        else:
            os.rmdir(folder_path)
        return {"success": True, "deleted": folder_path}
    except OSError as e:
        if "not empty" in str(e).lower():
            return {"success": False, "error": "Folder not empty. Use recursive=True"}
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
    """Search for files matching pattern"""
    import fnmatch
    try:
        directory = resolve_path(directory)
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        
        matches = []
        for root, dirs, files in os.walk(directory):
            for name in fnmatch.filter(files, pattern):
                matches.append(os.path.join(root, name))
            if len(matches) > 100:
                break
        
        return {"success": True, "pattern": pattern, "matches": matches[:100], "count": len(matches)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# CONTENT GENERATION TOOLS
# ============================================================

def generate_text(prompt: str, max_length: str = "medium") -> Dict[str, Any]:
    """Generate text using LLM"""
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return {"success": False, "error": "GROQ_API_KEY not set"}
        
        from groq import Groq
        client = Groq(api_key=api_key)
        
        tokens = {"short": 500, "medium": 1500, "long": 3000}.get(max_length, 1500)
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=tokens,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        return {"success": True, "content": content, "length": len(content)}
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
    """Download file from URL"""
    try:
        import requests
        
        save_path = resolve_path(save_path)
        parent = os.path.dirname(save_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        return {"success": True, "url": url, "saved_to": save_path, "size": format_size(os.path.getsize(save_path))}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# SYSTEM TOOLS
# ============================================================

# POSIX command mappings for Windows
POSIX_TO_WINDOWS = {
    "ls": "dir",
    "pwd": "cd",
    "cat": "type",
    "rm": "del",
    "cp": "copy",
    "mv": "move",
    "mkdir": "mkdir",
    "rmdir": "rmdir",
    "clear": "cls",
    "grep": "findstr",
    "touch": "type nul >",
    "head": "more",
    "tail": "more",
    "which": "where",
    "whoami": "whoami",
    "echo": "echo",
}

def run_command(command: str, cwd: str = None) -> Dict[str, Any]:
    """Run shell command with POSIX compatibility on Windows"""
    try:
        original_command = command
        
        # Handle POSIX commands on Windows
        if platform.system() == "Windows":
            cmd_parts = command.strip().split()
            if cmd_parts:
                base_cmd = cmd_parts[0].lower()
                
                # Special handling for common POSIX commands
                if base_cmd == "pwd":
                    return get_cwd()
                elif base_cmd == "ls":
                    # Convert ls to dir with args handling
                    args = cmd_parts[1:] if len(cmd_parts) > 1 else ["."]
                    path = args[-1] if args and not args[-1].startswith("-") else "."
                    return list_directory(path)
                elif base_cmd == "cat" and len(cmd_parts) > 1:
                    return read_file(cmd_parts[1])
                elif base_cmd in POSIX_TO_WINDOWS:
                    cmd_parts[0] = POSIX_TO_WINDOWS[base_cmd]
                    command = " ".join(cmd_parts)
        
        # Set working directory
        work_dir = cwd if cwd else os.getcwd()
        
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60,
            cwd=work_dir
        )
        return {
            "success": result.returncode == 0,
            "command": original_command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "cwd": work_dir
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_cwd() -> Dict[str, Any]:
    """Get current working directory"""
    cwd = os.getcwd()
    return {
        "success": True,
        "cwd": cwd,
        "path": cwd
    }


def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    return {
        "success": True,
        "os": platform.system(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "home": os.path.expanduser("~"),
        "cwd": os.getcwd()
    }


def get_datetime() -> Dict[str, Any]:
    """Get current date/time"""
    now = datetime.now()
    return {
        "success": True,
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S")
    }


def calculate(expression: str) -> Dict[str, Any]:
    """Calculate math expression"""
    try:
        safe = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "log": math.log, "pi": math.pi, "e": math.e
        }
        result = eval(expression, {"__builtins__": {}}, safe)
        return {"success": True, "expression": expression, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# DATA FILE TOOLS
# ============================================================

def read_json(filepath: str) -> Dict[str, Any]:
    """Read JSON file"""
    try:
        filepath = resolve_path(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_json(filepath: str, data: Any) -> Dict[str, Any]:
    """Write JSON file"""
    try:
        filepath = resolve_path(filepath)
        parent = os.path.dirname(filepath)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return {"success": True, "filepath": filepath}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_csv(filepath: str) -> Dict[str, Any]:
    """Read CSV file"""
    try:
        import pandas as pd
        filepath = resolve_path(filepath)
        df = pd.read_csv(filepath, nrows=1000)
        return {
            "success": True,
            "columns": df.columns.tolist(),
            "rows": len(df),
            "preview": df.head(10).to_string()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_csv(filepath: str, data: List[Dict]) -> Dict[str, Any]:
    """Write CSV file"""
    try:
        import pandas as pd
        filepath = resolve_path(filepath)
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        return {"success": True, "filepath": filepath, "rows": len(data)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# REGISTER ALL TOOLS
# ============================================================

def register_all_tools():
    """Register all tools with MCP server"""
    mcp = get_mcp_server()
    
    # Filesystem tools
    mcp.register_tool("read_file", "Read content from a file", ToolCategory.FILESYSTEM,
                      {"filepath": "string"}, ["filepath"], read_file)
    mcp.register_tool("write_file", "Write content to a file (creates file if it doesn't exist)", ToolCategory.FILESYSTEM,
                      {"filepath": "string", "content": "string"}, ["filepath", "content"], write_file)
    mcp.register_tool("create_file", "Create a new file with content (alias for write_file)", ToolCategory.FILESYSTEM,
                      {"filepath": "string", "content": "string"}, ["filepath", "content"], write_file)
    mcp.register_tool("create_folder", "Create a folder", ToolCategory.FILESYSTEM,
                      {"folder_path": "string"}, ["folder_path"], create_folder)
    mcp.register_tool("list_directory", "List directory contents", ToolCategory.FILESYSTEM,
                      {"directory": "string"}, ["directory"], list_directory)
    mcp.register_tool("delete_file", "Delete a file", ToolCategory.FILESYSTEM,
                      {"filepath": "string"}, ["filepath"], delete_file)
    mcp.register_tool("delete_folder", "Delete a folder", ToolCategory.FILESYSTEM,
                      {"folder_path": "string", "recursive": "boolean"}, ["folder_path"], delete_folder)
    mcp.register_tool("move_file", "Move file/folder", ToolCategory.FILESYSTEM,
                      {"source": "string", "destination": "string"}, ["source", "destination"], move_file)
    mcp.register_tool("copy_file", "Copy file/folder", ToolCategory.FILESYSTEM,
                      {"source": "string", "destination": "string"}, ["source", "destination"], copy_file)
    mcp.register_tool("search_files", "Search for files", ToolCategory.FILESYSTEM,
                      {"directory": "string", "pattern": "string"}, ["directory", "pattern"], search_files)
    
    # Content tools
    mcp.register_tool("generate_text", "Generate text with AI", ToolCategory.CONTENT,
                      {"prompt": "string", "max_length": "string"}, ["prompt"], generate_text)
    mcp.register_tool("summarize_text", "Summarize text", ToolCategory.CONTENT,
                      {"text": "string"}, ["text"], summarize_text)
    
    # Web tools
    mcp.register_tool("fetch_webpage", "Fetch and extract webpage text", ToolCategory.WEB,
                      {"url": "string"}, ["url"], fetch_webpage)
    mcp.register_tool("download_file", "Download file from URL", ToolCategory.WEB,
                      {"url": "string", "save_path": "string"}, ["url", "save_path"], download_file)
    
    # System tools
    mcp.register_tool("run_command", "Run shell command (supports POSIX commands on Windows)", ToolCategory.SYSTEM,
                      {"command": "string", "cwd": "string"}, ["command"], run_command)
    mcp.register_tool("get_cwd", "Get current working directory (pwd)", ToolCategory.SYSTEM,
                      {}, [], get_cwd)
    mcp.register_tool("get_system_info", "Get system information", ToolCategory.SYSTEM,
                      {}, [], get_system_info)
    mcp.register_tool("get_datetime", "Get current date/time", ToolCategory.SYSTEM,
                      {}, [], get_datetime)
    mcp.register_tool("calculate", "Calculate math expression", ToolCategory.SYSTEM,
                      {"expression": "string"}, ["expression"], calculate)
    
    # Data tools
    mcp.register_tool("read_json", "Read JSON file", ToolCategory.DATA,
                      {"filepath": "string"}, ["filepath"], read_json)
    mcp.register_tool("write_json", "Write JSON file", ToolCategory.DATA,
                      {"filepath": "string", "data": "any"}, ["filepath", "data"], write_json)
    mcp.register_tool("read_csv", "Read CSV file", ToolCategory.DATA,
                      {"filepath": "string"}, ["filepath"], read_csv)
    mcp.register_tool("write_csv", "Write CSV file", ToolCategory.DATA,
                      {"filepath": "string", "data": "array"}, ["filepath", "data"], write_csv)
    
    print(f"[MCP] Registered {len(mcp.tools)} tools")
