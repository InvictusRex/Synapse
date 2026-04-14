"""
DAG Visualization utility
Generates a visual representation of the task graph
"""
from typing import List
from core.context import TaskNode


def generate_dag_mermaid(tasks: List[TaskNode]) -> str:
    """Generate Mermaid diagram syntax for the task graph"""
    lines = ["graph TD"]
    
    for task in tasks:
        # Node with tool name
        node_label = f"{task.id}[{task.id}: {task.tool}]"
        lines.append(f"    {node_label}")
        
        # Dependencies as edges
        for dep in task.deps:
            lines.append(f"    {dep} --> {task.id}")
    
    # Add styling based on status
    for task in tasks:
        if task.status == "success":
            lines.append(f"    style {task.id} fill:#90EE90")
        elif task.status == "failed":
            lines.append(f"    style {task.id} fill:#FFB6C1")
        elif task.status == "running":
            lines.append(f"    style {task.id} fill:#FFE4B5")
    
    return "\n".join(lines)


def generate_dag_ascii(tasks: List[TaskNode]) -> str:
    """Generate simple ASCII visualization"""
    lines = []
    lines.append("┌─────────────────────────────────────────┐")
    lines.append("│           TASK EXECUTION GRAPH          │")
    lines.append("└─────────────────────────────────────────┘")
    lines.append("")
    
    # Build dependency levels
    levels = {}
    remaining = list(tasks)
    level = 0
    
    while remaining:
        current_level = []
        for task in remaining[:]:
            deps_satisfied = all(
                any(t.id == dep and t.id in [x.id for lvl in levels.values() for x in lvl] 
                    for t in tasks)
                for dep in task.deps
            ) if task.deps else True
            
            if not task.deps or deps_satisfied:
                current_level.append(task)
                remaining.remove(task)
        
        if current_level:
            levels[level] = current_level
            level += 1
        else:
            # Avoid infinite loop
            levels[level] = remaining
            break
    
    # Render levels
    for lvl, tasks_at_level in levels.items():
        lines.append(f"Level {lvl}:")
        for task in tasks_at_level:
            status_icon = {
                "pending": "⏳",
                "running": "🔄",
                "success": "✅",
                "failed": "❌"
            }.get(task.status, "❓")
            
            deps_str = f" ← [{', '.join(task.deps)}]" if task.deps else ""
            lines.append(f"  {status_icon} {task.id}: {task.tool}{deps_str}")
        lines.append("       │")
        lines.append("       ▼")
    
    lines.pop()  # Remove last arrow
    lines.pop()
    lines.append("")
    lines.append("─" * 45)
    
    return "\n".join(lines)


def print_execution_flow(tasks: List[TaskNode]):
    """Print a nice execution flow diagram"""
    print(generate_dag_ascii(tasks))
