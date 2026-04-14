"""
Planner Agent - LLM-powered task decomposition
Converts user intent into executable DAG
"""
import json
import re
from typing import List, Dict, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GROQ_API_KEY, GEMINI_API_KEY, GROQ_MODEL, GEMINI_MODEL, LLM_PROVIDER
from core.context import Context, TaskNode
from mcp.registry import get_registry


class PlannerAgent:
    """
    LLM-powered planner that decomposes user requests into task DAGs
    Supports both Groq and Gemini APIs
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.provider = LLM_PROVIDER
        
        # Initialize the appropriate client
        if GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(GEMINI_MODEL)
            self.provider = "gemini"
        elif GROQ_API_KEY:
            from groq import Groq
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            self.provider = "groq"
        else:
            self.gemini_model = None
            self.groq_client = None
    
    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider"""
        if self.provider == "gemini" and hasattr(self, 'gemini_model'):
            response = self.gemini_model.generate_content(prompt)
            return response.text
        elif self.provider == "groq" and hasattr(self, 'groq_client'):
            response = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            return response.choices[0].message.content
        else:
            raise ValueError("No LLM API key configured. Set GEMINI_API_KEY or GROQ_API_KEY")
    
    def plan(self, context: Context) -> List[TaskNode]:
        """
        Generate a task DAG from user input
        
        Args:
            context: Context with raw_input
            
        Returns:
            List of TaskNode objects representing the execution plan
        """
        # Get available tools for the prompt
        tools_desc = self.registry.get_tools_prompt()
        
        # Create the planning prompt
        prompt = f"""You are a task planning agent. Decompose the user's request into a sequence of tool calls.

{tools_desc}

USER REQUEST: {context.raw_input}

Create a JSON task graph. Each task has:
- id: unique identifier (T1, T2, etc.)
- tool: one of the available tools
- args: arguments for the tool
- deps: list of task IDs this depends on (empty if none)

Rules:
1. Break down complex requests into simple tool calls
2. Use web_search to gather information first
3. Use generate_report or generate_text to create content
4. Use summarize_text if user wants summaries
5. Use write_file to save output. Always save files to the "outputs/" folder (e.g. "outputs/report.txt", "outputs/data.csv")
6. Tasks can run in parallel if they don't depend on each other
7. Pass results between tasks using {{T1.result}} syntax in args
8. Only use tool names that appear in the available tools list above. Do not invent tool names.

Respond with ONLY valid JSON in this format:
{{
  "tasks": [
    {{"id": "T1", "tool": "tool_name", "args": {{}}, "deps": []}}
  ]
}}

Think step by step about what tools are needed and their dependencies."""

        try:
            result = self._call_llm(prompt)
            
            # Parse the JSON from the response
            task_graph = self._parse_task_graph(result)
            
            # Convert to TaskNode objects
            task_nodes = []
            for task in task_graph.get("tasks", []):
                node = TaskNode(
                    id=task["id"],
                    tool=task["tool"],
                    args=task.get("args", {}),
                    deps=task.get("deps", [])
                )
                task_nodes.append(node)
            
            context.log_event("PLANNED", "planner", f"Generated {len(task_nodes)} tasks via {self.provider}")
            return task_nodes
            
        except Exception as e:
            context.log_event("ERROR", "planner", str(e))
            raise
    
    def _parse_task_graph(self, response: str) -> Dict:
        """Extract JSON from LLM response"""
        # Try to find JSON in the response
        try:
            # First try: direct JSON parse
            return json.loads(response)
        except:
            pass
        
        # Second try: find JSON block
        json_match = re.search(r'\{[\s\S]*"tasks"[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Fallback: create a simple task
        return {
            "tasks": [{
                "id": "T1",
                "tool": "generate_text",
                "args": {"prompt": response},
                "deps": []
            }]
        }
    
    def replan(self, context: Context, failed_task: TaskNode) -> List[TaskNode]:
        """
        Re-plan when a task fails
        """
        prompt = f"""A task failed during execution. Create an alternative plan.

Original request: {context.raw_input}
Failed task: {failed_task.tool} with args {failed_task.args}
Error: {failed_task.error}

Create an alternative approach that avoids this failure.
Respond with ONLY valid JSON."""
        
        # Similar to plan() but with failure context
        # Simplified for PoC - just returns remaining tasks
        remaining = [t for t in context.task_graph if t.status == "pending"]
        return remaining
