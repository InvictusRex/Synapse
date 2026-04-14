"""
Web Agent
Handles web operations - fetching, downloading, scraping
"""
import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class WebAgent(BaseAgent):
    """
    Web Agent
    
    Responsibilities:
    - Fetch web pages
    - Download files from URLs
    - Extract content from websites
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Web Agent",
            description="I handle web operations. I can fetch web pages, download files, and extract content from URLs.",
            capabilities=[
                "Fetch and extract text from web pages",
                "Download files from URLs",
                "Parse web content"
            ],
            tool_categories=[ToolCategory.WEB]
        )
        super().__init__(config)
    
    def fetch_and_summarize(self, url: str) -> Dict[str, Any]:
        """Fetch a webpage and provide a summary"""
        # First fetch the page
        fetch_result = self.use_tool("fetch_webpage", {"url": url})
        
        if not fetch_result.get("success"):
            return fetch_result
        
        content = fetch_result.get("content", "")
        title = fetch_result.get("title", "")
        
        # Create a summary using our thinking capability
        summary_prompt = f"""Summarize this webpage content:

Title: {title}
Content: {content[:3000]}

Provide a clear, concise summary of the main points."""

        summary = self.think(summary_prompt)
        
        return {
            "success": True,
            "url": url,
            "title": title,
            "content": content,
            "summary": summary
        }
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a web task"""
        tool = task.get("tool")
        args = task.get("args", {})
        
        if tool:
            result = self.use_tool(tool, args)
            return {
                "success": result.get("success", False),
                "tool": tool,
                "result": result
            }
        
        # Autonomous decision
        decision = self.decide_action(task)
        
        if decision.get("action") == "use_tool":
            return self.use_tool(
                decision.get("tool_name"),
                decision.get("tool_args", {})
            )
        
        return {"success": False, "error": "Could not handle task", "decision": decision}
    
    def handle_message(self, message: Message) -> Optional[Dict]:
        """Handle incoming messages"""
        if message.msg_type == MessageType.TASK_REQUEST:
            result = self.handle_task(message.payload)
            
            self.send_message(
                message.sender,
                MessageType.TASK_RESULT,
                result,
                message.id
            )
            return result
        
        elif message.msg_type == MessageType.TOOL_REQUEST:
            tool = message.payload.get("tool")
            args = message.payload.get("args", {})
            result = self.use_tool(tool, args)
            
            self.send_message(
                message.sender,
                MessageType.TOOL_RESULT,
                result,
                message.id
            )
            return result
        
        return None
