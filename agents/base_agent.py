"""
Base Agent Class
Foundation for all specialized agents with LLM pool support
"""
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.a2a_bus import get_bus, Message, MessageType, A2ABus
from mcp.server import get_mcp_server, MCPServer, ToolCategory
from llm import get_llm_pool, LLMPool


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    name: str
    description: str
    capabilities: List[str]
    tool_categories: List[ToolCategory]


class BaseAgent(ABC):
    """
    Base Agent Class
    
    Every agent:
    - Has a unique ID and name
    - Connects to the A2A bus
    - Has access to MCP tools (filtered by category)
    - Uses LLM pool for reasoning (with fallback)
    - Can send/receive messages
    - Makes autonomous decisions
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.name.lower().replace(" ", "_")
        self.bus: A2ABus = get_bus()
        self.mcp: MCPServer = get_mcp_server()
        self.llm_pool: LLMPool = get_llm_pool()
        self.running = False
        self.message_history: List[Dict] = []
        
        # Register with bus
        self.bus.register_agent(self.agent_id)
    
    # ==================== LLM Reasoning ====================
    
    def think(self, prompt: str, context: Dict = None, preferred_llm: str = None) -> str:
        """
        Use LLM pool to reason about a situation
        Automatically handles fallback between providers
        """
        # Build system prompt based on agent identity
        system_prompt = f"""You are {self.config.name}, an autonomous AI agent.

YOUR ROLE: {self.config.description}

YOUR CAPABILITIES:
{chr(10).join(f'- {c}' for c in self.config.capabilities)}

AVAILABLE TOOLS:
{self._get_my_tools_description()}

CONTEXT:
{json.dumps(context, indent=2) if context else 'None'}

You must respond with clear, actionable decisions. Be autonomous - make decisions, don't ask for clarification."""

        response = self.llm_pool.generate(prompt, system_prompt, preferred_llm)
        
        if response.success:
            return response.content
        else:
            return f"ERROR: {response.error}"
    
    def decide_action(self, task: Dict) -> Dict[str, Any]:
        """
        Given a task, decide what action to take
        Returns: {"action": "use_tool|delegate|respond", "details": {...}}
        """
        prompt = f"""Given this task, decide what to do:

TASK: {json.dumps(task, indent=2)}

You must respond with ONLY a JSON object (no other text):
{{
    "action": "use_tool" or "delegate" or "respond",
    "reasoning": "why you chose this action",
    "tool_name": "name of tool to use (if action=use_tool)",
    "tool_args": {{...}} (if action=use_tool),
    "delegate_to": "agent_id (if action=delegate)",
    "response": "your response (if action=respond)"
}}

JSON ONLY:"""

        response = self.think(prompt, {"my_tools": self._get_my_tools_list()})
        
        # Parse response
        try:
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                return json.loads(match.group())
        except:
            pass
        
        return {"action": "respond", "response": response, "reasoning": "Could not parse decision"}
    
    # ==================== Tool Access ====================
    
    def _get_my_tools_list(self) -> List[str]:
        """Get list of tools this agent can use"""
        tools = []
        for category in self.config.tool_categories:
            tools.extend(self.mcp.get_tools_by_category(category))
        return tools
    
    def _get_my_tools_description(self) -> str:
        """Get description of tools this agent can use"""
        lines = []
        for category in self.config.tool_categories:
            tools = self.mcp.tools_list(category)
            for tool in tools:
                params = ", ".join(tool.get("required", []))
                lines.append(f"- {tool['name']}({params}): {tool['description']}")
        return "\n".join(lines) if lines else "No tools available"
    
    def use_tool(self, tool_name: str, args: Dict) -> Dict[str, Any]:
        """
        Execute a tool via MCP.
        
        Note: the agent's tool_categories are used for planning/prompting
        purposes (so the LLM knows what this agent is for) but are NOT
        enforced at execution time. If the planner misroutes a task - e.g.
        assigning check_file_exists to file_agent because the name looks
        filesystem-y - we just dispatch through MCP anyway rather than
        failing the task. Domain boundaries are advisory, not a hard wall.
        """
        result = self.mcp.tools_call(tool_name, args)
        return result
    
    # ==================== Messaging ====================
    
    def send_message(self, recipient: str, msg_type: MessageType, payload: Dict, 
                     correlation_id: str = None) -> bool:
        """Send a message to another agent"""
        msg = Message.create(
            sender=self.agent_id,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
            correlation_id=correlation_id
        )
        self.message_history.append({"direction": "sent", "message": msg.to_dict()})
        return self.bus.send(msg)
    
    def receive_message(self, timeout: float = None) -> Optional[Message]:
        """Receive a message (blocking)"""
        msg = self.bus.receive(self.agent_id, timeout)
        if msg:
            self.message_history.append({"direction": "received", "message": msg.to_dict()})
        return msg
    
    def check_messages(self) -> Optional[Message]:
        """Check for messages without blocking"""
        msg = self.bus.receive_nowait(self.agent_id)
        if msg:
            self.message_history.append({"direction": "received", "message": msg.to_dict()})
        return msg
    
    def broadcast(self, msg_type: MessageType, payload: Dict):
        """Broadcast to all agents"""
        msg = Message.create(
            sender=self.agent_id,
            recipient="broadcast",
            msg_type=msg_type,
            payload=payload
        )
        self.bus.send(msg)
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    def handle_task(self, task: Dict) -> Dict[str, Any]:
        """Handle a task - each agent implements this differently"""
        pass
    
    @abstractmethod
    def handle_message(self, message: Message) -> Optional[Dict]:
        """Handle an incoming message"""
        pass
    
    # ==================== Lifecycle ====================
    
    def start(self):
        """Start the agent"""
        self.running = True
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        self.bus.unregister_agent(self.agent_id)
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            "id": self.agent_id,
            "name": self.config.name,
            "running": self.running,
            "capabilities": self.config.capabilities,
            "tools": self._get_my_tools_list(),
            "messages_processed": len(self.message_history)
        }
