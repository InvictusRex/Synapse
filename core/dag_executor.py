"""
Parallel DAG Executor
Executes tasks in parallel while respecting dependencies
"""
import threading
import time
import re
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from queue import Queue, Empty

from core.dag import DAG, DAGTask, TaskStatus


class DAGExecutor:
    """
    Parallel DAG Executor
    
    Features:
    - Parallel execution of independent tasks
    - Dependency resolution
    - Result propagation between tasks
    - Error handling with optional skip-on-failure
    - Real-time progress tracking
    """
    
    def __init__(self, max_workers: int = 4, task_timeout: int = 60):
        self.max_workers = max_workers
        self.task_timeout = task_timeout
        self._executor: Optional[ThreadPoolExecutor] = None
        self._task_handler: Optional[Callable] = None
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._progress_callback: Optional[Callable] = None
    
    def set_task_handler(self, handler: Callable[[DAGTask, Dict[str, Any]], Dict[str, Any]]):
        """
        Set the task execution handler
        
        Handler signature: (task: DAGTask, context: Dict) -> Dict[str, Any]
        Context contains results from dependent tasks
        """
        self._task_handler = handler
    
    def set_progress_callback(self, callback: Callable[[DAGTask, str], None]):
        """Set callback for progress updates: callback(task, status)"""
        self._progress_callback = callback
    
    def _notify_progress(self, task: DAGTask, status: str):
        """Notify progress callback"""
        if self._progress_callback:
            try:
                self._progress_callback(task, status)
            except:
                pass
    
    def _resolve_task_args(self, task: DAGTask, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve task arguments by substituting references to previous task results
        
        Patterns supported:
        - {T1.content} -> results["T1"]["content"]
        - {T1.result} -> results["T1"]
        - {T1} -> results["T1"]
        """
        resolved_args = {}
        
        for key, value in task.args.items():
            if isinstance(value, str):
                # Find all references like {T1.content} or {T1}
                pattern = r'\{(\w+)(?:\.(\w+))?\}'
                
                def replace_ref(match):
                    task_id = match.group(1)
                    field = match.group(2)
                    
                    if task_id in results:
                        task_result = results[task_id]
                        if field:
                            if isinstance(task_result, dict):
                                return str(task_result.get(field, ""))
                            return str(task_result)
                        else:
                            if isinstance(task_result, dict):
                                # Return content or result field if available
                                return str(task_result.get("content", 
                                          task_result.get("result", task_result)))
                            return str(task_result)
                    return match.group(0)  # Keep original if not found
                
                resolved_value = re.sub(pattern, replace_ref, value)
                resolved_args[key] = resolved_value
            else:
                resolved_args[key] = value
        
        return resolved_args
    
    def _execute_task(self, task: DAGTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task"""
        if not self._task_handler:
            raise RuntimeError("No task handler set")
        
        # Resolve arguments with results from dependencies
        resolved_args = self._resolve_task_args(task, context)
        task_copy = DAGTask(
            task_id=task.task_id,
            agent=task.agent,
            tool=task.tool,
            args=resolved_args,
            description=task.description,
            depends_on=task.depends_on
        )
        
        return self._task_handler(task_copy, context)
    
    def execute(self, dag: DAG, skip_on_failure: bool = False) -> Dict[str, Any]:
        """
        Execute the DAG with parallel task execution
        
        Args:
            dag: The DAG to execute
            skip_on_failure: If True, skip dependent tasks on failure instead of stopping
        
        Returns:
            Dict with execution results and statistics
        """
        if not self._task_handler:
            raise RuntimeError("No task handler set. Call set_task_handler first.")
        
        # Validate DAG
        validation = dag.validate()
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"Invalid DAG: {validation['errors']}",
                "tasks_completed": 0,
                "tasks_failed": 0
            }
        
        self._results = {}
        failed_tasks = set()
        
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        try:
            while not dag.is_complete():
                # Get tasks ready to execute
                ready_tasks = dag.get_ready_tasks()
                
                if not ready_tasks:
                    # Check if we're stuck (tasks pending but none ready)
                    stats = dag.get_stats()
                    if stats["pending"] > 0 and stats["running"] == 0:
                        # Deadlock or all remaining tasks have failed dependencies
                        break
                    time.sleep(0.1)
                    continue
                
                # Filter out tasks with failed dependencies if not skipping
                if not skip_on_failure:
                    ready_tasks = [t for t in ready_tasks 
                                  if not any(d in failed_tasks for d in t.depends_on)]
                
                # Submit tasks for parallel execution
                futures: Dict[Future, DAGTask] = {}
                
                for task in ready_tasks:
                    # Check if any dependency failed
                    has_failed_dep = any(d in failed_tasks for d in task.depends_on)
                    
                    if has_failed_dep and skip_on_failure:
                        dag.tasks[task.task_id].status = TaskStatus.SKIPPED
                        self._notify_progress(task, "skipped")
                        continue
                    elif has_failed_dep:
                        continue
                    
                    dag.mark_running(task.task_id)
                    self._notify_progress(task, "running")
                    
                    # Build context with dependency results
                    context = {tid: self._results.get(tid) for tid in task.depends_on}
                    
                    future = self._executor.submit(self._execute_task, task, context)
                    futures[future] = task
                
                # Wait for submitted tasks to complete
                for future in as_completed(futures, timeout=self.task_timeout):
                    task = futures[future]
                    
                    try:
                        result = future.result(timeout=self.task_timeout)
                        
                        with self._lock:
                            self._results[task.task_id] = result
                        
                        if result.get("success", True):
                            dag.mark_complete(task.task_id, result)
                            self._notify_progress(task, "completed")
                        else:
                            error = result.get("error", "Unknown error")
                            dag.mark_failed(task.task_id, error)
                            failed_tasks.add(task.task_id)
                            self._notify_progress(task, "failed")
                            
                            if not skip_on_failure:
                                # Mark dependent tasks as skipped
                                self._skip_dependents(dag, task.task_id, failed_tasks)
                    
                    except Exception as e:
                        dag.mark_failed(task.task_id, str(e))
                        failed_tasks.add(task.task_id)
                        self._notify_progress(task, "failed")
                        
                        if not skip_on_failure:
                            self._skip_dependents(dag, task.task_id, failed_tasks)
        
        finally:
            self._executor.shutdown(wait=False)
            self._executor = None
        
        # Compile final results
        stats = dag.get_stats()
        all_outputs = []
        
        for task_id, task in dag.tasks.items():
            if task.status == TaskStatus.COMPLETED and task_id in self._results:
                result = self._results[task_id]
                if result:
                    all_outputs.append({
                        "task_id": task_id,
                        "type": task.tool,
                        "content": result.get("content", result.get("result", result))
                    })
        
        return {
            "success": stats["failed"] == 0,
            "tasks_completed": stats["completed"],
            "tasks_failed": stats["failed"],
            "tasks_skipped": stats["skipped"],
            "tasks_total": stats["total"],
            "task_states": {tid: task.to_dict() for tid, task in dag.tasks.items()},
            "results": self._results,
            "all_outputs": all_outputs,
            "final_result": self._results.get(list(dag.tasks.keys())[-1]) if dag.tasks else None
        }
    
    def _skip_dependents(self, dag: DAG, failed_id: str, failed_set: set):
        """Skip all tasks that depend on a failed task"""
        for task_id, task in dag.tasks.items():
            if failed_id in task.depends_on and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.SKIPPED
                failed_set.add(task_id)
                self._notify_progress(task, "skipped")
                # Recursively skip dependents
                self._skip_dependents(dag, task_id, failed_set)
    
    def execute_sync(self, dag: DAG) -> Dict[str, Any]:
        """Execute DAG synchronously (for simpler cases)"""
        if not self._task_handler:
            raise RuntimeError("No task handler set")
        
        self._results = {}
        
        # Get topological order
        order = dag.get_topological_order()
        
        for task_id in order:
            task = dag.tasks.get(task_id)
            if not task:
                continue
            
            # Check dependencies
            has_failed = False
            for dep_id in task.depends_on:
                dep_task = dag.tasks.get(dep_id)
                if dep_task and dep_task.status == TaskStatus.FAILED:
                    has_failed = True
                    break
            
            if has_failed:
                dag.mark_failed(task_id, "Dependency failed")
                continue
            
            dag.mark_running(task_id)
            
            try:
                context = {tid: self._results.get(tid) for tid in task.depends_on}
                result = self._execute_task(task, context)
                
                self._results[task_id] = result
                
                if result.get("success", True):
                    dag.mark_complete(task_id, result)
                else:
                    dag.mark_failed(task_id, result.get("error", "Unknown"))
            
            except Exception as e:
                dag.mark_failed(task_id, str(e))
        
        stats = dag.get_stats()
        return {
            "success": stats["failed"] == 0,
            "tasks_completed": stats["completed"],
            "tasks_failed": stats["failed"],
            "tasks_total": stats["total"],
            "results": self._results
        }


def create_executor(max_workers: int = 4, task_timeout: int = 60) -> DAGExecutor:
    """Factory function to create a DAG executor"""
    return DAGExecutor(max_workers=max_workers, task_timeout=task_timeout)
