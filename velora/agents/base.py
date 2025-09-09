"""
Base Agent class and common agent functionality
"""

import uuid
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from enum import Enum
from dataclasses import dataclass, field

from velora.core.logging import LoggerMixin
from velora.core.exceptions import AgentError
from velora.protocols import UAICP, UAICPMessage, MessageType, ANP


class AgentState(Enum):
    """Agent lifecycle states"""
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


class AgentType(Enum):
    """Agent types"""
    SPECIALIZED = "specialized"
    ORCHESTRATOR = "orchestrator"
    UTILITY = "utility"


@dataclass
class AgentCapability:
    """Agent capability definition"""
    capability_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfiguration:
    """Agent configuration"""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType = AgentType.SPECIALIZED
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    capabilities: List[AgentCapability] = field(default_factory=list)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    security_policies: Dict[str, Any] = field(default_factory=dict)
    runtime_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskContext:
    """Task execution context"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    input_data: Any = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    deadline: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str = ""
    status: str = "pending"
    output_data: Any = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    @property
    def execution_time(self) -> float:
        """Get execution time in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class Agent(ABC, LoggerMixin):
    """
    Base Agent class
    
    All agents inherit from this base class and implement specific functionality
    """
    
    def __init__(self, configuration: AgentConfiguration):
        """
        Initialize agent
        
        Args:
            configuration: Agent configuration
        """
        self.configuration = configuration
        self.agent_id = configuration.agent_id
        self.name = configuration.name or f"Agent-{self.agent_id[:8]}"
        self.state = AgentState.CREATED
        
        # Communication protocols
        self.uaicp: Optional[UAICP] = None
        self.anp: Optional[ANP] = None
        
        # Task management
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, TaskContext] = {}
        self.completed_tasks: List[TaskResult] = []
        
        # Performance tracking
        self.metrics = {
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "average_execution_time": 0.0,
            "current_load": 0.0,
            "uptime_seconds": 0.0
        }
        
        # Lifecycle management
        self.start_time: Optional[datetime] = None
        self.is_running = False
        self._task_processor: Optional[asyncio.Task] = None
        
        self.log_info(f"Agent {self.name} created", agent_id=self.agent_id)
    
    async def initialize(self, uaicp: UAICP, anp: ANP) -> None:
        """
        Initialize agent with protocol handlers
        
        Args:
            uaicp: UAICP protocol handler
            anp: ANP protocol handler
        """
        try:
            self.state = AgentState.INITIALIZING
            
            self.uaicp = uaicp
            self.anp = anp
            
            # Register capabilities with ANP
            for capability in self.configuration.capabilities:
                self.anp.register_capability(capability)
            
            # Register message handlers
            self._register_message_handlers()
            
            # Perform agent-specific initialization
            await self._initialize()
            
            self.state = AgentState.READY
            self.log_info(f"Agent {self.name} initialized")
            
        except Exception as e:
            self.state = AgentState.FAILED
            self.log_error(f"Failed to initialize agent {self.name}", error=e)
            raise AgentError(f"Initialization failed: {str(e)}", self.agent_id)
    
    @abstractmethod
    async def _initialize(self) -> None:
        """Agent-specific initialization (to be implemented by subclasses)"""
        pass
    
    def _register_message_handlers(self) -> None:
        """Register UAICP message handlers"""
        self.uaicp.register_handler(
            MessageType.TASK_EXECUTION_REQUEST,
            self._handle_task_request
        )
        self.uaicp.register_handler(
            MessageType.STATUS_UPDATE,
            self._handle_status_request
        )
    
    async def start(self) -> None:
        """Start agent"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_time = datetime.utcnow()
        self.state = AgentState.READY
        
        # Start task processor
        self._task_processor = asyncio.create_task(self._process_tasks())
        
        # Start agent-specific services
        await self._start()
        
        self.log_info(f"Agent {self.name} started")
    
    @abstractmethod
    async def _start(self) -> None:
        """Agent-specific start logic (to be implemented by subclasses)"""
        pass
    
    async def stop(self) -> None:
        """Stop agent"""
        if not self.is_running:
            return
        
        self.state = AgentState.STOPPING
        self.is_running = False
        
        # Stop task processor
        if self._task_processor:
            self._task_processor.cancel()
            try:
                await self._task_processor
            except asyncio.CancelledError:
                pass
        
        # Stop agent-specific services
        await self._stop()
        
        self.state = AgentState.STOPPED
        self.log_info(f"Agent {self.name} stopped")
    
    @abstractmethod
    async def _stop(self) -> None:
        """Agent-specific stop logic (to be implemented by subclasses)"""
        pass
    
    async def _process_tasks(self) -> None:
        """Process tasks from queue"""
        while self.is_running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                # Update state
                self.state = AgentState.BUSY
                self.active_tasks[task.task_id] = task
                
                # Process task
                result = await self.process_task(task)
                
                # Update metrics
                self._update_metrics(result)
                
                # Store result
                self.completed_tasks.append(result)
                if len(self.completed_tasks) > 100:
                    self.completed_tasks = self.completed_tasks[-100:]
                
                # Clean up
                del self.active_tasks[task.task_id]
                
                # Update state
                if self.task_queue.empty():
                    self.state = AgentState.READY
                elif self.task_queue.qsize() > 10:
                    self.state = AgentState.OVERLOADED
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.log_error("Task processing error", error=e)
    
    @abstractmethod
    async def process_task(self, task: TaskContext) -> TaskResult:
        """
        Process a task (to be implemented by subclasses)
        
        Args:
            task: Task context
        
        Returns:
            Task result
        """
        pass
    
    async def submit_task(self, task: TaskContext) -> str:
        """
        Submit task for processing
        
        Args:
            task: Task to process
        
        Returns:
            Task ID
        """
        if self.state not in [AgentState.READY, AgentState.BUSY]:
            raise AgentError(
                f"Agent not ready to accept tasks (state: {self.state.value})",
                self.agent_id
            )
        
        await self.task_queue.put(task)
        
        self.log_debug(f"Task {task.task_id} submitted")
        return task.task_id
    
    def _update_metrics(self, result: TaskResult) -> None:
        """Update performance metrics"""
        self.metrics["tasks_processed"] += 1
        
        if result.status == "completed":
            self.metrics["tasks_succeeded"] += 1
        else:
            self.metrics["tasks_failed"] += 1
        
        # Update average execution time
        if result.execution_time > 0:
            current_avg = self.metrics["average_execution_time"]
            total_tasks = self.metrics["tasks_processed"]
            new_avg = ((current_avg * (total_tasks - 1)) + result.execution_time) / total_tasks
            self.metrics["average_execution_time"] = new_avg
        
        # Update current load
        self.metrics["current_load"] = len(self.active_tasks) / 10.0  # Normalize to 0-1
    
    async def _handle_task_request(self, message: UAICPMessage) -> UAICPMessage:
        """Handle incoming task execution request"""
        try:
            # Create task context from message
            task = TaskContext(
                task_type=message.payload.get("task_type", ""),
                input_data=message.payload.get("input_data"),
                parameters=message.payload.get("parameters", {}),
                constraints=message.payload.get("constraints", {}),
                priority=message.payload.get("priority", 5)
            )
            
            # Submit task
            task_id = await self.submit_task(task)
            
            # Return acknowledgment
            return self.uaicp.create_message(
                MessageType.ACKNOWLEDGMENT,
                message.source_agent.agent_id,
                {
                    "task_id": task_id,
                    "status": "accepted",
                    "estimated_completion": self._estimate_completion_time()
                }
            )
            
        except Exception as e:
            # Return error
            return self.uaicp.create_message(
                MessageType.ERROR_REPORT,
                message.source_agent.agent_id,
                {
                    "error": str(e),
                    "task_id": message.payload.get("task_id", "unknown")
                }
            )
    
    async def _handle_status_request(self, message: UAICPMessage) -> UAICPMessage:
        """Handle status update request"""
        status = self.get_status()
        
        return self.uaicp.create_message(
            MessageType.STATUS_UPDATE,
            message.source_agent.agent_id,
            status
        )
    
    def _estimate_completion_time(self) -> str:
        """Estimate task completion time"""
        # Simple estimation based on queue size and average execution time
        queue_size = self.task_queue.qsize()
        avg_time = self.metrics["average_execution_time"]
        
        if avg_time > 0:
            estimated_seconds = queue_size * avg_time
            estimated_time = datetime.utcnow() + timedelta(seconds=estimated_seconds)
            return estimated_time.isoformat()
        
        return (datetime.utcnow() + timedelta(minutes=1)).isoformat()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        uptime = 0.0
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "type": self.configuration.agent_type.value,
            "capabilities": [cap.name for cap in self.configuration.capabilities],
            "metrics": self.metrics,
            "active_tasks": len(self.active_tasks),
            "queued_tasks": self.task_queue.qsize(),
            "uptime_seconds": uptime
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            "status": "healthy",
            "agent_id": self.agent_id,
            "state": self.state.value,
            "checks": {}
        }
        
        # Check state
        if self.state == AgentState.FAILED:
            health["status"] = "unhealthy"
            health["checks"]["state"] = "failed"
        elif self.state == AgentState.OVERLOADED:
            health["status"] = "degraded"
            health["checks"]["state"] = "overloaded"
        else:
            health["checks"]["state"] = "ok"
        
        # Check task processing
        if self.metrics["tasks_failed"] > self.metrics["tasks_succeeded"]:
            health["status"] = "degraded"
            health["checks"]["task_processing"] = "high_failure_rate"
        else:
            health["checks"]["task_processing"] = "ok"
        
        # Check load
        if self.metrics["current_load"] > 0.8:
            health["status"] = "degraded"
            health["checks"]["load"] = "high"
        else:
            health["checks"]["load"] = "ok"
        
        return health