"""
Code Execution & Utility Tools
Execute Python code, run shell commands, and utility functions
"""
import os
import sys
import subprocess
from typing import Dict, Any
from io import StringIO
import math


def execute_python(code: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute Python code safely
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds
    
    Note: This executes in a restricted environment
    """
    try:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        # Create a restricted globals dict
        safe_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "reversed": reversed,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "any": any,
                "all": all,
                "isinstance": isinstance,
                "type": type,
            },
            "math": math,
        }
        
        local_vars = {}
        
        # Execute the code
        exec(code, safe_globals, local_vars)
        
        # Get output
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        # Get any returned variables
        result_vars = {k: v for k, v in local_vars.items() if not k.startswith('_')}
        
        return {
            "success": True,
            "output": output,
            "variables": str(result_vars) if result_vars else None
        }
        
    except Exception as e:
        sys.stdout = old_stdout
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def run_shell_command(command: str, timeout: int = 60, shell: bool = True) -> Dict[str, Any]:
    """
    Run a shell command
    
    Args:
        command: Command to execute
        timeout: Maximum execution time
        shell: Use shell execution (default True)
    
    Warning: Be careful with untrusted input
    """
    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def calculate(expression: str) -> Dict[str, Any]:
    """
    Safely evaluate a mathematical expression
    
    Args:
        expression: Math expression like "2 + 2 * 3" or "math.sqrt(16)"
    """
    try:
        # Safe math functions
        safe_dict = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            # Math module functions
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "pi": math.pi,
            "e": math.e,
            "floor": math.floor,
            "ceil": math.ceil,
            "factorial": math.factorial,
        }
        
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        
        return {
            "success": True,
            "expression": expression,
            "result": result
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_system_info() -> Dict[str, Any]:
    """Get information about the system"""
    import platform
    
    return {
        "success": True,
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "home": os.path.expanduser("~")
    }


def get_environment_variable(name: str) -> Dict[str, Any]:
    """Get an environment variable"""
    value = os.environ.get(name)
    return {
        "success": value is not None,
        "name": name,
        "value": value,
        "message": "Variable not set" if value is None else "Found"
    }


def set_working_directory(path: str) -> Dict[str, Any]:
    """Change the current working directory"""
    try:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return {"success": False, "error": f"Path not found: {path}"}
        
        if not os.path.isdir(path):
            return {"success": False, "error": f"Not a directory: {path}"}
        
        os.chdir(path)
        
        return {
            "success": True,
            "cwd": os.getcwd()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_uuid() -> Dict[str, Any]:
    """Generate a unique identifier"""
    import uuid
    return {
        "success": True,
        "uuid": str(uuid.uuid4())
    }


def get_current_datetime() -> Dict[str, Any]:
    """Get current date and time"""
    from datetime import datetime
    now = datetime.now()
    return {
        "success": True,
        "datetime": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": now.timestamp()
    }


def base64_encode(text: str) -> Dict[str, Any]:
    """Encode text to base64"""
    import base64
    try:
        encoded = base64.b64encode(text.encode()).decode()
        return {"success": True, "encoded": encoded}
    except Exception as e:
        return {"success": False, "error": str(e)}


def base64_decode(encoded: str) -> Dict[str, Any]:
    """Decode base64 text"""
    import base64
    try:
        decoded = base64.b64decode(encoded).decode()
        return {"success": True, "decoded": decoded}
    except Exception as e:
        return {"success": False, "error": str(e)}


def hash_text(text: str, algorithm: str = "sha256") -> Dict[str, Any]:
    """Generate hash of text"""
    import hashlib
    try:
        h = hashlib.new(algorithm)
        h.update(text.encode())
        return {
            "success": True,
            "algorithm": algorithm,
            "hash": h.hexdigest()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
