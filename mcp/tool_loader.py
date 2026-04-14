"""
Tool implementations and registration for the MCP system
This file contains core AI tools and registers all tools from submodules
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from duckduckgo_search import DDGS
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL, LLM_PROVIDER
except ImportError:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GROQ_MODEL = "llama-3.1-8b-instant"
    GEMINI_MODEL = "gemini-1.5-flash"
    LLM_PROVIDER = "gemini" if GEMINI_API_KEY else "groq"


# Initialize clients
groq_client = None
gemini_model = None

def get_groq_client():
    global groq_client
    if groq_client is None and GROQ_API_KEY:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
    return groq_client

def get_gemini_model():
    global gemini_model
    if gemini_model is None and GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    return gemini_model


# ============ CORE AI TOOLS ============

def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web using DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", "")
            })
        
        return {
            "query": query,
            "results": formatted,
            "count": len(formatted)
        }
    except Exception as e:
        return {"query": query, "results": [], "error": str(e)}


def generate_text(prompt: str, max_tokens: int = 1000) -> str:
    """Generate text using LLM (supports both Groq and Gemini)"""
    
    if GEMINI_API_KEY:
        try:
            model = get_gemini_model()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"[Gemini Error]: {e}")
    
    if GROQ_API_KEY:
        try:
            client = get_groq_client()
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[Error generating text: {e}]"
    
    return "[Error: No API key set. Set GEMINI_API_KEY or GROQ_API_KEY]"


def summarize_text(text: str, style: str = "bullet_points") -> str:
    """Summarize text into key points"""
    if style == "bullet_points":
        prompt = f"Summarize the following into clear bullet points:\n\n{text}"
    else:
        prompt = f"Write a concise summary of:\n\n{text}"
    
    return generate_text(prompt, max_tokens=500)


def generate_report(topic: str, context: str = "") -> str:
    """Generate a structured report on a topic"""
    prompt = f"""Write a professional report on: {topic}

Additional context: {context if context else 'None provided'}

Structure the report with:
1. Executive Summary
2. Key Findings
3. Analysis
4. Conclusions

Keep it concise but informative."""
    
    return generate_text(prompt, max_tokens=1500)


# ============ REGISTER ALL TOOLS ============

def register_all_tools():
    """Register all tools with the MCP registry"""
    from mcp.registry import get_registry
    
    # Import all tool modules
    from mcp.tools import filesystem
    from mcp.tools import pdf_tools
    from mcp.tools import image_tools
    from mcp.tools import email_tools
    from mcp.tools import http_tools
    from mcp.tools import database_tools
    from mcp.tools import data_tools
    from mcp.tools import code_tools
    
    registry = get_registry()
    
    # ==================== AI TOOLS ====================
    registry.register(
        name="web_search",
        description="Search the web for information on any topic",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (default 5)"}
            },
            "required": ["query"]
        },
        handler=web_search
    )
    
    registry.register(
        name="generate_text",
        description="Generate text content using AI",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt for text generation"},
                "max_tokens": {"type": "integer", "description": "Maximum tokens"}
            },
            "required": ["prompt"]
        },
        handler=generate_text
    )
    
    registry.register(
        name="summarize_text",
        description="Summarize text into key points or a brief summary",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"},
                "style": {"type": "string", "description": "Style: bullet_points or paragraph"}
            },
            "required": ["text"]
        },
        handler=summarize_text
    )
    
    registry.register(
        name="generate_report",
        description="Generate a structured report on a topic",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic for the report"},
                "context": {"type": "string", "description": "Additional context"}
            },
            "required": ["topic"]
        },
        handler=generate_report
    )
    
    # ==================== FILESYSTEM TOOLS ====================
    registry.register(
        name="read_file",
        description="Read content from any file on the system",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Full path to the file (use ~ for home directory)"}
            },
            "required": ["filepath"]
        },
        handler=filesystem.read_file
    )
    
    registry.register(
        name="write_file",
        description="Write content to any file location on the system",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Full path for the output file"},
                "content": {"type": "string", "description": "Content to write"},
                "create_dirs": {"type": "boolean", "description": "Create parent directories if needed (default true)"}
            },
            "required": ["filepath", "content"]
        },
        handler=filesystem.write_file
    )
    
    registry.register(
        name="create_folder",
        description="Create a new folder/directory at any location",
        parameters={
            "type": "object",
            "properties": {
                "folder_path": {"type": "string", "description": "Full path for the new folder"}
            },
            "required": ["folder_path"]
        },
        handler=filesystem.create_folder
    )
    
    registry.register(
        name="list_directory",
        description="List contents of a directory",
        parameters={
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory path to list"},
                "include_hidden": {"type": "boolean", "description": "Include hidden files (default false)"}
            },
            "required": ["directory"]
        },
        handler=filesystem.list_directory
    )
    
    registry.register(
        name="delete_file",
        description="Delete a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to file to delete"}
            },
            "required": ["filepath"]
        },
        handler=filesystem.delete_file
    )
    
    registry.register(
        name="delete_folder",
        description="Delete a folder (optionally with all contents)",
        parameters={
            "type": "object",
            "properties": {
                "folder_path": {"type": "string", "description": "Path to folder to delete"},
                "recursive": {"type": "boolean", "description": "Delete contents recursively (default false)"}
            },
            "required": ["folder_path"]
        },
        handler=filesystem.delete_folder
    )
    
    registry.register(
        name="move_file",
        description="Move a file or folder to a new location",
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"}
            },
            "required": ["source", "destination"]
        },
        handler=filesystem.move_file
    )
    
    registry.register(
        name="copy_file",
        description="Copy a file to a new location",
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"}
            },
            "required": ["source", "destination"]
        },
        handler=filesystem.copy_file
    )
    
    registry.register(
        name="get_file_info",
        description="Get detailed information about a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to the file"}
            },
            "required": ["filepath"]
        },
        handler=filesystem.get_file_info
    )
    
    registry.register(
        name="search_files",
        description="Search for files matching a pattern",
        parameters={
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory to search in"},
                "pattern": {"type": "string", "description": "File pattern (e.g., *.txt, *.py)"},
                "recursive": {"type": "boolean", "description": "Search subdirectories (default true)"}
            },
            "required": ["directory", "pattern"]
        },
        handler=filesystem.search_files
    )
    
    # ==================== PDF TOOLS ====================
    registry.register(
        name="read_pdf",
        description="Read text content from a PDF file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to PDF file"},
                "pages": {"type": "string", "description": "Pages to read: 'all' or '1,2,5' or '1-5'"}
            },
            "required": ["filepath"]
        },
        handler=pdf_tools.read_pdf
    )
    
    registry.register(
        name="get_pdf_info",
        description="Get metadata and info about a PDF file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to PDF file"}
            },
            "required": ["filepath"]
        },
        handler=pdf_tools.get_pdf_info
    )
    
    registry.register(
        name="extract_pdf_tables",
        description="Extract tables from a PDF file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to PDF file"},
                "page_number": {"type": "integer", "description": "Specific page number (optional)"}
            },
            "required": ["filepath"]
        },
        handler=pdf_tools.extract_pdf_tables
    )
    
    # ==================== IMAGE TOOLS ====================
    registry.register(
        name="generate_image",
        description="Generate an AI image from a text description (free, no API key needed)",
        parameters={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Description of the image to generate"},
                "filename": {"type": "string", "description": "Output filename (optional)"},
                "width": {"type": "integer", "description": "Image width (default 1024)"},
                "height": {"type": "integer", "description": "Image height (default 1024)"}
            },
            "required": ["prompt"]
        },
        handler=image_tools.generate_image
    )
    
    registry.register(
        name="resize_image",
        description="Resize an image",
        parameters={
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Input image path"},
                "output_path": {"type": "string", "description": "Output image path"},
                "width": {"type": "integer", "description": "New width"},
                "height": {"type": "integer", "description": "New height"}
            },
            "required": ["input_path", "output_path"]
        },
        handler=image_tools.resize_image
    )
    
    registry.register(
        name="convert_image",
        description="Convert image to a different format",
        parameters={
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Input image path"},
                "output_path": {"type": "string", "description": "Output path with new extension"}
            },
            "required": ["input_path", "output_path"]
        },
        handler=image_tools.convert_image
    )
    
    registry.register(
        name="get_image_info",
        description="Get information about an image file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to image file"}
            },
            "required": ["filepath"]
        },
        handler=image_tools.get_image_info
    )
    
    # ==================== EMAIL TOOLS ====================
    registry.register(
        name="send_email",
        description="Send an email (requires SMTP configuration via environment variables)",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
                "html": {"type": "boolean", "description": "If true, body is treated as HTML"}
            },
            "required": ["to", "subject", "body"]
        },
        handler=email_tools.send_email
    )
    
    registry.register(
        name="check_email_config",
        description="Check if email is properly configured",
        parameters={"type": "object", "properties": {}},
        handler=email_tools.check_email_config
    )
    
    # ==================== HTTP TOOLS ====================
    registry.register(
        name="http_get",
        description="Make an HTTP GET request to any URL/API",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to request"},
                "headers": {"type": "object", "description": "Optional headers"}
            },
            "required": ["url"]
        },
        handler=http_tools.http_get
    )
    
    registry.register(
        name="http_post",
        description="Make an HTTP POST request to any URL/API",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to request"},
                "json_data": {"type": "object", "description": "JSON data to send"},
                "headers": {"type": "object", "description": "Optional headers"}
            },
            "required": ["url"]
        },
        handler=http_tools.http_post
    )
    
    registry.register(
        name="fetch_webpage",
        description="Fetch a webpage and extract readable text content",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "extract_text": {"type": "boolean", "description": "Extract readable text (default true)"}
            },
            "required": ["url"]
        },
        handler=http_tools.fetch_webpage
    )
    
    registry.register(
        name="download_file",
        description="Download a file from a URL to local disk",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to download from"},
                "save_path": {"type": "string", "description": "Local path to save the file"}
            },
            "required": ["url", "save_path"]
        },
        handler=http_tools.download_file
    )
    
    # ==================== DATABASE TOOLS ====================
    registry.register(
        name="create_database",
        description="Create a new SQLite database file",
        parameters={
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Path for the database file"}
            },
            "required": ["db_path"]
        },
        handler=database_tools.create_database
    )
    
    registry.register(
        name="execute_sql",
        description="Execute a SQL statement on a SQLite database",
        parameters={
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Path to database"},
                "sql": {"type": "string", "description": "SQL statement to execute"}
            },
            "required": ["db_path", "sql"]
        },
        handler=database_tools.execute_sql
    )
    
    registry.register(
        name="create_table",
        description="Create a table in a SQLite database",
        parameters={
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Path to database"},
                "table_name": {"type": "string", "description": "Name of the table"},
                "columns": {"type": "object", "description": "Column definitions {name: type}"}
            },
            "required": ["db_path", "table_name", "columns"]
        },
        handler=database_tools.create_table
    )
    
    registry.register(
        name="query_table",
        description="Query data from a database table",
        parameters={
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Path to database"},
                "table_name": {"type": "string", "description": "Name of the table"},
                "where": {"type": "string", "description": "Optional WHERE clause"}
            },
            "required": ["db_path", "table_name"]
        },
        handler=database_tools.query_table
    )
    
    registry.register(
        name="list_tables",
        description="List all tables in a SQLite database",
        parameters={
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "Path to database"}
            },
            "required": ["db_path"]
        },
        handler=database_tools.list_tables
    )
    
    # ==================== DATA PROCESSING TOOLS ====================
    registry.register(
        name="read_csv",
        description="Read a CSV file into structured data",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to CSV file"},
                "delimiter": {"type": "string", "description": "Column delimiter (default comma)"},
                "limit": {"type": "integer", "description": "Max rows to read (default 1000)"}
            },
            "required": ["filepath"]
        },
        handler=data_tools.read_csv
    )
    
    registry.register(
        name="write_csv",
        description="Write data to a CSV file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Output path"},
                "data": {"type": "array", "description": "List of row dictionaries"}
            },
            "required": ["filepath", "data"]
        },
        handler=data_tools.write_csv
    )
    
    registry.register(
        name="read_excel",
        description="Read an Excel file (.xlsx, .xls)",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to Excel file"},
                "sheet_name": {"type": "string", "description": "Sheet name to read (optional)"}
            },
            "required": ["filepath"]
        },
        handler=data_tools.read_excel
    )
    
    registry.register(
        name="write_excel",
        description="Write data to an Excel file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Output path"},
                "data": {"type": "array", "description": "List of row dictionaries"},
                "sheet_name": {"type": "string", "description": "Sheet name (default Sheet1)"}
            },
            "required": ["filepath", "data"]
        },
        handler=data_tools.write_excel
    )
    
    registry.register(
        name="read_word",
        description="Read a Word document (.docx)",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to Word file"}
            },
            "required": ["filepath"]
        },
        handler=data_tools.read_word
    )
    
    registry.register(
        name="write_word",
        description="Write content to a Word document",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Output path"},
                "content": {"type": "string", "description": "Document content"},
                "title": {"type": "string", "description": "Document title (optional)"}
            },
            "required": ["filepath", "content"]
        },
        handler=data_tools.write_word
    )
    
    registry.register(
        name="read_json",
        description="Read a JSON file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to JSON file"}
            },
            "required": ["filepath"]
        },
        handler=data_tools.read_json
    )
    
    registry.register(
        name="write_json",
        description="Write data to a JSON file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Output path"},
                "data": {"type": "object", "description": "Data to write"}
            },
            "required": ["filepath", "data"]
        },
        handler=data_tools.write_json
    )
    
    # ==================== CODE & UTILITY TOOLS ====================
    registry.register(
        name="execute_python",
        description="Execute Python code safely in a restricted environment",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"}
            },
            "required": ["code"]
        },
        handler=code_tools.execute_python
    )
    
    registry.register(
        name="run_shell_command",
        description="Run a shell/terminal command",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)"}
            },
            "required": ["command"]
        },
        handler=code_tools.run_shell_command
    )
    
    registry.register(
        name="calculate",
        description="Safely evaluate a mathematical expression",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression like '2 + 2 * 3' or 'sqrt(16)'"}
            },
            "required": ["expression"]
        },
        handler=code_tools.calculate
    )
    
    registry.register(
        name="get_system_info",
        description="Get information about the operating system",
        parameters={"type": "object", "properties": {}},
        handler=code_tools.get_system_info
    )
    
    registry.register(
        name="get_current_datetime",
        description="Get current date and time",
        parameters={"type": "object", "properties": {}},
        handler=code_tools.get_current_datetime
    )
    
    print(f"[MCP] Registered {len(registry.tools)} tools")
    return registry
