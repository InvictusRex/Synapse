"""
A2A (Agent-to-Agent) Message Bus
Central communication system for all agents
"""
import uuid
import time
import threading
from queue import Queue, Empty
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """Types of messages that can be sent between agents"""
    # Requests
    TASK_REQUEST = "task_request"
    TOOL_REQUEST = "tool_request"
    INFO_REQUEST = "info_request"
    
    # Responses
    TASK_RESULT = "task_result"
    TOOL_RESULT = "tool_result"
    INFO_RESPONSE = "info_response"
    
    # Status
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    
    # Control
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"


@dataclass
class Message:
    """A2A Message structure"""
    id: str
    sender: str
    recipient: str  # Can be specific agent or "broadcast"
    msg_type: MessageType
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None  # For request-response pairing
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.msg_type.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat()
        }
    
    @staticmethod
    def create(sender: str, recipient: str, msg_type: MessageType, 
               payload: Dict, correlation_id: str = None) -> 'Message':
        return Message(
            id=str(uuid.uuid4())[:8],
            sender=sender,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
            correlation_id=correlation_id
        )


class A2ABus:
    """
    Agent-to-Agent Message Bus
    Handles all inter-agent communication
    """
    
    def __init__(self):
        self.agents: Dict[str, Queue] = {}  # agent_id -> message queue
        self.subscribers: Dict[MessageType, List[str]] = {}  # msg_type -> [agent_ids]
        self.message_log: List[Message] = []
        self.lock = threading.Lock()
        self.running = True
        
    def register_agent(self, agent_id: str) -> bool:
        """Register an agent to the bus"""
        with self.lock:
            if agent_id in self.agents:
                return False
            
            self.agents[agent_id] = Queue()
            self._log(f"Agent registered: {agent_id}")
            return True
    
    def unregister_agent(self, agent_id: str):
        """Remove an agent from the bus"""
        with self.lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                # Remove from all subscriptions
                for msg_type in self.subscribers:
                    if agent_id in self.subscribers[msg_type]:
                        self.subscribers[msg_type].remove(agent_id)
                self._log(f"Agent unregistered: {agent_id}")
    
    def subscribe(self, agent_id: str, msg_type: MessageType):
        """Subscribe an agent to a message type"""
        with self.lock:
            if msg_type not in self.subscribers:
                self.subscribers[msg_type] = []
            if agent_id not in self.subscribers[msg_type]:
                self.subscribers[msg_type].append(agent_id)
    
    def send(self, message: Message) -> bool:
        """Send a message to an agent or broadcast"""
        with self.lock:
            self.message_log.append(message)
            
            if message.recipient == "broadcast":
                # Send to all agents except sender
                for agent_id, queue in self.agents.items():
                    if agent_id != message.sender:
                        queue.put(message)
                self._log(f"[BROADCAST] {message.sender} → ALL: {message.msg_type.value}")
            else:
                # Send to specific agent
                if message.recipient in self.agents:
                    self.agents[message.recipient].put(message)
                    self._log(f"[MSG] {message.sender} → {message.recipient}: {message.msg_type.value}")
                    return True
                else:
                    self._log(f"[ERROR] Agent not found: {message.recipient}")
                    return False
            
            return True
    
    def receive(self, agent_id: str, timeout: float = None) -> Optional[Message]:
        """Receive a message for an agent (blocking)"""
        if agent_id not in self.agents:
            return None
        
        try:
            return self.agents[agent_id].get(timeout=timeout)
        except Empty:
            return None
    
    def receive_nowait(self, agent_id: str) -> Optional[Message]:
        """Receive a message without blocking"""
        if agent_id not in self.agents:
            return None
        
        try:
            return self.agents[agent_id].get_nowait()
        except Empty:
            return None
    
    def has_messages(self, agent_id: str) -> bool:
        """Check if agent has pending messages"""
        if agent_id not in self.agents:
            return False
        return not self.agents[agent_id].empty()
    
    def get_registered_agents(self) -> List[str]:
        """Get list of registered agents"""
        return list(self.agents.keys())
    
    def get_message_history(self, limit: int = 50) -> List[Dict]:
        """Get recent message history"""
        return [m.to_dict() for m in self.message_log[-limit:]]
    
    def _log(self, message: str):
        """Internal logging"""
        print(f"[A2A Bus] {message}")


# Global bus instance
_bus_instance = None

def get_bus() -> A2ABus:
    """Get the global A2A bus instance"""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = A2ABus()
    return _bus_instance

def reset_bus():
    """Reset the bus (for testing)"""
    global _bus_instance
    _bus_instance = A2ABus()
