"""
A2A (Agent-to-Agent) Message Bus
Inter-agent communication system
"""
import uuid
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from datetime import datetime


class MessageType(Enum):
    """Types of messages in the A2A system"""
    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    BROADCAST = "broadcast"
    QUERY = "query"
    RESPONSE = "response"


@dataclass
class Message:
    """A2A Message"""
    id: str
    sender: str
    recipient: str
    msg_type: MessageType
    payload: Dict[str, Any]
    timestamp: float
    correlation_id: Optional[str] = None
    ttl: int = 60  # Time to live in seconds
    
    @classmethod
    def create(cls, sender: str, recipient: str, msg_type: MessageType,
               payload: Dict[str, Any], correlation_id: str = None) -> 'Message':
        return cls(
            id=str(uuid.uuid4())[:8],
            sender=sender,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
            timestamp=time.time(),
            correlation_id=correlation_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.msg_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "ttl": self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            sender=data.get("sender", "unknown"),
            recipient=data.get("recipient", "unknown"),
            msg_type=MessageType(data.get("type", "task_request")),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            correlation_id=data.get("correlation_id"),
            ttl=data.get("ttl", 60)
        )
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class A2ABus:
    """
    Agent-to-Agent Message Bus
    
    Features:
    - Asynchronous message passing
    - Topic-based routing
    - Message persistence (optional)
    - Dead letter queue for failed messages
    - Message expiration
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._queues: Dict[str, Queue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._message_log: List[Message] = []
        self._dead_letters: List[Message] = []
        self._lock = threading.Lock()
        self._running = False
        self._dispatcher_thread: Optional[threading.Thread] = None
        self._stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_expired": 0,
            "messages_failed": 0
        }
        self._initialized = True
    
    def register_agent(self, agent_id: str):
        """Register an agent with the bus"""
        with self._lock:
            if agent_id not in self._queues:
                self._queues[agent_id] = Queue()
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        with self._lock:
            if agent_id in self._queues:
                del self._queues[agent_id]
            if agent_id in self._subscribers:
                del self._subscribers[agent_id]
    
    def subscribe(self, agent_id: str, callback: Callable[[Message], None]):
        """Subscribe to messages for an agent"""
        with self._lock:
            if agent_id not in self._subscribers:
                self._subscribers[agent_id] = []
            self._subscribers[agent_id].append(callback)
    
    def unsubscribe(self, agent_id: str, callback: Callable = None):
        """Unsubscribe from messages"""
        with self._lock:
            if agent_id in self._subscribers:
                if callback:
                    self._subscribers[agent_id].remove(callback)
                else:
                    del self._subscribers[agent_id]
    
    def send(self, message: Message) -> bool:
        """Send a message to an agent"""
        self._stats["messages_sent"] += 1
        
        # Log message
        self._message_log.append(message)
        if len(self._message_log) > 1000:
            self._message_log = self._message_log[-500:]
        
        # Handle broadcast
        if message.recipient == "broadcast":
            return self._broadcast(message)
        
        # Direct message
        with self._lock:
            if message.recipient in self._queues:
                self._queues[message.recipient].put(message)
                self._stats["messages_delivered"] += 1
                
                # Notify subscribers
                if message.recipient in self._subscribers:
                    for callback in self._subscribers[message.recipient]:
                        try:
                            callback(message)
                        except Exception:
                            pass
                
                return True
            else:
                self._dead_letters.append(message)
                self._stats["messages_failed"] += 1
                return False
    
    def _broadcast(self, message: Message) -> bool:
        """Broadcast message to all agents"""
        sent = False
        with self._lock:
            for agent_id, queue in self._queues.items():
                if agent_id != message.sender:
                    queue.put(message)
                    self._stats["messages_delivered"] += 1
                    sent = True
        return sent
    
    def receive(self, agent_id: str, timeout: float = None) -> Optional[Message]:
        """Receive a message (blocking)"""
        queue = self._queues.get(agent_id)
        if not queue:
            return None
        
        try:
            message = queue.get(timeout=timeout)
            
            # Check expiration
            if message.is_expired():
                self._stats["messages_expired"] += 1
                return None
            
            return message
        except Empty:
            return None
    
    def receive_nowait(self, agent_id: str) -> Optional[Message]:
        """Receive a message (non-blocking)"""
        queue = self._queues.get(agent_id)
        if not queue:
            return None
        
        try:
            message = queue.get_nowait()
            if message.is_expired():
                self._stats["messages_expired"] += 1
                return None
            return message
        except Empty:
            return None
    
    def peek(self, agent_id: str) -> int:
        """Get number of pending messages"""
        queue = self._queues.get(agent_id)
        return queue.qsize() if queue else 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bus statistics"""
        return {
            **self._stats,
            "registered_agents": list(self._queues.keys()),
            "agent_count": len(self._queues),
            "dead_letter_count": len(self._dead_letters),
            "message_log_size": len(self._message_log)
        }
    
    def get_message_history(self, limit: int = 100) -> List[Dict]:
        """Get recent message history"""
        return [m.to_dict() for m in self._message_log[-limit:]]
    
    def get_dead_letters(self) -> List[Dict]:
        """Get dead letter queue"""
        return [m.to_dict() for m in self._dead_letters]
    
    def clear_dead_letters(self):
        """Clear dead letter queue"""
        self._dead_letters.clear()
    
    def reset(self):
        """Reset the bus"""
        with self._lock:
            for queue in self._queues.values():
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except Empty:
                        break
            self._message_log.clear()
            self._dead_letters.clear()
            self._stats = {
                "messages_sent": 0,
                "messages_delivered": 0,
                "messages_expired": 0,
                "messages_failed": 0
            }


# Global bus instance
_bus: Optional[A2ABus] = None

def get_bus() -> A2ABus:
    """Get or create the global A2A bus"""
    global _bus
    if _bus is None:
        _bus = A2ABus()
    return _bus
