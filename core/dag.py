"""
DAG (Directed Acyclic Graph) Data Structure
For representing task execution plans with dependencies
"""
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid


class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGTask:
    """A single task in the DAG"""
    task_id: str
    agent: str
    tool: str
    args: Dict[str, Any]
    description: str = ""
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent": self.agent,
            "tool": self.tool,
            "args": self.args,
            "description": self.description,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DAGTask':
        return cls(
            task_id=data.get("task_id", str(uuid.uuid4())[:8]),
            agent=data.get("agent", ""),
            tool=data.get("tool", ""),
            args=data.get("args", {}),
            description=data.get("description", ""),
            depends_on=data.get("depends_on", []),
            status=TaskStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error")
        )


class DAG:
    """
    Directed Acyclic Graph for task execution
    
    Features:
    - Task dependency management
    - Parallel execution detection
    - Cycle detection
    - Topological ordering
    """
    
    def __init__(self, plan_id: str = None, description: str = ""):
        self.plan_id = plan_id or str(uuid.uuid4())[:8]
        self.description = description
        self.tasks: Dict[str, DAGTask] = {}
        self._adjacency: Dict[str, Set[str]] = {}  # task -> tasks that depend on it
        self._reverse_adj: Dict[str, Set[str]] = {}  # task -> tasks it depends on
    
    def add_task(self, task: DAGTask):
        """Add a task to the DAG"""
        self.tasks[task.task_id] = task
        
        if task.task_id not in self._adjacency:
            self._adjacency[task.task_id] = set()
        if task.task_id not in self._reverse_adj:
            self._reverse_adj[task.task_id] = set()
        
        # Update dependency graph
        for dep_id in task.depends_on:
            if dep_id not in self._adjacency:
                self._adjacency[dep_id] = set()
            self._adjacency[dep_id].add(task.task_id)
            self._reverse_adj[task.task_id].add(dep_id)
    
    def remove_task(self, task_id: str):
        """Remove a task from the DAG"""
        if task_id in self.tasks:
            del self.tasks[task_id]
        
        # Clean up adjacency
        if task_id in self._adjacency:
            del self._adjacency[task_id]
        if task_id in self._reverse_adj:
            del self._reverse_adj[task_id]
        
        # Remove from other tasks' dependencies
        for adj in self._adjacency.values():
            adj.discard(task_id)
        for adj in self._reverse_adj.values():
            adj.discard(task_id)
    
    def get_ready_tasks(self) -> List[DAGTask]:
        """
        Get all tasks that are ready to execute
        A task is ready if:
        - Status is PENDING
        - All dependencies are COMPLETED
        """
        ready = []
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            
            # Check all dependencies
            deps_completed = True
            for dep_id in task.depends_on:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    deps_completed = False
                    break
            
            if deps_completed:
                ready.append(task)
        
        return ready
    
    def get_parallel_groups(self) -> List[List[DAGTask]]:
        """
        Get tasks grouped by execution level
        Tasks in the same group can run in parallel
        """
        # Calculate levels using BFS
        levels: Dict[str, int] = {}
        
        # Find root tasks (no dependencies)
        roots = [tid for tid, task in self.tasks.items() if not task.depends_on]
        
        for root in roots:
            levels[root] = 0
        
        # BFS to assign levels
        queue = list(roots)
        while queue:
            current = queue.pop(0)
            current_level = levels.get(current, 0)
            
            for dependent in self._adjacency.get(current, []):
                new_level = current_level + 1
                if dependent not in levels or levels[dependent] < new_level:
                    levels[dependent] = new_level
                    queue.append(dependent)
        
        # Group tasks by level
        max_level = max(levels.values()) if levels else 0
        groups = [[] for _ in range(max_level + 1)]
        
        for task_id, level in levels.items():
            if task_id in self.tasks:
                groups[level].append(self.tasks[task_id])
        
        return groups
    
    def get_topological_order(self) -> List[str]:
        """Get tasks in topological order (respecting dependencies)"""
        in_degree = {tid: len(task.depends_on) for tid, task in self.tasks.items()}
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            for dependent in self._adjacency.get(current, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        return order
    
    def has_cycle(self) -> bool:
        """Check if the DAG has a cycle (invalid)"""
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        
        return False
    
    def validate(self) -> Dict[str, Any]:
        """Validate the DAG"""
        errors = []
        warnings = []
        
        # Check for cycles
        if self.has_cycle():
            errors.append("DAG contains a cycle")
        
        # Check for missing dependencies
        for task_id, task in self.tasks.items():
            for dep_id in task.depends_on:
                if dep_id not in self.tasks:
                    errors.append(f"Task {task_id} depends on non-existent task {dep_id}")
        
        # Check for empty DAG
        if not self.tasks:
            warnings.append("DAG has no tasks")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def mark_complete(self, task_id: str, result: Dict[str, Any] = None):
        """Mark a task as completed"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].result = result
    
    def mark_failed(self, task_id: str, error: str):
        """Mark a task as failed"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED
            self.tasks[task_id].error = error
    
    def mark_running(self, task_id: str):
        """Mark a task as running"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.RUNNING
    
    def is_complete(self) -> bool:
        """Check if all tasks are complete or failed"""
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.READY, TaskStatus.RUNNING]:
                return False
        return True
    
    def get_stats(self) -> Dict[str, int]:
        """Get task statistics"""
        stats = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0
        }
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                stats["pending"] += 1
            elif task.status == TaskStatus.RUNNING:
                stats["running"] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats["completed"] += 1
            elif task.status == TaskStatus.FAILED:
                stats["failed"] += 1
            elif task.status == TaskStatus.SKIPPED:
                stats["skipped"] += 1
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert DAG to dictionary"""
        return {
            "plan_id": self.plan_id,
            "description": self.description,
            "tasks": [task.to_dict() for task in self.tasks.values()],
            "stats": self.get_stats()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DAG':
        """Create DAG from dictionary"""
        dag = cls(
            plan_id=data.get("plan_id"),
            description=data.get("description", "")
        )
        for task_data in data.get("tasks", []):
            task = DAGTask.from_dict(task_data)
            dag.add_task(task)
        return dag
    
    @classmethod
    def from_plan(cls, plan: Dict[str, Any]) -> 'DAG':
        """Create DAG from a planner output"""
        dag = cls(
            plan_id=plan.get("plan_id", ""),
            description=plan.get("description", "")
        )
        for task_data in plan.get("tasks", []):
            task = DAGTask.from_dict(task_data)
            dag.add_task(task)
        return dag
