"""
A2A (Agent-to-Agent) Communication Bus
Simple implementation using Python queues
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from queue import Queue
from datetime import datetime
import threading


@dataclass
class A2AMessage:
    """Standard message format for agent communication"""
    id: str
    sender: str
    recipient: str
    msg_type: str  # task_request, task_result, status_update
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "from": self.sender,
            "to": self.recipient,
            "type": self.msg_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat()
        }


class A2ABus:
    """
    Agent-to-Agent Message Bus
    Enables decoupled communication between agents
    """
    
    def __init__(self):
        self.queues: Dict[str, Queue] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_log: List[A2AMessage] = []
        self._lock = threading.Lock()
    
    def register_agent(self, agent_id: str):
        """Register an agent to receive messages"""
        with self._lock:
            if agent_id not in self.queues:
                self.queues[agent_id] = Queue()
                self.subscribers[agent_id] = []
                print(f"[A2A] Agent registered: {agent_id}")
    
    def send(self, message: A2AMessage):
        """Send a message to an agent"""
        with self._lock:
            self.message_log.append(message)
            
            # Direct queue delivery
            if message.recipient in self.queues:
                self.queues[message.recipient].put(message)
            
            # Notify subscribers
            if message.recipient in self.subscribers:
                for callback in self.subscribers[message.recipient]:
                    try:
                        callback(message)
                    except Exception as e:
                        print(f"[A2A] Subscriber error: {e}")
            
            print(f"[A2A] {message.sender} → {message.recipient}: {message.msg_type}")
    
    def receive(self, agent_id: str, timeout: float = None) -> Optional[A2AMessage]:
        """Receive a message for an agent (blocking)"""
        if agent_id not in self.queues:
            return None
        try:
            return self.queues[agent_id].get(timeout=timeout)
        except:
            return None
    
    def subscribe(self, agent_id: str, callback: Callable):
        """Subscribe to messages for an agent"""
        with self._lock:
            if agent_id not in self.subscribers:
                self.subscribers[agent_id] = []
            self.subscribers[agent_id].append(callback)
    
    def broadcast(self, sender: str, msg_type: str, payload: Dict):
        """Broadcast a message to all registered agents"""
        for agent_id in self.queues.keys():
            if agent_id != sender:
                msg = A2AMessage(
                    id=f"broadcast_{datetime.now().timestamp()}",
                    sender=sender,
                    recipient=agent_id,
                    msg_type=msg_type,
                    payload=payload
                )
                self.send(msg)
    
    def get_message_history(self) -> List[Dict]:
        """Get all messages for debugging/display"""
        return [m.to_dict() for m in self.message_log]


# Global bus instance
_bus_instance = None

def get_bus() -> A2ABus:
    """Get the global A2A bus instance"""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = A2ABus()
    return _bus_instance
