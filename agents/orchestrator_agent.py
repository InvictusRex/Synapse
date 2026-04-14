"""
Orchestrator Agent
The central coordinator that manages task execution across all agents
"""
import json
import re
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType, get_bus
from mcp.server import ToolCategory


@dataclass
class TaskState:
    """Track state of a task"""
    task_id: str
    agent: str
    status: str  # pending, running, completed, failed
    result: Optional[Dict] = None
    error: Optional[str] = None


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent
    
    Responsibilities:
    - Receive execution plans
    - Dispatch tasks to appropriate agents
    - Track task completion and dependencies
    - Resolve data passing between tasks
    - Aggregate final results
    """
    
    def __init__(self):
        config = AgentConfig(
            name="Orchestrator Agent",
            description="I coordinate task execution. I dispatch tasks to agents, manage dependencies, and aggregate results.",
            capabilities=[
                "Execute plans across multiple agents",
                "Manage task dependencies",
                "Track execution progress",
                "Handle errors and retries",
                "Aggregate final results"
            ],
            tool_categories=[]  # Works through other agents
        )
        super().__init__(config)
        
        # Agent registry - stores actual agent instances
        self.worker_agents: Dict[str, 'BaseAgent'] = {}  # agent_type -> agent instance
        self.task_states: Dict[str, TaskState] = {}
        self.task_results: Dict[str, Dict] = {}
        self.execution_log: List[Dict] = []
    
    def register_worker_agent(self, agent_type: str, agent_instance):
        """Register a worker agent instance"""
        self.worker_agents[agent_type] = agent_instance
        print(f"[orchestrator] Registered {agent_type} -> {agent_instance.agent_id}")
    
    def execute_plan(self, plan: Dict) -> Dict[str, Any]:
        """
        Execute a plan by dispatching tasks to agents
        Handles dependencies and result passing
        """
        tasks = plan.get("tasks", [])
        
        if not tasks:
            return {"success": False, "error": "No tasks in plan"}
        
        self.log(f"Starting execution of plan with {len(tasks)} tasks")
        
        # Initialize task states
        self.task_states = {}
        self.task_results = {}
        
        for task in tasks:
            task_id = task.get("task_id")
            self.task_states[task_id] = TaskState(
                task_id=task_id,
                agent=task.get("agent"),
                status="pending"
            )
        
        # Execute tasks in dependency order
        completed = set()
        max_iterations = len(tasks) * 2  # Prevent infinite loops
        iterations = 0
        
        while len(completed) < len(tasks) and iterations < max_iterations:
            iterations += 1
            progress_made = False
            
            for task in tasks:
                task_id = task.get("task_id")
                
                # Skip if already completed or running
                if task_id in completed:
                    continue
                
                state = self.task_states[task_id]
                if state.status in ["running", "completed"]:
                    if state.status == "completed":
                        completed.add(task_id)
                    continue
                
                # Check dependencies
                deps = task.get("depends_on", [])
                deps_met = all(d in completed for d in deps)
                
                if deps_met:
                    # Execute this task
                    self.log(f"Executing task {task_id}")
                    state.status = "running"
                    
                    # Resolve argument references
                    resolved_args = self._resolve_args(task.get("args", {}))
                    
                    # Dispatch to agent
                    result = self._dispatch_task(task, resolved_args)
                    
                    if result.get("success"):
                        state.status = "completed"
                        state.result = result
                        self.task_results[task_id] = result
                        completed.add(task_id)
                        self.log(f"Task {task_id} completed successfully")
                    else:
                        state.status = "failed"
                        # Get the actual error message
                        error_msg = result.get("error")
                        if not error_msg and "result" in result:
                            inner_result = result.get("result", {})
                            if isinstance(inner_result, dict):
                                error_msg = inner_result.get("error")
                        state.error = error_msg or "Unknown error"
                        completed.add(task_id)  # Mark as done (failed) so we don't retry
                        self.log(f"Task {task_id} failed: {state.error}")
                        # Continue with other tasks - don't halt on failure
                    
                    progress_made = True
            
            if not progress_made and len(completed) < len(tasks):
                # Check for stuck tasks (circular dependencies or all remaining failed)
                pending = [t for t in tasks if t.get("task_id") not in completed]
                if all(self.task_states[t.get("task_id")].status == "failed" for t in pending):
                    break
                time.sleep(0.1)  # Small delay before retry
        
        # Aggregate results
        final_result = self._aggregate_results(tasks)
        
        # Determine overall success - success if at least one task completed
        # and the last task in the chain completed
        success_count = sum(1 for s in self.task_states.values() if s.status == "completed")
        failed_count = sum(1 for s in self.task_states.values() if s.status == "failed")
        
        # Get the last task (usually the final output)
        last_task_id = tasks[-1].get("task_id") if tasks else None
        last_task_succeeded = last_task_id and self.task_states.get(last_task_id, TaskState("", "", "")).status == "completed"
        
        # Overall success if: last task succeeded OR majority succeeded
        overall_success = last_task_succeeded or (success_count > failed_count)
        
        return {
            "success": overall_success,
            "tasks_completed": success_count,
            "tasks_failed": failed_count,
            "tasks_total": len(tasks),
            "task_states": {tid: {"status": s.status, "error": s.error} 
                          for tid, s in self.task_states.items()},
            "final_result": final_result,
            "execution_log": self.execution_log[-20:]  # Last 20 entries
        }
    
    def _resolve_args(self, args: Dict) -> Dict:
        """Resolve references to previous task results"""
        resolved = {}
        
        for key, value in args.items():
            if isinstance(value, str):
                # Look for {TASK_ID.result} or {TASK_ID.field} patterns
                def replace_ref(match):
                    ref = match.group(1)
                    parts = ref.split(".")
                    task_id = parts[0]
                    
                    if task_id in self.task_results:
                        result = self.task_results[task_id]
                        
                        # Navigate to field if specified
                        if len(parts) > 1:
                            field = parts[1]
                            if isinstance(result, dict):
                                # Try to get the field
                                if field in result:
                                    return str(result[field])
                                # Try nested result
                                if "result" in result and isinstance(result["result"], dict):
                                    if field in result["result"]:
                                        return str(result["result"][field])
                                # Try content field commonly used
                                if field == "content" or field == "result":
                                    for key in ["content", "result", "data", "output"]:
                                        if key in result:
                                            return str(result[key])
                                        if "result" in result and key in result.get("result", {}):
                                            return str(result["result"][key])
                        
                        # Return best content from result
                        if isinstance(result, dict):
                            for key in ["content", "result", "data", "output"]:
                                if key in result:
                                    return str(result[key])
                                if "result" in result and isinstance(result["result"], dict):
                                    if key in result["result"]:
                                        return str(result["result"][key])
                        
                        return str(result)
                    
                    return match.group(0)  # Keep original if not found
                
                resolved[key] = re.sub(r'\{([^}]+)\}', replace_ref, value)
            else:
                resolved[key] = value
        
        return resolved
    
    def _dispatch_task(self, task: Dict, resolved_args: Dict) -> Dict[str, Any]:
        """Dispatch a task to the appropriate agent"""
        agent_type = task.get("agent")
        tool = task.get("tool")
        
        # Get the actual agent instance
        agent = self.worker_agents.get(agent_type)
        
        if not agent:
            return {"success": False, "error": f"Unknown agent type: {agent_type}"}
        
        # Log the message to A2A bus (for visibility)
        correlation_id = f"task_{task.get('task_id')}_{int(time.time())}"
        
        self.send_message(
            agent.agent_id,
            MessageType.TASK_REQUEST,
            {"tool": tool, "args": resolved_args, "task_id": task.get("task_id")},
            correlation_id
        )
        
        # Directly invoke the agent's handle_task method
        # This is synchronous but still uses the A2A bus for logging
        try:
            result = agent.handle_task({"tool": tool, "args": resolved_args})
            
            # Log the response to A2A bus
            agent.send_message(
                self.agent_id,
                MessageType.TASK_RESULT,
                result,
                correlation_id
            )
            
            return result
            
        except Exception as e:
            error_result = {"success": False, "error": f"Agent error: {str(e)}"}
            
            agent.send_message(
                self.agent_id,
                MessageType.ERROR,
                error_result,
                correlation_id
            )
            
            return error_result
    
    def _aggregate_results(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Aggregate all task results into final result"""
        last_result = None
        all_content = []
        
        for task in tasks:
            task_id = task.get("task_id")
            if task_id in self.task_results:
                result = self.task_results[task_id]
                last_result = result
                
                # Get the tool type
                tool_type = task.get("tool", "unknown")
                
                # Extract meaningful content based on result structure
                content = None
                
                if isinstance(result, dict):
                    # For list_directory, preserve the full structure
                    if tool_type == "list_directory":
                        content = {
                            "items": result.get("items", []),
                            "directory": result.get("directory", ""),
                            "count": result.get("count", 0)
                        }
                    # For system info
                    elif tool_type == "get_system_info":
                        content = {k: v for k, v in result.items() if k != "success"}
                    # For datetime
                    elif tool_type == "get_datetime":
                        content = {k: v for k, v in result.items() if k != "success"}
                    # For calculations
                    elif tool_type == "calculate":
                        content = {
                            "expression": result.get("expression", ""),
                            "result": result.get("result", "")
                        }
                    # For file operations
                    elif tool_type in ["write_file", "create_file", "move_file", "copy_file", "delete_file", "create_folder"]:
                        content = {k: v for k, v in result.items() if k not in ["success", "tool"]}
                    # For read_file
                    elif tool_type == "read_file":
                        content = result.get("content", "")
                    # For fetch_webpage
                    elif tool_type == "fetch_webpage":
                        content = {
                            "title": result.get("title", ""),
                            "content": result.get("content", "")[:3000],
                            "url": result.get("url", "")
                        }
                    # For generate_text
                    elif tool_type == "generate_text":
                        content = result.get("content", "")
                    # Default: try common keys
                    else:
                        for key in ["content", "result", "data", "output"]:
                            if key in result:
                                content = result[key]
                                break
                        if content is None:
                            content = {k: v for k, v in result.items() if k not in ["success", "tool"]}
                
                if content is not None:
                    all_content.append({
                        "task": task_id,
                        "type": tool_type,
                        "content": content
                    })
        
        return {
            "last_task_result": last_result,
            "all_outputs": all_content,
            "task_count": len(tasks),
            "success_count": sum(1 for s in self.task_states.values() if s.status == "completed")
        }
    
    def log(self, message: str):
        """Log execution event"""
        entry = {"time": time.time(), "message": message}
        self.execution_log.append(entry)
        print(f"[orchestrator] {message}")
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a task (execute a plan)"""
        if "plan" in task:
            return self.execute_plan(task["plan"])
        return {"success": False, "error": "No plan provided"}
    
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
        
        return None
