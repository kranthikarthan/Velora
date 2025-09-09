"""
Pydantic models for API requests and responses
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class AgentState(str, Enum):
    """Agent state enum"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    SCALING = "scaling"
    MAINTENANCE = "maintenance"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class AgentType(str, Enum):
    """Agent type enum"""
    SPECIALIZED = "specialized"
    ORCHESTRATOR = "orchestrator"
    UTILITY = "utility"


class MessageType(str, Enum):
    """Message type enum"""
    CAPABILITY_DISCOVERY_REQUEST = "capability_discovery_request"
    CAPABILITY_ANNOUNCEMENT = "capability_announcement"
    NEGOTIATION_PROPOSAL = "negotiation_proposal"
    NEGOTIATION_RESPONSE = "negotiation_response"
    TASK_EXECUTION_REQUEST = "task_execution_request"
    TASK_EXECUTION_RESPONSE = "task_execution_response"
    STATUS_UPDATE = "status_update"
    PERFORMANCE_REPORT = "performance_report"
    ERROR_REPORT = "error_report"
    HEARTBEAT = "heartbeat"
    ACKNOWLEDGMENT = "acknowledgment"
    TERMINATION = "termination"


# Request Models

class AgentCreate(BaseModel):
    """Agent creation request"""
    agent_type: str = Field(..., description="Type of agent to create")
    agent_id: Optional[str] = Field(None, description="Optional agent ID")
    name: Optional[str] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    capabilities: Optional[List[Dict[str, Any]]] = Field(None, description="Agent capabilities")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Agent configuration")


class TaskSubmit(BaseModel):
    """Task submission request"""
    agent_id: Optional[str] = Field(None, description="Target agent ID (or auto-select)")
    agent_type: Optional[str] = Field(None, description="Agent type for auto-selection")
    task_type: str = Field(..., description="Type of task")
    input_data: Any = Field(None, description="Input data for task")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Task constraints")
    priority: int = Field(5, ge=1, le=10, description="Task priority (1-10)")


class MessageSend(BaseModel):
    """Message send request"""
    message_type: MessageType = Field(..., description="Type of message")
    destination_agent: str = Field(..., description="Destination agent ID")
    payload: Dict[str, Any] = Field(..., description="Message payload")
    priority: int = Field(5, ge=1, le=10, description="Message priority")
    timeout: Optional[int] = Field(None, description="Response timeout in seconds")


class ServiceRegister(BaseModel):
    """Service registration request"""
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    service_category: str = Field(..., description="Service category")
    service_description: str = Field(..., description="Service description")
    capabilities: List[Dict[str, Any]] = Field(..., description="Service capabilities")
    api_specification: Optional[Dict[str, Any]] = Field(None, description="API specification")
    pricing_information: Optional[Dict[str, Any]] = Field(None, description="Pricing information")


class ServiceQuery(BaseModel):
    """Service query request"""
    capabilities: List[str] = Field(..., description="Required capabilities")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


# Response Models

class AgentInfo(BaseModel):
    """Agent information"""
    agent_id: str
    name: str
    state: AgentState
    type: AgentType
    capabilities: List[str]
    metrics: Dict[str, Any]
    uptime_seconds: float


class TaskInfo(BaseModel):
    """Task information"""
    task_id: str
    agent_id: str
    task_type: str
    status: str
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class MessageInfo(BaseModel):
    """Message information"""
    message_id: str
    message_type: MessageType
    source_agent: str
    destination_agent: str
    timestamp: datetime
    status: str
    response: Optional[Any] = None


class ServiceInfo(BaseModel):
    """Service information"""
    service_id: str
    agent_id: str
    service_name: str
    service_version: str
    service_category: str
    status: str
    capabilities: List[Dict[str, Any]]
    registration_timestamp: datetime
    last_heartbeat: datetime


class SystemStatus(BaseModel):
    """System status"""
    instance_id: str
    is_running: bool
    start_time: datetime
    uptime_seconds: float
    environment: str
    version: str
    components: Dict[str, str]


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    instance_id: str
    uptime_seconds: float
    checks: Dict[str, Any]


class ProtocolStats(BaseModel):
    """Protocol statistics"""
    agent_id: str
    active_connections: int
    registered_services: int
    known_agents: int
    active_negotiations: int
    messages_sent: int = 0
    messages_received: int = 0


class AgentMetrics(BaseModel):
    """Agent metrics"""
    total_agents: int
    agents_by_type: Dict[str, int]
    agents_by_state: Dict[str, int]
    agent_metrics: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Success response"""
    success: bool = True
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)