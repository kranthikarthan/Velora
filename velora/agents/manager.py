"""
Agent Manager for lifecycle management of all agents
"""

import asyncio
from typing import Dict, Any, Optional, List, Type
from datetime import datetime
import uuid

from velora.core.config import Settings
from velora.core.logging import LoggerMixin
from velora.core.exceptions import AgentError, ResourceNotFoundError
from velora.agents.base import Agent, AgentState, AgentConfiguration
from velora.protocols import ProtocolManager


class AgentManager(LoggerMixin):
    """
    Manages the lifecycle of all agents in the system
    """
    
    def __init__(self, settings: Settings, protocol_manager: ProtocolManager):
        """
        Initialize agent manager
        
        Args:
            settings: Application settings
            protocol_manager: Protocol manager for agent communication
        """
        self.settings = settings
        self.protocol_manager = protocol_manager
        
        # Agent registry
        self.agents: Dict[str, Agent] = {}
        self.agent_types: Dict[str, Type[Agent]] = {}
        
        # Agent pools for scaling
        self.agent_pools: Dict[str, List[Agent]] = {}
        
        # Monitoring
        self.agent_metrics: Dict[str, Dict[str, Any]] = {}
        
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        self.log_info("Agent manager initialized")
    
    async def initialize(self) -> None:
        """Initialize agent manager"""
        try:
            # Register default agent types
            self._register_default_agent_types()
            
            # Create default agents
            await self._create_default_agents()
            
            self.log_info("Agent manager initialized")
            
        except Exception as e:
            self.log_error("Failed to initialize agent manager", error=e)
            raise AgentError(f"Agent manager initialization failed: {str(e)}", "manager")
    
    def _register_default_agent_types(self) -> None:
        """Register default agent types"""
        from velora.agents.specialized import (
            DataProcessorAgent,
            ProtocolTranslatorAgent,
            APIIntegrationAgent
        )
        
        self.register_agent_type("data_processor", DataProcessorAgent)
        self.register_agent_type("protocol_translator", ProtocolTranslatorAgent)
        self.register_agent_type("api_integration", APIIntegrationAgent)
    
    async def _create_default_agents(self) -> None:
        """Create default agents"""
        # Create one of each type by default
        default_agents = [
            ("data_processor", "default-data-processor"),
            ("protocol_translator", "default-protocol-translator"),
            ("api_integration", "default-api-integration")
        ]
        
        for agent_type, agent_id in default_agents:
            await self.create_agent(agent_type, agent_id)
    
    def register_agent_type(self, type_name: str, agent_class: Type[Agent]) -> None:
        """
        Register a new agent type
        
        Args:
            type_name: Name of the agent type
            agent_class: Agent class
        """
        self.agent_types[type_name] = agent_class
        self.log_info(f"Registered agent type: {type_name}")
    
    async def create_agent(
        self,
        agent_type: str,
        agent_id: Optional[str] = None,
        configuration: Optional[AgentConfiguration] = None
    ) -> Agent:
        """
        Create a new agent
        
        Args:
            agent_type: Type of agent to create
            agent_id: Optional agent ID
            configuration: Optional agent configuration
        
        Returns:
            Created agent instance
        """
        if agent_type not in self.agent_types:
            raise AgentError(f"Unknown agent type: {agent_type}", "manager")
        
        # Generate agent ID if not provided
        if not agent_id:
            agent_id = f"{agent_type}-{uuid.uuid4()}"
        
        # Check if agent already exists
        if agent_id in self.agents:
            raise AgentError(f"Agent {agent_id} already exists", agent_id)
        
        # Create agent instance
        agent_class = self.agent_types[agent_type]
        agent = agent_class(agent_id)
        
        # Override configuration if provided
        if configuration:
            agent.configuration = configuration
        
        # Initialize agent with protocols
        await agent.initialize(
            self.protocol_manager.uaicp,
            self.protocol_manager.anp
        )
        
        # Register agent
        self.agents[agent_id] = agent
        
        # Add to pool
        if agent_type not in self.agent_pools:
            self.agent_pools[agent_type] = []
        self.agent_pools[agent_type].append(agent)
        
        self.log_info(f"Created agent: {agent_id} (type: {agent_type})")
        
        return agent
    
    async def start_agent(self, agent_id: str) -> None:
        """
        Start an agent
        
        Args:
            agent_id: Agent identifier
        """
        agent = self.get_agent(agent_id)
        await agent.start()
        self.log_info(f"Started agent: {agent_id}")
    
    async def stop_agent(self, agent_id: str) -> None:
        """
        Stop an agent
        
        Args:
            agent_id: Agent identifier
        """
        agent = self.get_agent(agent_id)
        await agent.stop()
        self.log_info(f"Stopped agent: {agent_id}")
    
    async def remove_agent(self, agent_id: str) -> None:
        """
        Remove an agent
        
        Args:
            agent_id: Agent identifier
        """
        agent = self.get_agent(agent_id)
        
        # Stop agent if running
        if agent.is_running:
            await agent.stop()
        
        # Remove from pools
        for pool in self.agent_pools.values():
            if agent in pool:
                pool.remove(agent)
        
        # Remove from registry
        del self.agents[agent_id]
        
        self.log_info(f"Removed agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Agent:
        """
        Get agent by ID
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Agent instance
        """
        if agent_id not in self.agents:
            raise ResourceNotFoundError("Agent", agent_id)
        return self.agents[agent_id]
    
    def list_agents(self, agent_type: Optional[str] = None) -> List[Agent]:
        """
        List agents
        
        Args:
            agent_type: Optional filter by agent type
        
        Returns:
            List of agents
        """
        if agent_type:
            return self.agent_pools.get(agent_type, [])
        return list(self.agents.values())
    
    async def get_available_agent(self, agent_type: str) -> Optional[Agent]:
        """
        Get an available agent of specified type
        
        Args:
            agent_type: Type of agent needed
        
        Returns:
            Available agent or None
        """
        if agent_type not in self.agent_pools:
            return None
        
        # Find agent with lowest load
        available_agents = [
            agent for agent in self.agent_pools[agent_type]
            if agent.state in [AgentState.READY, AgentState.BUSY]
        ]
        
        if not available_agents:
            return None
        
        # Sort by current load
        available_agents.sort(key=lambda a: a.metrics.get("current_load", 0))
        
        return available_agents[0]
    
    async def scale_agents(self, agent_type: str, target_count: int) -> None:
        """
        Scale agents of a specific type
        
        Args:
            agent_type: Type of agents to scale
            target_count: Target number of agents
        """
        if agent_type not in self.agent_pools:
            self.agent_pools[agent_type] = []
        
        current_count = len(self.agent_pools[agent_type])
        
        if target_count > current_count:
            # Scale up
            for _ in range(target_count - current_count):
                agent = await self.create_agent(agent_type)
                await agent.start()
        elif target_count < current_count:
            # Scale down
            agents_to_remove = current_count - target_count
            for agent in self.agent_pools[agent_type][-agents_to_remove:]:
                await self.remove_agent(agent.agent_id)
        
        self.log_info(f"Scaled {agent_type} agents from {current_count} to {target_count}")
    
    async def start(self) -> None:
        """Start agent manager"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start all agents
        for agent in self.agents.values():
            if not agent.is_running:
                await agent.start()
        
        # Start monitoring
        self._monitor_task = asyncio.create_task(self._monitor_agents())
        
        self.log_info("Agent manager started")
    
    async def stop(self) -> None:
        """Stop agent manager"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop monitoring
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all agents
        for agent in self.agents.values():
            if agent.is_running:
                await agent.stop()
        
        self.log_info("Agent manager stopped")
    
    async def _monitor_agents(self) -> None:
        """Monitor agent health and performance"""
        while self.is_running:
            try:
                for agent_id, agent in self.agents.items():
                    # Get agent status
                    status = agent.get_status()
                    
                    # Update metrics
                    self.agent_metrics[agent_id] = {
                        "status": status,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Check for issues
                    if agent.state == AgentState.FAILED:
                        self.log_warning(f"Agent {agent_id} in failed state")
                        # Attempt restart
                        await self._restart_agent(agent)
                    elif agent.state == AgentState.OVERLOADED:
                        self.log_warning(f"Agent {agent_id} overloaded")
                        # Could trigger scaling here
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                self.log_error("Agent monitoring error", error=e)
    
    async def _restart_agent(self, agent: Agent) -> None:
        """Restart a failed agent"""
        try:
            await agent.stop()
            await asyncio.sleep(2)
            await agent.start()
            self.log_info(f"Restarted agent: {agent.agent_id}")
        except Exception as e:
            self.log_error(f"Failed to restart agent {agent.agent_id}", error=e)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent manager metrics"""
        return {
            "total_agents": len(self.agents),
            "agents_by_type": {
                agent_type: len(agents)
                for agent_type, agents in self.agent_pools.items()
            },
            "agents_by_state": self._count_agents_by_state(),
            "agent_metrics": self.agent_metrics
        }
    
    def _count_agents_by_state(self) -> Dict[str, int]:
        """Count agents by state"""
        state_counts = {}
        for agent in self.agents.values():
            state = agent.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        return state_counts
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            "status": "healthy",
            "total_agents": len(self.agents),
            "healthy_agents": 0,
            "unhealthy_agents": 0,
            "agent_health": {}
        }
        
        for agent_id, agent in self.agents.items():
            agent_health = await agent.health_check()
            health["agent_health"][agent_id] = agent_health
            
            if agent_health["status"] == "healthy":
                health["healthy_agents"] += 1
            else:
                health["unhealthy_agents"] += 1
        
        if health["unhealthy_agents"] > 0:
            health["status"] = "degraded"
        
        if health["unhealthy_agents"] == len(self.agents):
            health["status"] = "unhealthy"
        
        return health