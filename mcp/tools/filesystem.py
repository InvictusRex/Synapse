"""
Filesystem Tools - Full file and folder operations
Allows reading, writing, creating, moving, copying files and folders
"""
import os
import shutil
from typing import Dict, Any, List
from datetime import datetime


def read_file(filepath: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Read content from any file on the system"""
    try:
        filepath = os.path.expanduser(filepath)  # Handle ~ for home directory
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        if not os.path.isfile(filepath):
            return {"success": False, "error": f"Not a file: {filepath}"}
        
        # Get file info
        file_stats = os.stat(filepath)
        file_info = {
            "size_bytes": file_stats.st_size,
            "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat()
        }
        
        # Read content
        with open(filepath, 'r', encoding=encoding) as f:
            content = f.read()
        
        return {
            "success": True, 
            "content": content,
            "filepath": filepath,
            "info": file_info
        }
    except UnicodeDecodeError:
        return {"success": False, "error": f"Cannot read file as text. May be a binary file."}
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {filepath}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(filepath: str, content: str, create_dirs: bool = True, encoding: str = "utf-8") -> Dict[str, Any]:
    """Write content to any file location on the system"""
    try:
        filepath = os.path.expanduser(filepath)
        
        # Create parent directories if needed
        if create_dirs:
            parent_dir = os.path.dirname(filepath)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
        
        # Write content
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "filepath": os.path.abspath(filepath),
            "size_bytes": len(content.encode(encoding))
        }
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {filepath}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def append_to_file(filepath: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Append content to an existing file"""
    try:
        filepath = os.path.expanduser(filepath)
        
        with open(filepath, 'a', encoding=encoding) as f:
            f.write(content)
        
        return {
            "success": True,
            "filepath": os.path.abspath(filepath),
            "appended_bytes": len(content.encode(encoding))
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_folder(folder_path: str) -> Dict[str, Any]:
    """Create a new folder/directory"""
    try:
        folder_path = os.path.expanduser(folder_path)
        
        if os.path.exists(folder_path):
            return {"success": True, "message": "Folder already exists", "path": folder_path}
        
        os.makedirs(folder_path, exist_ok=True)
        
        return {
            "success": True,
            "path": os.path.abspath(folder_path),
            "message": "Folder created successfully"
        }
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {folder_path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_directory(directory: str, include_hidden: bool = False) -> Dict[str, Any]:
    """List contents of a directory"""
    try:
        directory = os.path.expanduser(directory)
        
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        
        if not os.path.isdir(directory):
            return {"success": False, "error": f"Not a directory: {directory}"}
        
        items = []
        for item in os.listdir(directory):
            if not include_hidden and item.startswith('.'):
                continue
            
            item_path = os.path.join(directory, item)
            item_stat = os.stat(item_path)
            
            items.append({
                "name": item,
                "type": "folder" if os.path.isdir(item_path) else "file",
                "size_bytes": item_stat.st_size,
                "modified": datetime.fromtimestamp(item_stat.st_mtime).isoformat()
            })
        
        # Sort: folders first, then files
        items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
        
        return {
            "success": True,
            "directory": os.path.abspath(directory),
            "items": items,
            "total_items": len(items)
        }
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {directory}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_file(filepath: str) -> Dict[str, Any]:
    """Delete a file"""
    try:
        filepath = os.path.expanduser(filepath)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        if os.path.isdir(filepath):
            return {"success": False, "error": f"Use delete_folder for directories: {filepath}"}
        
        os.remove(filepath)
        
        return {
            "success": True,
            "deleted": filepath,
            "message": "File deleted successfully"
        }
    except PermissionError:
        return {"success": False, "error": f"Permission denied: {filepath}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_folder(folder_path: str, recursive: bool = False) -> Dict[str, Any]:
    """Delete a folder (optionally with all contents)"""
    try:
        folder_path = os.path.expanduser(folder_path)
        
        if not os.path.exists(folder_path):
            return {"success": False, "error": f"Folder not found: {folder_path}"}
        
        if not os.path.isdir(folder_path):
            return {"success": False, "error": f"Not a folder: {folder_path}"}
        
        if recursive:
            shutil.rmtree(folder_path)
        else:
            os.rmdir(folder_path)  # Only works if empty
        
        return {
            "success": True,
            "deleted": folder_path,
            "message": "Folder deleted successfully"
        }
    except OSError as e:
        if "not empty" in str(e).lower() or "directory not empty" in str(e).lower():
            return {"success": False, "error": "Folder is not empty. Set recursive=True to delete with contents."}
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move a file or folder to a new location"""
    try:
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        
        if not os.path.exists(source):
            return {"success": False, "error": f"Source not found: {source}"}
        
        # Create destination directory if needed
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        shutil.move(source, destination)
        
        return {
            "success": True,
            "source": source,
            "destination": os.path.abspath(destination),
            "message": "Moved successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def copy_file(source: str, destination: str) -> Dict[str, Any]:
    """Copy a file to a new location"""
    try:
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        
        if not os.path.exists(source):
            return {"success": False, "error": f"Source not found: {source}"}
        
        # Create destination directory if needed
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        
        return {
            "success": True,
            "source": source,
            "destination": os.path.abspath(destination),
            "message": "Copied successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_file_info(filepath: str) -> Dict[str, Any]:
    """Get detailed information about a file"""
    try:
        filepath = os.path.expanduser(filepath)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": f"Path not found: {filepath}"}
        
        stat = os.stat(filepath)
        
        info = {
            "success": True,
            "path": os.path.abspath(filepath),
            "name": os.path.basename(filepath),
            "type": "folder" if os.path.isdir(filepath) else "file",
            "size_bytes": stat.st_size,
            "size_human": _format_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
        }
        
        if os.path.isfile(filepath):
            _, ext = os.path.splitext(filepath)
            info["extension"] = ext.lower()
        
        return info
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_files(directory: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
    """Search for files matching a pattern"""
    import fnmatch
    
    try:
        directory = os.path.expanduser(directory)
        
        if not os.path.exists(directory):
            return {"success": False, "error": f"Directory not found: {directory}"}
        
        matches = []
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                for filename in fnmatch.filter(files, pattern):
                    matches.append(os.path.join(root, filename))
        else:
            for item in os.listdir(directory):
                if fnmatch.fnmatch(item, pattern):
                    matches.append(os.path.join(directory, item))
        
        return {
            "success": True,
            "pattern": pattern,
            "directory": directory,
            "matches": matches,
            "count": len(matches)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _format_size(size_bytes: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"
