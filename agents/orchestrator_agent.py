"""
Orchestrator Agent
Executes plans with parallel DAG execution
"""
import json
from typing import Dict, Any, Optional, List

from agents.base_agent import BaseAgent, AgentConfig
from core.a2a_bus import Message, MessageType, get_bus
from core.dag import DAG, DAGTask, TaskStatus
from core.dag_executor import DAGExecutor, create_executor
from mcp.server import ToolCategory, get_mcp_server


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent
    
    Responsibilities:
    - Execute plans using parallel DAG execution
    - Coordinate between agents
    - Handle task dependencies
    - Aggregate results
    - Handle failures gracefully
    """
    
    def __init__(self, max_workers: int = 4):
        config = AgentConfig(
            name="Orchestrator Agent",
            description="I orchestrate plan execution. I coordinate agents and execute tasks in parallel when possible.",
            capabilities=[
                "Execute task plans",
                "Parallel task execution",
                "Coordinate multiple agents",
                "Handle dependencies",
                "Aggregate results"
            ],
            tool_categories=[]
        )
        super().__init__(config)
        
        self.max_workers = max_workers
        self.executor = create_executor(max_workers=max_workers)
        self.executor.set_task_handler(self._execute_single_task)
        
        # Agent registry
        self._agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent_id: str, agent: BaseAgent):
        """Register an agent for task execution"""
        self._agents[agent_id] = agent
    
    def _execute_single_task(self, task: DAGTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task - called by DAG executor"""
        agent_id = task.agent
        tool_name = task.tool
        args = task.args
        
        # Get the agent
        agent = self._agents.get(agent_id)
        
        if not agent:
            # Fallback: use MCP directly
            mcp = get_mcp_server()
            result = mcp.tools_call(tool_name, args)
            return result
        
        # Use agent to execute tool
        result = agent.use_tool(tool_name, args)
        return result
    
    def execute_plan(self, plan: Dict, parallel: bool = True) -> Dict[str, Any]:
        """
        Execute a plan
        
        Args:
            plan: The execution plan from planner
            parallel: Whether to use parallel execution
        
        Returns:
            Execution results
        """
        # Convert plan to DAG
        dag = DAG.from_plan(plan)
        
        # Validate
        validation = dag.validate()
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"Invalid plan: {validation['errors']}",
                "tasks_completed": 0,
                "tasks_failed": 0
            }
        
        # Execute
        if parallel:
            result = self.executor.execute(dag, skip_on_failure=False)
        else:
            result = self.executor.execute_sync(dag)
        
        # Format output
        all_outputs = []
        for task_id, task in dag.tasks.items():
            if task.status == TaskStatus.COMPLETED and task_id in result.get("results", {}):
                task_result = result["results"][task_id]
                all_outputs.append({
                    "task_id": task_id,
                    "type": task.tool,
                    "content": task_result.get("content", 
                              task_result.get("result",
                              task_result.get("data", task_result)))
                })
        
        return {
            "success": result.get("success", False),
            "tasks_completed": result.get("tasks_completed", 0),
            "tasks_failed": result.get("tasks_failed", 0),
            "tasks_total": result.get("tasks_total", len(dag.tasks)),
            "task_states": result.get("task_states", {}),
            "all_outputs": all_outputs,
            "final_result": result.get("final_result"),
            "parallel_execution": parallel
        }
    
    def execute_plan_sequential(self, plan: Dict) -> Dict[str, Any]:
        """Execute plan sequentially (for debugging or simple cases)"""
        return self.execute_plan(plan, parallel=False)
    
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle orchestration request"""
        if "plan" in task:
            parallel = task.get("parallel", True)
            return self.execute_plan(task["plan"], parallel=parallel)
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
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        base_status = super().get_status()
        base_status["max_workers"] = self.max_workers
        base_status["registered_agents"] = list(self._agents.keys())
        return base_status
