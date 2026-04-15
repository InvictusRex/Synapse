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
# DEVELOPMENT TOOLS
# ============================================================

# --- Project Templates ---
PROJECT_TEMPLATES = {
    "python": {
        "files": {
            "main.py": '"""Main entry point"""\n\n\ndef main():\n    print("Hello, World!")\n\n\nif __name__ == "__main__":\n    main()\n',
            "requirements.txt": "# Add your dependencies here\n",
            ".gitignore": "__pycache__/\n*.py[cod]\n*$py.class\n*.so\n.env\nvenv/\n.venv/\ndist/\nbuild/\n*.egg-info/\n",
            "README.md": "# {project_name}\n\n## Setup\n\n```bash\npip install -r requirements.txt\npython main.py\n```\n",
        },
        "folders": ["tests", "src"],
    },
    "python-flask": {
        "files": {
            "app.py": '"""Flask application"""\nfrom flask import Flask, jsonify, request\n\napp = Flask(__name__)\n\n\n@app.route("/")\ndef index():\n    return jsonify({{"message": "Welcome to the API"}})\n\n\n@app.route("/health")\ndef health():\n    return jsonify({{"status": "healthy"}})\n\n\nif __name__ == "__main__":\n    app.run(debug=True)\n',
            "requirements.txt": "flask\npython-dotenv\n",
            ".gitignore": "__pycache__/\n*.py[cod]\n.env\nvenv/\n.venv/\ninstance/\n",
            "README.md": "# {project_name}\n\nFlask API project.\n\n## Setup\n\n```bash\npip install -r requirements.txt\npython app.py\n```\n",
            ".env.example": "FLASK_ENV=development\nSECRET_KEY=change-me\n",
        },
        "folders": ["templates", "static", "tests"],
    },
    "python-fastapi": {
        "files": {
            "main.py": '"""FastAPI application"""\nfrom fastapi import FastAPI\n\napp = FastAPI(title="{project_name}")\n\n\n@app.get("/")\nasync def root():\n    return {{"message": "Welcome to {project_name}"}}\n\n\n@app.get("/health")\nasync def health():\n    return {{"status": "healthy"}}\n',
            "requirements.txt": "fastapi\nuvicorn[standard]\npython-dotenv\n",
            ".gitignore": "__pycache__/\n*.py[cod]\n.env\nvenv/\n.venv/\n",
            "README.md": "# {project_name}\n\nFastAPI project.\n\n## Setup\n\n```bash\npip install -r requirements.txt\nuvicorn main:app --reload\n```\n",
        },
        "folders": ["routers", "models", "schemas", "tests"],
    },
    "node": {
        "files": {
            "index.js": 'console.log("Hello, World!");\n',
            "package.json": '{{\n  "name": "{project_name_lower}",\n  "version": "1.0.0",\n  "description": "{project_name}",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js",\n    "dev": "node --watch index.js",\n    "test": "echo \\"Error: no test specified\\" && exit 1"\n  }}\n}}\n',
            ".gitignore": "node_modules/\n.env\ndist/\ncoverage/\n",
            "README.md": "# {project_name}\n\n## Setup\n\n```bash\nnpm install\nnpm start\n```\n",
        },
        "folders": ["src", "tests"],
    },
    "node-express": {
        "files": {
            "index.js": 'const express = require("express");\n\nconst app = express();\nconst PORT = process.env.PORT || 3000;\n\napp.use(express.json());\n\napp.get("/", (req, res) => {{\n  res.json({{ message: "Welcome to {project_name}" }});\n}});\n\napp.get("/health", (req, res) => {{\n  res.json({{ status: "healthy" }});\n}});\n\napp.listen(PORT, () => {{\n  console.log(`Server running on port ${{PORT}}`);\n}});\n',
            "package.json": '{{\n  "name": "{project_name_lower}",\n  "version": "1.0.0",\n  "description": "{project_name}",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js",\n    "dev": "node --watch index.js",\n    "test": "echo \\"Error: no test specified\\" && exit 1"\n  }},\n  "dependencies": {{\n    "express": "^4.18.0"\n  }}\n}}\n',
            ".gitignore": "node_modules/\n.env\ndist/\ncoverage/\n",
            "README.md": "# {project_name}\n\nExpress.js API project.\n\n## Setup\n\n```bash\nnpm install\nnpm run dev\n```\n",
        },
        "folders": ["routes", "middleware", "tests"],
    },
    "react": {
        "files": {
            "public/index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>{project_name}</title>\n</head>\n<body>\n  <div id="root"></div>\n</body>\n</html>\n',
            "src/App.js": 'import React from "react";\n\nfunction App() {{\n  return (\n    <div className="App">\n      <h1>{project_name}</h1>\n      <p>Welcome to your React app.</p>\n    </div>\n  );\n}}\n\nexport default App;\n',
            "src/index.js": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n\nconst root = ReactDOM.createRoot(document.getElementById("root"));\nroot.render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n',
            "package.json": '{{\n  "name": "{project_name_lower}",\n  "version": "1.0.0",\n  "dependencies": {{\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0",\n    "react-scripts": "5.0.1"\n  }},\n  "scripts": {{\n    "start": "react-scripts start",\n    "build": "react-scripts build",\n    "test": "react-scripts test"\n  }}\n}}\n',
            ".gitignore": "node_modules/\nbuild/\n.env\ncoverage/\n",
            "README.md": "# {project_name}\n\nReact application.\n\n## Setup\n\n```bash\nnpm install\nnpm start\n```\n",
        },
        "folders": ["src/components", "src/hooks", "src/utils", "public"],
    },
    "html": {
        "files": {
            "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>{project_name}</title>\n  <link rel="stylesheet" href="css/style.css">\n</head>\n<body>\n  <header>\n    <h1>{project_name}</h1>\n  </header>\n  <main>\n    <p>Welcome to {project_name}.</p>\n  </main>\n  <script src="js/main.js"></script>\n</body>\n</html>\n',
            "css/style.css": "* {{\n  margin: 0;\n  padding: 0;\n  box-sizing: border-box;\n}}\n\nbody {{\n  font-family: system-ui, sans-serif;\n  line-height: 1.6;\n  color: #333;\n  max-width: 1200px;\n  margin: 0 auto;\n  padding: 2rem;\n}}\n\nheader {{\n  margin-bottom: 2rem;\n}}\n",
            "js/main.js": '// Main JavaScript file\nconsole.log("{project_name} loaded");\n',
            "README.md": "# {project_name}\n\nStatic HTML/CSS/JS project.\n\n## Usage\n\nOpen `index.html` in a browser.\n",
        },
        "folders": ["css", "js", "assets"],
    },
}

# --- Code Templates ---
CODE_TEMPLATES = {
    # Python templates
    "python:class": 'class {name}:\n    """{description}"""\n\n    def __init__(self):\n        pass\n\n    def __repr__(self):\n        return f"{name}()"\n',
    "python:dataclass": 'from dataclasses import dataclass\n\n\n@dataclass\nclass {name}:\n    """{description}"""\n    pass\n',
    "python:function": 'def {name}():\n    """{description}"""\n    pass\n',
    "python:test": 'import unittest\n\n\nclass Test{name}(unittest.TestCase):\n    """{description}"""\n\n    def setUp(self):\n        pass\n\n    def test_example(self):\n        self.assertTrue(True)\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
    "python:script": '#!/usr/bin/env python3\n"""{description}"""\nimport argparse\n\n\ndef main():\n    parser = argparse.ArgumentParser(description="{description}")\n    args = parser.parse_args()\n    print("Running {name}...")\n\n\nif __name__ == "__main__":\n    main()\n',
    "python:flask_blueprint": 'from flask import Blueprint, jsonify, request\n\n{name}_bp = Blueprint("{name}", __name__)\n\n\n@{name}_bp.route("/{name}", methods=["GET"])\ndef get_{name}():\n    return jsonify({{"message": "GET /{name}"}})\n\n\n@{name}_bp.route("/{name}", methods=["POST"])\ndef create_{name}():\n    data = request.get_json()\n    return jsonify({{"message": "POST /{name}", "data": data}}), 201\n',
    "python:fastapi_router": 'from fastapi import APIRouter, HTTPException\n\nrouter = APIRouter(prefix="/{name}", tags=["{name}"])\n\n\n@router.get("/")\nasync def list_{name}():\n    return {{"items": []}}\n\n\n@router.get("/{{item_id}}")\nasync def get_{name}(item_id: int):\n    return {{"id": item_id}}\n\n\n@router.post("/")\nasync def create_{name}(data: dict):\n    return {{"message": "created", "data": data}}\n',
    # JavaScript templates
    "javascript:class": 'class {name} {{\n  /**\n   * {description}\n   */\n  constructor() {{\n  }}\n}}\n\nmodule.exports = {name};\n',
    "javascript:function": '/**\n * {description}\n */\nfunction {name}() {{\n}}\n\nmodule.exports = {name};\n',
    "javascript:express_router": 'const express = require("express");\nconst router = express.Router();\n\nrouter.get("/", (req, res) => {{\n  res.json({{ message: "GET /{name}" }});\n}});\n\nrouter.post("/", (req, res) => {{\n  const data = req.body;\n  res.status(201).json({{ message: "POST /{name}", data }});\n}});\n\nrouter.get("/:id", (req, res) => {{\n  res.json({{ id: req.params.id }});\n}});\n\nmodule.exports = router;\n',
    "javascript:react_component": 'import React from "react";\n\nfunction {name}() {{\n  return (\n    <div className="{name}">\n      <h2>{name}</h2>\n    </div>\n  );\n}}\n\nexport default {name};\n',
    "javascript:test": 'const {{ describe, it, expect }} = require("@jest/globals");\n\ndescribe("{name}", () => {{\n  it("should work", () => {{\n    expect(true).toBe(true);\n  }});\n}});\n',
    # HTML templates
    "html:page": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>{name}</title>\n</head>\n<body>\n  <h1>{name}</h1>\n  <p>{description}</p>\n</body>\n</html>\n',
    "html:form": '<form action="" method="POST">\n  <fieldset>\n    <legend>{name}</legend>\n    <div>\n      <label for="field1">Field 1</label>\n      <input type="text" id="field1" name="field1" required>\n    </div>\n    <button type="submit">Submit</button>\n  </fieldset>\n</form>\n',
}

# --- Section Implementation Templates ---
SECTION_TEMPLATES = {
    "backend": {
        "python": {
            "description": "Python backend with REST API structure",
            "files": {
                "app.py": '"""Application entry point"""\nfrom flask import Flask\nfrom routes import register_routes\nfrom config import Config\n\n\ndef create_app():\n    app = Flask(__name__)\n    app.config.from_object(Config)\n    register_routes(app)\n    return app\n\n\nif __name__ == "__main__":\n    app = create_app()\n    app.run(debug=True)\n',
                "config.py": '"""Application configuration"""\nimport os\n\n\nclass Config:\n    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")\n    DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite:///app.db")\n    DEBUG = os.environ.get("DEBUG", "True").lower() == "true"\n',
                "routes/__init__.py": '"""Route registration"""\nfrom routes.api import api_bp\n\n\ndef register_routes(app):\n    app.register_blueprint(api_bp, url_prefix="/api")\n',
                "routes/api.py": '"""API routes"""\nfrom flask import Blueprint, jsonify, request\n\napi_bp = Blueprint("api", __name__)\n\n\n@api_bp.route("/health")\ndef health():\n    return jsonify({{"status": "healthy"}})\n\n\n@api_bp.route("/items", methods=["GET"])\ndef list_items():\n    return jsonify({{"items": []}})\n\n\n@api_bp.route("/items", methods=["POST"])\ndef create_item():\n    data = request.get_json()\n    return jsonify({{"message": "created", "data": data}}), 201\n',
                "models/__init__.py": '"""Database models"""\n',
                "models/base.py": '"""Base model"""\nfrom datetime import datetime\n\n\nclass BaseModel:\n    created_at = None\n    updated_at = None\n\n    def to_dict(self):\n        return {{k: v for k, v in self.__dict__.items() if not k.startswith("_")}}\n',
                "services/__init__.py": '"""Business logic services"""\n',
                "utils/__init__.py": '"""Utility functions"""\n',
                "requirements.txt": "flask\npython-dotenv\n",
            },
            "folders": ["routes", "models", "services", "utils", "tests"],
        },
        "node": {
            "description": "Node.js backend with Express REST API structure",
            "files": {
                "index.js": 'const express = require("express");\nconst {{ config }} = require("./config");\nconst {{ registerRoutes }} = require("./routes");\n\nconst app = express();\n\napp.use(express.json());\nregisterRoutes(app);\n\napp.listen(config.port, () => {{\n  console.log(`Server running on port ${{config.port}}`);\n}});\n',
                "config/index.js": 'const config = {{\n  port: process.env.PORT || 3000,\n  env: process.env.NODE_ENV || "development",\n}};\n\nmodule.exports = {{ config }};\n',
                "routes/index.js": 'const apiRoutes = require("./api");\n\nfunction registerRoutes(app) {{\n  app.use("/api", apiRoutes);\n}}\n\nmodule.exports = {{ registerRoutes }};\n',
                "routes/api.js": 'const express = require("express");\nconst router = express.Router();\n\nrouter.get("/health", (req, res) => {{\n  res.json({{ status: "healthy" }});\n}});\n\nrouter.get("/items", (req, res) => {{\n  res.json({{ items: [] }});\n}});\n\nrouter.post("/items", (req, res) => {{\n  const data = req.body;\n  res.status(201).json({{ message: "created", data }});\n}});\n\nmodule.exports = router;\n',
                "models/.gitkeep": "",
                "services/.gitkeep": "",
                "package.json": '{{\n  "name": "{project_name_lower}",\n  "version": "1.0.0",\n  "main": "index.js",\n  "scripts": {{\n    "start": "node index.js",\n    "dev": "node --watch index.js"\n  }},\n  "dependencies": {{\n    "express": "^4.18.0"\n  }}\n}}\n',
            },
            "folders": ["routes", "models", "services", "middleware", "config", "tests"],
        },
    },
    "frontend": {
        "react": {
            "description": "React frontend with component structure",
            "files": {
                "public/index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>{project_name}</title>\n</head>\n<body>\n  <div id="root"></div>\n</body>\n</html>\n',
                "src/App.js": 'import React from "react";\nimport Header from "./components/Header";\nimport Home from "./pages/Home";\n\nfunction App() {{\n  return (\n    <div className="App">\n      <Header />\n      <main>\n        <Home />\n      </main>\n    </div>\n  );\n}}\n\nexport default App;\n',
                "src/index.js": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\nimport "./styles/global.css";\n\nconst root = ReactDOM.createRoot(document.getElementById("root"));\nroot.render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n',
                "src/components/Header.js": 'import React from "react";\n\nfunction Header() {{\n  return (\n    <header>\n      <nav>\n        <h1>{project_name}</h1>\n      </nav>\n    </header>\n  );\n}}\n\nexport default Header;\n',
                "src/pages/Home.js": 'import React from "react";\n\nfunction Home() {{\n  return (\n    <div>\n      <h2>Welcome to {project_name}</h2>\n      <p>Start building your app.</p>\n    </div>\n  );\n}}\n\nexport default Home;\n',
                "src/styles/global.css": "* {{\n  margin: 0;\n  padding: 0;\n  box-sizing: border-box;\n}}\n\nbody {{\n  font-family: system-ui, sans-serif;\n  line-height: 1.6;\n  color: #333;\n}}\n\nnav {{\n  background: #282828;\n  color: #ebdbb2;\n  padding: 1rem 2rem;\n}}\n\nmain {{\n  padding: 2rem;\n  max-width: 1200px;\n  margin: 0 auto;\n}}\n",
                "src/utils/api.js": 'const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000/api";\n\nexport async function fetchAPI(endpoint, options = {{}}) {{\n  const response = await fetch(`${{API_BASE}}${{endpoint}}`, {{\n    headers: {{ "Content-Type": "application/json", ...options.headers }},\n    ...options,\n  }});\n  if (!response.ok) throw new Error(`API error: ${{response.status}}`);\n  return response.json();\n}}\n',
                "package.json": '{{\n  "name": "{project_name_lower}",\n  "version": "1.0.0",\n  "dependencies": {{\n    "react": "^18.2.0",\n    "react-dom": "^18.2.0",\n    "react-scripts": "5.0.1"\n  }},\n  "scripts": {{\n    "start": "react-scripts start",\n    "build": "react-scripts build",\n    "test": "react-scripts test"\n  }}\n}}\n',
            },
            "folders": ["public", "src/components", "src/pages", "src/hooks", "src/utils", "src/styles"],
        },
        "html": {
            "description": "Static HTML/CSS/JS frontend",
            "files": {
                "index.html": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>{project_name}</title>\n  <link rel="stylesheet" href="css/style.css">\n</head>\n<body>\n  <header>\n    <nav>\n      <h1>{project_name}</h1>\n      <ul>\n        <li><a href="index.html">Home</a></li>\n        <li><a href="about.html">About</a></li>\n      </ul>\n    </nav>\n  </header>\n  <main>\n    <section class="hero">\n      <h2>Welcome</h2>\n      <p>Start building your site.</p>\n    </section>\n  </main>\n  <footer>\n    <p>&copy; {project_name}</p>\n  </footer>\n  <script src="js/main.js"></script>\n</body>\n</html>\n',
                "css/style.css": "* {{\n  margin: 0;\n  padding: 0;\n  box-sizing: border-box;\n}}\n\nbody {{\n  font-family: system-ui, sans-serif;\n  line-height: 1.6;\n  color: #333;\n}}\n\nnav {{\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  padding: 1rem 2rem;\n  background: #282828;\n  color: #ebdbb2;\n}}\n\nnav ul {{\n  display: flex;\n  list-style: none;\n  gap: 1rem;\n}}\n\nnav a {{\n  color: #8ec07c;\n  text-decoration: none;\n}}\n\nmain {{\n  padding: 2rem;\n  max-width: 1200px;\n  margin: 0 auto;\n}}\n\n.hero {{\n  text-align: center;\n  padding: 4rem 2rem;\n}}\n\nfooter {{\n  text-align: center;\n  padding: 2rem;\n  background: #f5f5f5;\n}}\n",
                "js/main.js": '// Main JavaScript\nconsole.log("{project_name} loaded");\n',
            },
            "folders": ["css", "js", "assets", "images"],
        },
    },
    "database": {
        "sql": {
            "description": "SQL database schema and migration structure",
            "files": {
                "schema.sql": "-- Database Schema\n-- Generated for {project_name}\n\nCREATE TABLE IF NOT EXISTS users (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    username VARCHAR(50) UNIQUE NOT NULL,\n    email VARCHAR(100) UNIQUE NOT NULL,\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\nCREATE TABLE IF NOT EXISTS items (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    name VARCHAR(100) NOT NULL,\n    description TEXT,\n    user_id INTEGER,\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n    FOREIGN KEY (user_id) REFERENCES users(id)\n);\n",
                "seed.sql": "-- Seed Data\n\nINSERT INTO users (username, email) VALUES\n    ('admin', 'admin@example.com'),\n    ('user1', 'user1@example.com');\n",
                "migrations/001_initial.sql": "-- Migration 001: Initial Schema\n-- Run: sqlite3 app.db < migrations/001_initial.sql\n\nCREATE TABLE IF NOT EXISTS users (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    username VARCHAR(50) UNIQUE NOT NULL,\n    email VARCHAR(100) UNIQUE NOT NULL,\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n",
            },
            "folders": ["migrations"],
        },
    },
    "api": {
        "rest": {
            "description": "REST API structure with routes and middleware",
            "files": {
                "routes/index.py": '"""API route index"""\n\nROUTES = [\n    {{"path": "/api/health", "method": "GET", "handler": "health_check"}},\n    {{"path": "/api/items", "method": "GET", "handler": "list_items"}},\n    {{"path": "/api/items", "method": "POST", "handler": "create_item"}},\n    {{"path": "/api/items/<id>", "method": "GET", "handler": "get_item"}},\n    {{"path": "/api/items/<id>", "method": "PUT", "handler": "update_item"}},\n    {{"path": "/api/items/<id>", "method": "DELETE", "handler": "delete_item"}},\n]\n',
                "middleware/auth.py": '"""Authentication middleware"""\n\n\ndef require_auth(f):\n    """Decorator to require authentication"""\n    def decorated(*args, **kwargs):\n        # Add authentication logic here\n        return f(*args, **kwargs)\n    decorated.__name__ = f.__name__\n    return decorated\n',
                "middleware/cors.py": '"""CORS middleware"""\n\n\ndef add_cors_headers(response):\n    """Add CORS headers to response"""\n    response.headers["Access-Control-Allow-Origin"] = "*"\n    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"\n    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"\n    return response\n',
            },
            "folders": ["routes", "middleware", "validators"],
        },
    },
    "testing": {
        "python": {
            "description": "Python testing structure with unittest",
            "files": {
                "tests/__init__.py": "",
                "tests/conftest.py": '"""Test configuration and fixtures"""\nimport sys\nimport os\n\n# Add project root to path\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n',
                "tests/test_example.py": '"""Example test module"""\nimport unittest\n\n\nclass TestExample(unittest.TestCase):\n    def setUp(self):\n        pass\n\n    def test_sanity(self):\n        self.assertTrue(True)\n\n    def tearDown(self):\n        pass\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
            },
            "folders": ["tests", "tests/fixtures"],
        },
        "javascript": {
            "description": "JavaScript testing structure with Jest",
            "files": {
                "tests/example.test.js": 'describe("Example Test Suite", () => {{\n  test("sanity check", () => {{\n    expect(true).toBe(true);\n  }});\n}});\n',
                "jest.config.js": 'module.exports = {{\n  testEnvironment: "node",\n  testMatch: ["**/tests/**/*.test.js"],\n  coverageDirectory: "coverage",\n}};\n',
            },
            "folders": ["tests", "tests/fixtures"],
        },
    },
}


def generate_template(template_type: str, name: str = "Component", description: str = "") -> Dict[str, Any]:
    """Generate code from a template"""
    try:
        if not description:
            description = f"{name} implementation"

        if template_type not in CODE_TEMPLATES:
            available = list(CODE_TEMPLATES.keys())
            return {
                "success": False,
                "error": f"Unknown template: {template_type}",
                "available_templates": available
            }

        template = CODE_TEMPLATES[template_type]
        code = template.format(name=name, description=description)

        return {
            "success": True,
            "template_type": template_type,
            "name": name,
            "code": code,
            "language": template_type.split(":")[0]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_templates() -> Dict[str, Any]:
    """List all available code and project templates"""
    try:
        code_templates = {}
        for key in CODE_TEMPLATES:
            lang, ttype = key.split(":", 1)
            if lang not in code_templates:
                code_templates[lang] = []
            code_templates[lang].append(ttype)

        project_templates = list(PROJECT_TEMPLATES.keys())

        sections = {}
        for section, techs in SECTION_TEMPLATES.items():
            sections[section] = list(techs.keys())

        return {
            "success": True,
            "code_templates": code_templates,
            "project_templates": project_templates,
            "section_templates": sections
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def scaffold_project(project_name: str, template: str, directory: str = ".") -> Dict[str, Any]:
    """Scaffold a new project from a template"""
    try:
        if template not in PROJECT_TEMPLATES:
            return {
                "success": False,
                "error": f"Unknown template: {template}",
                "available_templates": list(PROJECT_TEMPLATES.keys())
            }

        directory = resolve_path(directory)
        project_dir = os.path.join(directory, project_name)

        if os.path.exists(project_dir):
            return {"success": False, "error": f"Directory already exists: {project_dir}"}

        tmpl = PROJECT_TEMPLATES[template]
        project_name_lower = project_name.lower().replace(" ", "-")

        # Create project directory
        os.makedirs(project_dir, exist_ok=True)

        # Create folders
        created_folders = []
        for folder in tmpl.get("folders", []):
            folder_path = os.path.join(project_dir, folder)
            os.makedirs(folder_path, exist_ok=True)
            created_folders.append(folder)

        # Create files
        created_files = []
        for filepath, content in tmpl.get("files", {}).items():
            content = content.format(
                project_name=project_name,
                project_name_lower=project_name_lower
            )
            full_path = os.path.join(project_dir, filepath)
            parent = os.path.dirname(full_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            created_files.append(filepath)

        return {
            "success": True,
            "project_name": project_name,
            "template": template,
            "project_dir": project_dir,
            "files_created": created_files,
            "folders_created": created_folders
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def implement_section(section: str, tech: str, project_name: str, directory: str = ".") -> Dict[str, Any]:
    """Implement a complete project section (backend, frontend, database, etc.)"""
    try:
        if section not in SECTION_TEMPLATES:
            return {
                "success": False,
                "error": f"Unknown section: {section}",
                "available_sections": list(SECTION_TEMPLATES.keys())
            }

        techs = SECTION_TEMPLATES[section]
        if tech not in techs:
            return {
                "success": False,
                "error": f"Unknown tech '{tech}' for section '{section}'",
                "available_techs": list(techs.keys())
            }

        directory = resolve_path(directory)
        section_dir = os.path.join(directory, section)
        tmpl = techs[tech]
        project_name_lower = project_name.lower().replace(" ", "-")

        # Create section directory
        os.makedirs(section_dir, exist_ok=True)

        # Create folders
        created_folders = []
        for folder in tmpl.get("folders", []):
            folder_path = os.path.join(section_dir, folder)
            os.makedirs(folder_path, exist_ok=True)
            created_folders.append(folder)

        # Create files
        created_files = []
        for filepath, content in tmpl.get("files", {}).items():
            content = content.format(
                project_name=project_name,
                project_name_lower=project_name_lower
            )
            full_path = os.path.join(section_dir, filepath)
            parent = os.path.dirname(full_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            created_files.append(filepath)

        return {
            "success": True,
            "section": section,
            "tech": tech,
            "description": tmpl.get("description", ""),
            "section_dir": section_dir,
            "files_created": created_files,
            "folders_created": created_folders
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_code(prompt: str, language: str = "python") -> Dict[str, Any]:
    """Generate code using LLM based on a natural language prompt"""
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return {"success": False, "error": "GROQ_API_KEY not set"}

        from groq import Groq
        client = Groq(api_key=api_key)

        system_prompt = f"""You are an expert {language} developer. Generate clean, well-structured, production-ready code.

Rules:
- Write ONLY code, no explanations before or after
- Include necessary imports
- Add brief docstrings/comments for clarity
- Follow {language} best practices and conventions
- Make the code complete and runnable"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate {language} code for: {prompt}"}
            ],
            max_tokens=3000,
            temperature=0.3
        )

        content = response.choices[0].message.content
        return {
            "success": True,
            "code": content,
            "language": language,
            "prompt": prompt
        }
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
    
    # Development tools
    mcp.register_tool("generate_template", "Generate code from a template (e.g., python:class, javascript:function)", ToolCategory.DEVELOPMENT,
                      {"template_type": "string", "name": "string", "description": "string"}, ["template_type", "name"], generate_template)
    mcp.register_tool("list_templates", "List all available code and project templates", ToolCategory.DEVELOPMENT,
                      {}, [], list_templates)
    mcp.register_tool("scaffold_project", "Scaffold a new project from a template (python, node, react, etc.)", ToolCategory.DEVELOPMENT,
                      {"project_name": "string", "template": "string", "directory": "string"}, ["project_name", "template"], scaffold_project)
    mcp.register_tool("implement_section", "Implement a complete project section (backend, frontend, database, api, testing)", ToolCategory.DEVELOPMENT,
                      {"section": "string", "tech": "string", "project_name": "string", "directory": "string"}, ["section", "tech", "project_name"], implement_section)
    mcp.register_tool("generate_code", "Generate code using AI from a natural language description", ToolCategory.DEVELOPMENT,
                      {"prompt": "string", "language": "string"}, ["prompt"], generate_code)

    print(f"[MCP] Registered {len(mcp.tools)} tools")
