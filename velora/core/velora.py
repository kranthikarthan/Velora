"""
Main Velora Core class that orchestrates the entire system
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from velora.core.config import Settings, get_settings
from velora.core.logging import LoggerMixin, setup_logging
from velora.core.exceptions import VeloraException, ConfigurationError


class VeloraCore(LoggerMixin):
    """
    Main Velora system orchestrator
    
    This class manages the lifecycle of all Velora components including:
    - Protocol handlers (UAICP, ANP)
    - Agent management
    - Data layer
    - Security framework
    - API gateway
    - Legacy integrations
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize Velora Core
        
        Args:
            settings: Optional settings override
        """
        self.settings = settings or get_settings()
        self.instance_id = str(uuid.uuid4())
        self.start_time = datetime.utcnow()
        self.is_running = False
        
        # Component references (will be initialized in setup)
        self.protocol_manager = None
        self.agent_manager = None
        self.data_manager = None
        self.security_manager = None
        self.api_gateway = None
        self.legacy_bridge = None
        self.semantic_engine = None
        self.monitoring = None
        
        # Setup logging
        setup_logging(self.settings.log_level)
        
        self.log_info(
            "Velora Core initialized",
            instance_id=self.instance_id,
            environment=self.settings.environment
        )
    
    async def setup(self) -> None:
        """
        Set up all Velora components
        """
        try:
            self.log_info("Starting Velora setup")
            
            # Initialize protocol manager
            await self._setup_protocols()
            
            # Initialize agent manager
            await self._setup_agents()
            
            # Initialize data layer
            await self._setup_data_layer()
            
            # Initialize security framework
            await self._setup_security()
            
            # Initialize API gateway
            await self._setup_api_gateway()
            
            # Initialize legacy bridge
            await self._setup_legacy_bridge()
            
            # Initialize semantic engine
            await self._setup_semantic_engine()
            
            # Initialize monitoring
            await self._setup_monitoring()
            
            self.log_info("Velora setup completed successfully")
            
        except Exception as e:
            self.log_error("Failed to setup Velora", error=e)
            raise ConfigurationError(f"Setup failed: {str(e)}")
    
    async def _setup_protocols(self) -> None:
        """Initialize protocol handlers"""
        from velora.protocols import ProtocolManager
        
        self.log_info("Setting up protocol manager")
        self.protocol_manager = ProtocolManager(self.settings)
        await self.protocol_manager.initialize()
    
    async def _setup_agents(self) -> None:
        """Initialize agent management system"""
        from velora.agents import AgentManager
        
        self.log_info("Setting up agent manager")
        self.agent_manager = AgentManager(self.settings, self.protocol_manager)
        await self.agent_manager.initialize()
    
    async def _setup_data_layer(self) -> None:
        """Initialize data layer"""
        from velora.data import DataManager
        
        self.log_info("Setting up data layer")
        self.data_manager = DataManager(self.settings)
        await self.data_manager.initialize()
    
    async def _setup_security(self) -> None:
        """Initialize security framework"""
        from velora.security import SecurityManager
        
        self.log_info("Setting up security framework")
        self.security_manager = SecurityManager(self.settings)
        await self.security_manager.initialize()
    
    async def _setup_api_gateway(self) -> None:
        """Initialize API gateway"""
        from velora.api import APIGateway
        
        self.log_info("Setting up API gateway")
        self.api_gateway = APIGateway(
            self.settings,
            self.protocol_manager,
            self.agent_manager,
            self.security_manager
        )
        await self.api_gateway.initialize()
    
    async def _setup_legacy_bridge(self) -> None:
        """Initialize legacy system bridge"""
        from velora.legacy import LegacyBridge
        
        self.log_info("Setting up legacy bridge")
        self.legacy_bridge = LegacyBridge(self.settings, self.data_manager)
        await self.legacy_bridge.initialize()
    
    async def _setup_semantic_engine(self) -> None:
        """Initialize semantic knowledge engine"""
        from velora.semantics import SemanticEngine
        
        self.log_info("Setting up semantic engine")
        self.semantic_engine = SemanticEngine(self.settings, self.data_manager)
        await self.semantic_engine.initialize()
    
    async def _setup_monitoring(self) -> None:
        """Initialize monitoring and observability"""
        from velora.monitoring import MonitoringSystem
        
        self.log_info("Setting up monitoring system")
        self.monitoring = MonitoringSystem(self.settings)
        await self.monitoring.initialize()
    
    async def start(self) -> None:
        """
        Start the Velora system
        """
        if self.is_running:
            self.log_warning("Velora is already running")
            return
        
        try:
            self.log_info("Starting Velora system")
            
            # Setup components if not already done
            if not self.protocol_manager:
                await self.setup()
            
            # Start all components
            await self.protocol_manager.start()
            await self.agent_manager.start()
            await self.data_manager.start()
            await self.security_manager.start()
            await self.api_gateway.start()
            await self.legacy_bridge.start()
            await self.semantic_engine.start()
            await self.monitoring.start()
            
            self.is_running = True
            self.log_info(
                "Velora system started successfully",
                instance_id=self.instance_id,
                uptime_seconds=self.get_uptime()
            )
            
        except Exception as e:
            self.log_error("Failed to start Velora", error=e)
            await self.stop()
            raise VeloraException(f"Start failed: {str(e)}")
    
    async def stop(self) -> None:
        """
        Stop the Velora system
        """
        if not self.is_running:
            self.log_warning("Velora is not running")
            return
        
        try:
            self.log_info("Stopping Velora system")
            
            # Stop all components in reverse order
            if self.monitoring:
                await self.monitoring.stop()
            if self.semantic_engine:
                await self.semantic_engine.stop()
            if self.legacy_bridge:
                await self.legacy_bridge.stop()
            if self.api_gateway:
                await self.api_gateway.stop()
            if self.security_manager:
                await self.security_manager.stop()
            if self.data_manager:
                await self.data_manager.stop()
            if self.agent_manager:
                await self.agent_manager.stop()
            if self.protocol_manager:
                await self.protocol_manager.stop()
            
            self.is_running = False
            self.log_info(
                "Velora system stopped",
                instance_id=self.instance_id,
                total_uptime_seconds=self.get_uptime()
            )
            
        except Exception as e:
            self.log_error("Error during shutdown", error=e)
            raise VeloraException(f"Shutdown error: {str(e)}")
    
    async def restart(self) -> None:
        """
        Restart the Velora system
        """
        self.log_info("Restarting Velora system")
        await self.stop()
        await asyncio.sleep(2)  # Brief pause before restart
        await self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current system status
        
        Returns:
            Dictionary containing system status information
        """
        return {
            "instance_id": self.instance_id,
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": self.get_uptime(),
            "environment": self.settings.environment,
            "version": self.settings.app_version,
            "components": {
                "protocol_manager": self._get_component_status(self.protocol_manager),
                "agent_manager": self._get_component_status(self.agent_manager),
                "data_manager": self._get_component_status(self.data_manager),
                "security_manager": self._get_component_status(self.security_manager),
                "api_gateway": self._get_component_status(self.api_gateway),
                "legacy_bridge": self._get_component_status(self.legacy_bridge),
                "semantic_engine": self._get_component_status(self.semantic_engine),
                "monitoring": self._get_component_status(self.monitoring),
            }
        }
    
    def _get_component_status(self, component) -> str:
        """Get status of a component"""
        if component is None:
            return "not_initialized"
        elif hasattr(component, "is_running"):
            return "running" if component.is_running else "stopped"
        else:
            return "initialized"
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds"""
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components
        
        Returns:
            Health check results
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "instance_id": self.instance_id,
            "uptime_seconds": self.get_uptime(),
            "checks": {}
        }
        
        # Check each component
        components = [
            ("protocol_manager", self.protocol_manager),
            ("agent_manager", self.agent_manager),
            ("data_manager", self.data_manager),
            ("security_manager", self.security_manager),
            ("api_gateway", self.api_gateway),
            ("legacy_bridge", self.legacy_bridge),
            ("semantic_engine", self.semantic_engine),
            ("monitoring", self.monitoring),
        ]
        
        for name, component in components:
            if component and hasattr(component, "health_check"):
                try:
                    component_health = await component.health_check()
                    health["checks"][name] = component_health
                    if component_health.get("status") != "healthy":
                        health["status"] = "degraded"
                except Exception as e:
                    health["checks"][name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
                    health["status"] = "unhealthy"
            else:
                health["checks"][name] = {
                    "status": "unknown" if component else "not_initialized"
                }
        
        return health