"""
Synapse - Multi-Agent System
Main orchestration class
"""
import os
import sys
import json
from typing import Dict, Any, Optional, Callable

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load .env from project directory
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

from llm import init_llm_pool, get_llm_pool
from mcp import get_mcp_server
from memory import get_persistent_memory, get_vector_memory
from core import get_bus
from tools import register_all_tools
from server import get_a2a_server, start_a2a_server, stop_a2a_server

from agents import (
    InteractionAgent, PlannerAgent, OrchestratorAgent,
    FileAgent, ContentAgent, WebAgent, SystemAgent,
    StateAgent, PerceptionAgent
)


class Synapse:
    """
    Synapse - Multi-Agent AI System
    
    Features:
    - Multi-LLM support with automatic fallback (Groq, Gemini)
    - Parallel DAG execution for task planning
    - Persistent memory for context retention
    - A2A (Agent-to-Agent) communication bus
    - MCP (Model Context Protocol) tool registry
    - HTTP server for external integration
    """
    
    def __init__(self, working_dir: str = None, parallel: bool = True, max_workers: int = 4):
        """
        Initialize Synapse
        
        Args:
            working_dir: Working directory for file operations
            parallel: Enable parallel task execution
            max_workers: Max parallel workers
        """
        self.working_dir = working_dir or os.getcwd()
        self.parallel = parallel
        self.max_workers = max_workers
        self.initialized = False
        
        # Components
        self.llm_pool = None
        self.mcp_server = None
        self.memory = None
        self.vector_memory = None
        self.bus = None
        self.a2a_server = None
        
        # Agents
        self.interaction_agent = None
        self.planner_agent = None
        self.orchestrator_agent = None
        self.file_agent = None
        self.content_agent = None
        self.web_agent = None
        self.system_agent = None
        # Phase 1 & 2 additions
        self.state_agent = None
        self.perception_agent = None
        
        # Callbacks
        self._progress_callback: Optional[Callable] = None
        
        # State
        self.last_result = None
        self.execution_log = []
    
    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            # Initialize LLM Pool
            self.llm_pool = init_llm_pool()
            
            # Initialize MCP and register tools
            self.mcp_server = get_mcp_server()
            tools_count = register_all_tools()
            
            # Initialize memory
            self.memory = get_persistent_memory()
            self.vector_memory = get_vector_memory()
            
            # Initialize A2A bus
            self.bus = get_bus()
            
            # Initialize A2A HTTP server (not started by default)
            self.a2a_server = get_a2a_server()
            
            # Initialize agents
            self._init_agents()
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"[Synapse] Initialization failed: {e}")
            return False
    
    def _init_agents(self):
        """Initialize all agents"""
        # Core agents
        self.interaction_agent = InteractionAgent()
        self.planner_agent = PlannerAgent()
        self.orchestrator_agent = OrchestratorAgent(max_workers=self.max_workers)
        
        # Worker agents
        self.file_agent = FileAgent()
        self.content_agent = ContentAgent()
        self.web_agent = WebAgent()
        self.system_agent = SystemAgent()
        # Phase 1 & 2: observational agents
        self.state_agent = StateAgent()
        self.perception_agent = PerceptionAgent()
        
        # Register workers with orchestrator
        self.orchestrator_agent.register_agent("file_agent", self.file_agent)
        self.orchestrator_agent.register_agent("content_agent", self.content_agent)
        self.orchestrator_agent.register_agent("web_agent", self.web_agent)
        self.orchestrator_agent.register_agent("system_agent", self.system_agent)
        self.orchestrator_agent.register_agent("state_agent", self.state_agent)
        self.orchestrator_agent.register_agent("perception_agent", self.perception_agent)
        
        # Set working directory for planner
        self.planner_agent.set_working_dir(self.working_dir)
        
        # Start all agents
        for agent in [self.interaction_agent, self.planner_agent, self.orchestrator_agent,
                      self.file_agent, self.content_agent, self.web_agent, self.system_agent,
                      self.state_agent, self.perception_agent]:
            agent.start()
    
    def set_working_dir(self, working_dir: str):
        """Set working directory"""
        self.working_dir = working_dir
        if self.planner_agent:
            self.planner_agent.set_working_dir(working_dir)
    
    def set_progress_callback(self, callback: Callable[[str, str], None]):
        """Set callback for progress updates: callback(stage, message)"""
        self._progress_callback = callback
    
    def _notify_progress(self, stage: str, message: str):
        """Notify progress"""
        if self._progress_callback:
            try:
                self._progress_callback(stage, message)
            except:
                pass
    
    def process(self, user_input: str, working_dir: str = None) -> Dict[str, Any]:
        """
        Process a user request through the full pipeline
        
        Pipeline:
        1. Interaction Agent interprets input
        2. Planner Agent creates DAG plan
        3. Orchestrator Agent executes plan (parallel if possible)
        4. Results aggregated and returned
        """
        if not self.initialized:
            if not self.initialize():
                return {"success": False, "error": "System not initialized"}
        
        if working_dir:
            self.set_working_dir(working_dir)
        
        try:
            # Stage 1: Interpret input
            self._notify_progress("interpret", "Analyzing request...")
            interpretation = self.interaction_agent.interpret_input(user_input)
            
            if not interpretation.get("success"):
                return {"success": False, "error": "Failed to interpret input"}
            
            request = interpretation.get("interpretation", {})
            
            # Stage 2: Create plan
            self._notify_progress("plan", "Creating execution plan...")
            plan_result = self.planner_agent.create_plan(request)
            
            if not plan_result.get("success"):
                return {
                    "success": False, 
                    "error": plan_result.get("error", "Planning failed"),
                    "raw": plan_result.get("raw", "")
                }
            
            plan = plan_result.get("plan", {})
            
            # Validate plan
            validation = self.planner_agent.validate_plan(plan)
            if not validation.get("valid"):
                return {"success": False, "error": f"Invalid plan: {validation.get('errors')}"}
            
            # Stage 3: Execute plan
            self._notify_progress("execute", "Executing tasks...")
            execution_result = self.orchestrator_agent.execute_plan(plan, parallel=self.parallel)
            
            # Store in memory
            self._store_execution(user_input, plan, execution_result)
            
            # Format result
            result = {
                "success": execution_result.get("success", False),
                "tasks_completed": execution_result.get("tasks_completed", 0),
                "tasks_failed": execution_result.get("tasks_failed", 0),
                "tasks_total": execution_result.get("tasks_total", 0),
                "parallel_execution": execution_result.get("parallel_execution", False),
                "plan": plan,
                "task_states": execution_result.get("task_states", {}),
                "all_outputs": execution_result.get("all_outputs", []),
                "final_result": execution_result.get("final_result")
            }
            
            self.last_result = result
            self.execution_log.append({
                "input": user_input,
                "result": result
            })
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _store_execution(self, user_input: str, plan: Dict, result: Dict):
        """Store execution in memory for future reference"""
        try:
            # Store in persistent memory
            self.memory.store(
                content=user_input,
                metadata={
                    "type": "execution",
                    "plan_id": plan.get("plan_id"),
                    "success": result.get("success"),
                    "tasks": result.get("tasks_total", 0)
                }
            )
            
            # Store in vector memory for semantic search
            self.vector_memory.store(
                content=f"{user_input} - {plan.get('description', '')}",
                metadata={"plan_id": plan.get("plan_id")}
            )
        except:
            pass
    
    def search_memory(self, query: str, limit: int = 5) -> list:
        """Search persistent memory"""
        return self.memory.search(query, limit)
    
    def search_similar(self, query: str, limit: int = 5) -> list:
        """Search vector memory for similar content"""
        return self.vector_memory.search_similar(query, limit)
    
    # ==================== A2A Server ====================
    
    def start_server(self) -> bool:
        """Start the A2A HTTP server"""
        if self.a2a_server:
            self.a2a_server.set_task_handler(self.process)
            return self.a2a_server.start()
        return False
    
    def stop_server(self):
        """Stop the A2A HTTP server"""
        if self.a2a_server:
            self.a2a_server.stop()
    
    def is_server_running(self) -> bool:
        """Check if A2A server is running"""
        return self.a2a_server.is_running() if self.a2a_server else False
    
    def get_server_url(self) -> Optional[str]:
        """Get A2A server URL"""
        if self.a2a_server and self.a2a_server.is_running():
            return f"http://{self.a2a_server.host}:{self.a2a_server.port}"
        return None
    
    # ==================== Status ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        status = {
            "initialized": self.initialized,
            "working_dir": self.working_dir,
            "parallel_enabled": self.parallel,
            "max_workers": self.max_workers
        }
        
        if self.initialized:
            status["llm_pool"] = self.llm_pool.get_stats() if self.llm_pool else None
            status["mcp"] = self.mcp_server.get_status() if self.mcp_server else None
            status["memory"] = self.memory.get_stats() if self.memory else None
            status["vector_memory"] = self.vector_memory.get_stats() if self.vector_memory else None
            status["a2a_bus"] = self.bus.get_stats() if self.bus else None
            status["a2a_server"] = self.a2a_server.get_status() if self.a2a_server else None
            
            status["agents"] = {
                "interaction": self.interaction_agent.get_status() if self.interaction_agent else None,
                "planner": self.planner_agent.get_status() if self.planner_agent else None,
                "orchestrator": self.orchestrator_agent.get_status() if self.orchestrator_agent else None,
                "file": self.file_agent.get_status() if self.file_agent else None,
                "content": self.content_agent.get_status() if self.content_agent else None,
                "web": self.web_agent.get_status() if self.web_agent else None,
                "system": self.system_agent.get_status() if self.system_agent else None,
                "state": self.state_agent.get_status() if self.state_agent else None,
                "perception": self.perception_agent.get_status() if self.perception_agent else None,
            }
        
        return status
    
    def get_tools(self) -> list:
        """Get all available tools"""
        if self.mcp_server:
            return self.mcp_server.tools_list()
        return []
    
    def shutdown(self):
        """Shutdown the system"""
        # Stop server
        self.stop_server()
        
        # Stop agents
        agents = [self.interaction_agent, self.planner_agent, self.orchestrator_agent,
                  self.file_agent, self.content_agent, self.web_agent, self.system_agent,
                  self.state_agent, self.perception_agent]
        for agent in agents:
            if agent:
                agent.stop()
        
        # Shutdown LLM pool
        if self.llm_pool:
            self.llm_pool.shutdown()
        
        self.initialized = False


# Convenience function
def create_synapse(working_dir: str = None, parallel: bool = True) -> Synapse:
    """Create and initialize a Synapse instance"""
    synapse = Synapse(working_dir=working_dir, parallel=parallel)
    synapse.initialize()
    return synapse
