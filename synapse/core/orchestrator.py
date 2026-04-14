"""
Orchestrator - DAG execution engine
Executes tasks in the correct order based on dependencies
"""
import re
from typing import List, Callable, Optional, Any
from datetime import datetime
from core.context import Context, TaskNode
from core.a2a_bus import get_bus, A2AMessage
from mcp.server import get_mcp_server


class Orchestrator:
    """
    Executes task DAG with dependency resolution
    """
    
    def __init__(self):
        self.mcp = get_mcp_server()
        self.bus = get_bus()
        self.on_task_update: Optional[Callable] = None  # Callback for UI updates
        
        # Register orchestrator with A2A bus
        self.bus.register_agent("orchestrator")
    
    def execute(self, context: Context) -> bool:
        """
        Execute all tasks in the context's task graph
        
        Returns:
            True if all tasks completed successfully
        """
        context.log_event("STARTED", "orchestrator", "Beginning execution")
        
        while True:
            # Get tasks that are ready to run
            ready_tasks = self._get_ready_tasks(context)
            
            if not ready_tasks:
                # Check if we're done or stuck
                pending = [t for t in context.task_graph if t.status == "pending"]
                if not pending:
                    break  # All done!
                else:
                    # Stuck - dependencies can't be resolved
                    context.log_event("ERROR", "orchestrator", "Deadlock detected")
                    return False
            
            # Execute ready tasks (could be parallelized)
            for task in ready_tasks:
                self._execute_task(context, task)
        
        # Check final status
        failed = [t for t in context.task_graph if t.status == "failed"]
        success = len(failed) == 0
        
        status = "SUCCESS" if success else "PARTIAL_FAILURE"
        context.log_event("COMPLETED", "orchestrator", f"{status}: {len(context.task_graph) - len(failed)}/{len(context.task_graph)} tasks")
        
        return success
    
    def _get_ready_tasks(self, context: Context) -> List[TaskNode]:
        """Get tasks whose dependencies are all satisfied"""
        ready = []
        
        for task in context.task_graph:
            if task.status != "pending":
                continue
            
            # Check if all dependencies are complete
            deps_satisfied = True
            for dep_id in task.deps:
                dep_task = context.get_task(dep_id)
                if not dep_task or dep_task.status != "success":
                    deps_satisfied = False
                    break
            
            if deps_satisfied:
                ready.append(task)
        
        return ready
    
    def _execute_task(self, context: Context, task: TaskNode):
        """Execute a single task"""
        task.status = "running"
        context.log_event("RUNNING", task.id, f"Executing {task.tool}")
        
        # Notify via callback if set
        if self.on_task_update:
            self.on_task_update(task, "running")
        
        # Send A2A message for tracking
        self.bus.send(A2AMessage(
            id=f"exec_{task.id}_{datetime.now().timestamp()}",
            sender="orchestrator",
            recipient="mcp_server",
            msg_type="task_request",
            payload={"task_id": task.id, "tool": task.tool, "args": task.args}
        ))
        
        # Resolve argument references (e.g., {T1.result})
        resolved_args = self._resolve_args(context, task.args)
        
        # Execute via MCP
        result = self.mcp.call_tool(task.tool, resolved_args)
        
        if result["success"]:
            context.update_task_status(task.id, "success", result["result"])
        else:
            context.update_task_status(task.id, "failed", error=result["error"])
        
        # Notify via callback
        if self.on_task_update:
            self.on_task_update(task, task.status)
        
        # Send completion message
        self.bus.send(A2AMessage(
            id=f"done_{task.id}_{datetime.now().timestamp()}",
            sender="mcp_server",
            recipient="orchestrator",
            msg_type="task_result",
            payload={"task_id": task.id, "status": task.status, "result": str(result)[:200]}
        ))
    
    def _resolve_args(self, context: Context, args: dict) -> dict:
        """Resolve references to previous task results in arguments"""
        resolved = {}
        
        for key, value in args.items():
            if isinstance(value, str):
                # Look for patterns like {T1.result} or {T1}
                def replace_ref(match):
                    ref = match.group(1)
                    task_id = ref.split('.')[0]
                    result = context.results.get(task_id)
                    if result is not None:
                        # Handle different result types
                        if isinstance(result, dict):
                            if 'results' in result:
                                # Web search results - extract text
                                return self._format_search_results(result)
                            elif 'content' in result:
                                return result['content']
                            else:
                                return str(result)
                        return str(result)
                    return match.group(0)
                
                resolved[key] = re.sub(r'\{(\w+(?:\.\w+)?)\}', replace_ref, value)
            else:
                resolved[key] = value
        
        return resolved
    
    def _format_search_results(self, search_result: dict) -> str:
        """Format search results for use in prompts"""
        if not search_result.get('results'):
            return "No search results found."
        
        formatted = []
        for r in search_result['results'][:5]:
            formatted.append(f"- {r.get('title', '')}: {r.get('snippet', '')}")
        
        return "\n".join(formatted)
