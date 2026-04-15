"""
Agents Package
All specialized agents for the Synapse system
"""
from agents.base_agent import BaseAgent, AgentConfig
from agents.interaction_agent import InteractionAgent
from agents.planner_agent import PlannerAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.file_agent import FileAgent
from agents.content_agent import ContentAgent
from agents.web_agent import WebAgent
from agents.system_agent import SystemAgent

__all__ = [
    'BaseAgent', 'AgentConfig',
    'InteractionAgent',
    'PlannerAgent',
    'OrchestratorAgent',
    'FileAgent',
    'ContentAgent',
    'WebAgent',
    'SystemAgent'
]
