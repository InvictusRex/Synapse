"""
A2A Protocol Data Models
All Pydantic v2 models for the Agent-to-Agent protocol
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# AGENT DISCOVERY MODELS
# ============================================================

class SkillInputSchema(BaseModel):
    """JSON Schema for a skill's input"""
    type: str = "object"
    properties: dict[str, Any] = {}
    required: list[str] = []


class AgentSkill(BaseModel):
    """A skill that an agent can perform"""
    id: str
    name: str
    description: str
    input_schema: Optional[SkillInputSchema] = None
    example_prompts: list[str] = []


class AgentCapabilities(BaseModel):
    """Capability flags for the agent"""
    streaming: bool = True
    push_notifications: bool = True
    state_transition_history: bool = True


class AuthScheme(BaseModel):
    """Authentication scheme supported by the agent"""
    scheme: str  # "bearer", "apiKey", "oauth2"
    description: str = ""
    config: dict[str, Any] = {}


class AgentCard(BaseModel):
    """Agent Card - served at /.well-known/agent.json"""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    capabilities: AgentCapabilities = AgentCapabilities()
    skills: list[AgentSkill] = []
    auth_schemes: list[AuthScheme] = []


# ============================================================
# MESSAGE MODELS
# ============================================================

class MessageRole(str, Enum):
    """Role of the message sender"""
    USER = "user"
    AGENT = "agent"


class A2AMessage(BaseModel):
    """A message in a task conversation"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = {}


# ============================================================
# ARTIFACT MODELS
# ============================================================

class ArtifactType(str, Enum):
    """Type of artifact produced by an agent"""
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    STRUCTURED_DATA = "structured_data"
    CUSTOM = "custom"


class Artifact(BaseModel):
    """An artifact produced during task execution"""
    type: ArtifactType
    name: str
    mime_type: str = "text/plain"
    description: str = ""
    data: Optional[str] = None  # inline base64 or text content
    uri: Optional[str] = None   # URI reference for large files
    index: int = 0              # for streaming: chunk index
    append: bool = False        # for streaming: append vs replace


# ============================================================
# TASK MODELS
# ============================================================

class TaskStatus(str, Enum):
    """Task state machine states"""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TaskStateTransition(BaseModel):
    """Record of a state transition"""
    from_state: TaskStatus
    to_state: TaskStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""


class Task(BaseModel):
    """A task being processed by the agent system"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.SUBMITTED
    messages: list[A2AMessage] = []
    artifacts: list[Artifact] = []
    history: list[TaskStateTransition] = []
    metadata: dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class TaskSendRequest(BaseModel):
    """Request to create or continue a task"""
    message: str
    task_id: Optional[str] = None  # None = new task, set = continue existing
    skill_id: Optional[str] = None
    metadata: dict[str, Any] = {}


class TaskSendResponse(BaseModel):
    """Response from tasks/send"""
    task: Task


class TaskGetRequest(BaseModel):
    """Request to get task state"""
    task_id: str


class TaskGetResponse(BaseModel):
    """Response from tasks/get"""
    task: Task


class TaskCancelRequest(BaseModel):
    """Request to cancel a task"""
    task_id: str
    reason: str = ""


class TaskCancelResponse(BaseModel):
    """Response from tasks/cancel"""
    task: Task


class ResubscribeRequest(BaseModel):
    """Request to resubscribe to a task's SSE stream"""
    task_id: str


# ============================================================
# STREAMING MODELS
# ============================================================

class SSEEventType(str, Enum):
    """Types of SSE events"""
    STATUS = "status"
    ARTIFACT = "artifact"
    MESSAGE = "message"
    ERROR = "error"


class SSEEvent(BaseModel):
    """An event sent via Server-Sent Events"""
    event_type: SSEEventType
    task_id: str
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# PUSH NOTIFICATION MODELS
# ============================================================

class WebhookRegistration(BaseModel):
    """Client webhook registration for push notifications"""
    url: str
    events: list[str] = ["task/updated", "task/completed"]
    secret: Optional[str] = None  # for HMAC verification


class WebhookRegistrationResponse(BaseModel):
    """Response from webhook registration"""
    id: str


class PushEvent(BaseModel):
    """A push notification event"""
    event: str  # "task/updated", "task/completed"
    task_id: str
    task: Task
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================
# ERROR MODELS
# ============================================================

class A2AError(BaseModel):
    """Standardized error response"""
    code: int
    message: str
    data: Optional[dict[str, Any]] = None
    retryable: bool = False
    retry_after_seconds: Optional[int] = None
