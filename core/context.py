"""
Context Manager - Central state management for the agent system
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


@dataclass
class TaskNode:
    """Represents a single task in the execution graph"""
    id: str
    tool: str
    args: Dict[str, Any]
    deps: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, success, failed
    result: Any = None
    error: Optional[str] = None


@dataclass 
class Context:
    """Central context object that flows through the system"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    raw_input: str = ""
    intent: Dict[str, Any] = field(default_factory=dict)
    task_graph: List[TaskNode] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    execution_log: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def log_event(self, event_type: str, task_id: str, details: str):
        """Log an execution event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "task_id": task_id,
            "details": details
        }
        self.execution_log.append(event)
        print(f"[{event['timestamp']}] {event_type}: {task_id} - {details}")
    
    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """Get a task by ID"""
        for task in self.task_graph:
            if task.id == task_id:
                return task
        return None
    
    def update_task_status(self, task_id: str, status: str, result: Any = None, error: str = None):
        """Update task status and result"""
        task = self.get_task(task_id)
        if task:
            task.status = status
            task.result = result
            task.error = error
            self.results[task_id] = result
            self.log_event(status.upper(), task_id, str(result)[:100] if result else error or "")


class ContextManager:
    """Manages context lifecycle"""
    
    def __init__(self):
        self.contexts: Dict[str, Context] = {}
    
    def create_context(self, raw_input: str) -> Context:
        """Create a new context for a user request"""
        ctx = Context(raw_input=raw_input)
        self.contexts[ctx.session_id] = ctx
        ctx.log_event("CREATED", "system", f"New session: {ctx.session_id}")
        return ctx
    
    def get_context(self, session_id: str) -> Optional[Context]:
        """Retrieve an existing context"""
        return self.contexts.get(session_id)
