"""
Planner Agent - LLM-powered task decomposition
Converts user intent into executable DAG
"""
import json
import re
from typing import List, Dict, Any
from groq import Groq
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GROQ_API_KEY, LLM_MODEL
from core.context import Context, TaskNode
from mcp.registry import get_registry


class PlannerAgent:
    """
    LLM-powered planner that decomposes user requests into task DAGs
    """
    
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self.registry = get_registry()
    
    def plan(self, context: Context) -> List[TaskNode]:
        """
        Generate a task DAG from user input
        
        Args:
            context: Context with raw_input
            
        Returns:
            List of TaskNode objects representing the execution plan
        """
        if not self.client:
            raise ValueError("GROQ_API_KEY not configured")
        
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
5. Use save_to_file if user wants to save output
6. Tasks can run in parallel if they don't depend on each other
7. Pass results between tasks using {{T1.result}} syntax in args

Respond with ONLY valid JSON in this format:
{{
  "tasks": [
    {{"id": "T1", "tool": "tool_name", "args": {{}}, "deps": []}}
  ]
}}

Think step by step about what tools are needed and their dependencies."""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            
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
            
            context.log_event("PLANNED", "planner", f"Generated {len(task_nodes)} tasks")
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
