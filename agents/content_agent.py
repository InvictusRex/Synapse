"""
Content Agent
Handles content generation, summarization, and text processing
"""
import json
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType
from mcp.server import ToolCategory


class ContentAgent(BaseAgent):
    """
    Content Agent
    
    Responsibilities:
    - Generate text content (articles, reports, code, etc.)
    - Summarize text
    - Transform/rewrite content
    - Answer questions
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Content Agent",
            description="I generate and process text content. I can write articles, reports, summaries, and answer questions.",
            capabilities=[
                "Generate articles and reports",
                "Summarize text content",
                "Answer questions",
                "Transform and rewrite content",
                "Create structured documents"
            ],
            tool_categories=[ToolCategory.CONTENT]
        )
        super().__init__(config)
    
    def generate_content(self, topic: str, content_type: str = "article", 
                        length: str = "medium") -> Dict[str, Any]:
        """
        Generate content about a topic
        """
        prompts = {
            "article": f"""Write a detailed, well-structured article about: {topic}

Include:
- An engaging introduction
- Multiple sections with clear headings (use ## for headings)
- Detailed explanations and examples
- A conclusion

Write at least 500 words. Make it informative and engaging.""",

            "report": f"""Write a professional report about: {topic}

Structure:
## Executive Summary
## Introduction
## Analysis/Findings
## Conclusions
## Recommendations

Be thorough and professional. Include specific details and insights.""",

            "research": f"""Write a research paper about: {topic}

Structure:
## Abstract
## Introduction  
## Background
## Methodology
## Results/Discussion
## Conclusion
## References

Use academic tone. Be thorough and cite plausible sources.""",

            "summary": f"""Provide a comprehensive summary of: {topic}

Cover the key points, main ideas, and important details.
Be concise but thorough."""
        }
        
        prompt = prompts.get(content_type, prompts["article"])
        result = self.use_tool("generate_text", {"prompt": prompt, "max_length": length})
        
        if result.get("success"):
            return {
                "success": True,
                "content": result.get("content"),
                "topic": topic,
                "type": content_type,
                "length": len(result.get("content", ""))
            }
        return result
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a content task"""
        tool = task.get("tool")
        args = task.get("args", {})
        
        if tool == "generate_text":
            # Check if we have a structured content request
            if "topic" in args and "content_type" in args:
                return self.generate_content(
                    args["topic"],
                    args.get("content_type", "article"),
                    args.get("length", "medium")
                )
            # Direct generation
            return self.use_tool(tool, args)
        
        elif tool == "summarize_text":
            return self.use_tool(tool, args)
        
        # Autonomous decision
        decision = self.decide_action(task)
        
        if decision.get("action") == "use_tool":
            return self.use_tool(
                decision.get("tool_name"),
                decision.get("tool_args", {})
            )
        
        # Direct response
        if decision.get("response"):
            return {
                "success": True,
                "content": decision.get("response"),
                "reasoning": decision.get("reasoning")
            }
        
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
