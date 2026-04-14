"""
Tool implementations for the MCP system
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from groq import Groq
from duckduckgo_search import DDGS
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from config import GROQ_API_KEY, LLM_MODEL
except ImportError:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    LLM_MODEL = "llama-3.1-8b-instant"


# Initialize clients
groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None and GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
    return groq_client


# ============ TOOL: Web Search ============
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


# ============ TOOL: Generate Text ============
def generate_text(prompt: str, max_tokens: int = 1000) -> str:
    """Generate text using LLM"""
    client = get_groq_client()
    if not client:
        return "[Error: GROQ_API_KEY not set]"
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Error generating text: {e}]"


# ============ TOOL: Summarize Text ============
def summarize_text(text: str, style: str = "bullet_points") -> str:
    """Summarize text into key points"""
    if style == "bullet_points":
        prompt = f"Summarize the following into clear bullet points:\n\n{text}"
    else:
        prompt = f"Write a concise summary of:\n\n{text}"
    
    return generate_text(prompt, max_tokens=500)


# ============ TOOL: Generate Report ============
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


# ============ TOOL: Save to File ============
def save_to_file(content: str, filename: str, directory: str = "./outputs") -> Dict[str, Any]:
    """Save content to a file"""
    try:
        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "filepath": filepath,
            "size": len(content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ TOOL: Read File ============
def read_file(filepath: str) -> Dict[str, Any]:
    """Read content from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ TOOL: Combine Results ============
def combine_results(results: List[str], format: str = "merged") -> str:
    """Combine multiple results into one output"""
    if format == "numbered":
        return "\n\n".join([f"{i+1}. {r}" for i, r in enumerate(results)])
    else:
        return "\n\n---\n\n".join(results)


# ============ Register All Tools ============
def register_all_tools():
    """Register all tools with the MCP registry"""
    from mcp.registry import get_registry
    
    registry = get_registry()
    
    # Web Search
    registry.register(
        name="web_search",
        description="Search the web for information on a topic",
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
    
    # Generate Text
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
    
    # Summarize
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
    
    # Generate Report
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
    
    # Save File
    registry.register(
        name="save_to_file",
        description="Save content to a file",
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Content to save"},
                "filename": {"type": "string", "description": "Output filename"}
            },
            "required": ["content", "filename"]
        },
        handler=save_to_file
    )
    
    # Read File
    registry.register(
        name="read_file",
        description="Read content from a file",
        parameters={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to the file"}
            },
            "required": ["filepath"]
        },
        handler=read_file
    )
    
    print(f"[MCP] Registered {len(registry.tools)} tools")
