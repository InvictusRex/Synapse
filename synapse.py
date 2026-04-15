"""
Synapse - Multi-Agent System
Main system that initializes and coordinates all agents
"""
import os
import sys
from typing import Dict, Any, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.a2a_bus import get_bus, reset_bus, Message, MessageType
from mcp.server import get_mcp_server
from tools.all_tools import register_all_tools

from agents.interaction_agent import InteractionAgent
from agents.planner_agent import PlannerAgent
from agents.file_agent import FileAgent
from agents.content_agent import ContentAgent
from agents.web_agent import WebAgent
from agents.system_agent import SystemAgent
from agents.codegen_agent import CodeGenAgent
from agents.scaffolding_agent import ScaffoldingAgent
from agents.implementation_agent import ImplementationAgent
from agents.orchestrator_agent import OrchestratorAgent


class Synapse:
    """
    Synapse Multi-Agent System
    
    Architecture:
    User → InteractionAgent → PlannerAgent → OrchestratorAgent → Worker Agents → Result
    
    All agents communicate via A2A Message Bus
    All tools accessed via MCP Server
    """
    
    def __init__(self):
        print("=" * 50)
        print("SYNAPSE - Multi-Agent System")
        print("=" * 50)
        
        # Reset and initialize bus
        reset_bus()
        self.bus = get_bus()
        
        # Initialize MCP and register tools
        self.mcp = get_mcp_server()
        register_all_tools()
        
        # Initialize all agents
        print("\n[Synapse] Initializing agents...")
        self.interaction_agent = InteractionAgent()
        self.planner_agent = PlannerAgent()
        self.file_agent = FileAgent()
        self.content_agent = ContentAgent()
        self.web_agent = WebAgent()
        self.system_agent = SystemAgent()
        self.codegen_agent = CodeGenAgent()
        self.scaffolding_agent = ScaffoldingAgent()
        self.implementation_agent = ImplementationAgent()
        self.orchestrator = OrchestratorAgent()

        # Register worker agents with orchestrator (pass instances, not IDs)
        self.orchestrator.register_worker_agent("file_agent", self.file_agent)
        self.orchestrator.register_worker_agent("content_agent", self.content_agent)
        self.orchestrator.register_worker_agent("web_agent", self.web_agent)
        self.orchestrator.register_worker_agent("system_agent", self.system_agent)
        self.orchestrator.register_worker_agent("codegen_agent", self.codegen_agent)
        self.orchestrator.register_worker_agent("scaffolding_agent", self.scaffolding_agent)
        self.orchestrator.register_worker_agent("implementation_agent", self.implementation_agent)
        
        # Start all agents
        for agent in self.get_all_agents():
            agent.start()
        
        print("\n[Synapse] System ready!")
        print(f"[Synapse] Registered agents: {self.bus.get_registered_agents()}")
        print(f"[Synapse] Available tools: {len(self.mcp.tools)}")
        print("=" * 50)
    
    def get_all_agents(self) -> list:
        """Get all agents"""
        return [
            self.interaction_agent,
            self.planner_agent,
            self.file_agent,
            self.content_agent,
            self.web_agent,
            self.system_agent,
            self.codegen_agent,
            self.scaffolding_agent,
            self.implementation_agent,
            self.orchestrator
        ]
    
    def process(self, user_input: str, working_dir: str = None) -> Dict[str, Any]:
        """
        Process a user request through the multi-agent pipeline
        
        Flow:
        1. InteractionAgent parses input
        2. PlannerAgent creates execution plan
        3. OrchestratorAgent executes plan via worker agents
        4. InteractionAgent formats result
        """
        result = {
            "input": user_input,
            "stages": {},
            "success": False
        }
        
        # Set working directory if provided
        if working_dir:
            self.planner_agent.set_working_dir(working_dir)
        
        try:
            # Stage 1: Parse user input
            print("\n[Stage 1] Interaction Agent: Parsing input...")
            parsed = self.interaction_agent.process_user_input(user_input)
            result["stages"]["parsing"] = parsed
            
            if not parsed.get("success"):
                result["error"] = "Failed to parse input"
                return result
            
            # Stage 2: Create execution plan
            print("\n[Stage 2] Planner Agent: Creating plan...")
            plan_result = self.planner_agent.create_plan(parsed.get("parsed", {}))
            result["stages"]["planning"] = plan_result
            
            if not plan_result.get("success"):
                result["error"] = "Failed to create plan"
                return result
            
            plan = plan_result.get("plan", {})
            print(f"[Stage 2] Plan created with {len(plan.get('tasks', []))} tasks")
            
            # Stage 3: Execute plan
            print("\n[Stage 3] Orchestrator: Executing plan...")
            execution_result = self.orchestrator.execute_plan(plan)
            result["stages"]["execution"] = execution_result
            
            # Stage 4: Format result
            print("\n[Stage 4] Formatting result...")
            formatted = self.interaction_agent.format_result(execution_result)
            result["formatted_result"] = formatted
            
            result["success"] = execution_result.get("success", False)
            result["final_output"] = execution_result.get("final_result", {})
            
        except Exception as e:
            result["error"] = str(e)
            print(f"[Synapse] Error: {e}")
        
        return result
    
    def set_working_dir(self, working_dir: str):
        """Set the working directory for file operations"""
        self.planner_agent.set_working_dir(working_dir)
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "agents": [agent.get_status() for agent in self.get_all_agents()],
            "bus": {
                "registered_agents": self.bus.get_registered_agents(),
                "message_count": len(self.bus.message_log)
            },
            "mcp": self.mcp.get_execution_stats()
        }
    
    def get_message_history(self, limit: int = 50) -> list:
        """Get A2A message history"""
        return self.bus.get_message_history(limit)
    
    def shutdown(self):
        """Shutdown the system"""
        print("\n[Synapse] Shutting down...")
        for agent in self.get_all_agents():
            agent.stop()
        print("[Synapse] Goodbye!")


# Global instance
_synapse_instance = None

def get_synapse() -> Synapse:
    """Get or create Synapse instance"""
    global _synapse_instance
    if _synapse_instance is None:
        _synapse_instance = Synapse()
    return _synapse_instance

def reset_synapse():
    """Reset Synapse (for testing)"""
    global _synapse_instance
    if _synapse_instance:
        _synapse_instance.shutdown()
    _synapse_instance = None
