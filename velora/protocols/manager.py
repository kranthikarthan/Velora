"""
Protocol Manager for coordinating UAICP and ANP protocols
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from velora.core.config import Settings
from velora.core.logging import LoggerMixin
from velora.core.exceptions import ProtocolError
from velora.protocols.uaicp import UAICP, UAICPMessage, MessageType
from velora.protocols.anp import ANP, ANPMessage, AgentIdentity, ServiceRegistration


class ProtocolManager(LoggerMixin):
    """
    Manages and coordinates protocol handlers
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize protocol manager
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.agent_id = f"velora-{settings.environment}"
        
        # Initialize protocol handlers
        self.uaicp = UAICP(self.agent_id)
        self.anp = ANP(self.agent_id)
        
        # Protocol routing
        self.protocol_routes: Dict[str, Any] = {}
        
        # Active connections
        self.connections: Dict[str, Any] = {}
        
        self.is_running = False
        
        self.log_info("Protocol manager initialized", agent_id=self.agent_id)
    
    async def initialize(self) -> None:
        """Initialize protocol handlers"""
        try:
            # Register UAICP message handlers
            self._register_uaicp_handlers()
            
            # Register ANP message handlers
            self._register_anp_handlers()
            
            # Register local agent identity
            self.anp.authenticate_agent(self.anp.identity)
            
            self.log_info("Protocol handlers initialized")
            
        except Exception as e:
            self.log_error("Failed to initialize protocols", error=e)
            raise ProtocolError(f"Protocol initialization failed: {str(e)}", "MANAGER")
    
    def _register_uaicp_handlers(self) -> None:
        """Register UAICP message handlers"""
        # Discovery handlers
        self.uaicp.register_handler(
            MessageType.CAPABILITY_DISCOVERY_REQUEST,
            self._handle_capability_discovery
        )
        self.uaicp.register_handler(
            MessageType.CAPABILITY_ANNOUNCEMENT,
            self._handle_capability_announcement
        )
        
        # Negotiation handlers
        self.uaicp.register_handler(
            MessageType.NEGOTIATION_PROPOSAL,
            self._handle_negotiation_proposal
        )
        self.uaicp.register_handler(
            MessageType.NEGOTIATION_RESPONSE,
            self._handle_negotiation_response
        )
        
        # Execution handlers
        self.uaicp.register_handler(
            MessageType.TASK_EXECUTION_REQUEST,
            self._handle_task_execution_request
        )
        self.uaicp.register_handler(
            MessageType.TASK_EXECUTION_RESPONSE,
            self._handle_task_execution_response
        )
        
        # Status handlers
        self.uaicp.register_handler(
            MessageType.STATUS_UPDATE,
            self._handle_status_update
        )
        self.uaicp.register_handler(
            MessageType.HEARTBEAT,
            self._handle_heartbeat
        )
    
    def _register_anp_handlers(self) -> None:
        """Register ANP message handlers"""
        # Layer 1: Identity handlers
        self.anp.register_handler(1, "identity_request", self._handle_identity_request)
        self.anp.register_handler(1, "identity_response", self._handle_identity_response)
        self.anp.register_handler(1, "trust_update", self._handle_trust_update)
        
        # Layer 2: Negotiation handlers
        self.anp.register_handler(2, "negotiation_request", self._handle_anp_negotiation_request)
        self.anp.register_handler(2, "negotiation_proposal", self._handle_anp_negotiation_proposal)
        self.anp.register_handler(2, "negotiation_agreement", self._handle_anp_negotiation_agreement)
        
        # Layer 3: Discovery handlers
        self.anp.register_handler(3, "service_announcement", self._handle_service_announcement)
        self.anp.register_handler(3, "service_query", self._handle_service_query)
        self.anp.register_handler(3, "service_update", self._handle_service_update)
    
    async def start(self) -> None:
        """Start protocol manager"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start heartbeat task
        asyncio.create_task(self._heartbeat_loop())
        
        # Start service announcement task
        asyncio.create_task(self._service_announcement_loop())
        
        self.log_info("Protocol manager started")
    
    async def stop(self) -> None:
        """Stop protocol manager"""
        self.is_running = False
        
        # Close all connections
        for conn_id in list(self.connections.keys()):
            await self.close_connection(conn_id)
        
        self.log_info("Protocol manager stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats"""
        while self.is_running:
            try:
                # Send UAICP heartbeat
                heartbeat = self.uaicp.create_message(
                    MessageType.HEARTBEAT,
                    "broadcast",
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "active",
                        "agent_id": self.agent_id
                    }
                )
                await self.uaicp.send_message(heartbeat)
                
                # Update ANP service heartbeats
                for service_id in self.anp.service_registry:
                    self.anp.update_service_status(
                        service_id,
                        self.anp.service_registry[service_id].status
                    )
                
            except Exception as e:
                self.log_error("Heartbeat error", error=e)
            
            await asyncio.sleep(self.settings.agent_heartbeat_interval)
    
    async def _service_announcement_loop(self) -> None:
        """Periodically announce available services"""
        while self.is_running:
            try:
                # Announce local services via UAICP
                for service in self.anp.service_registry.values():
                    if service.agent_id == self.agent_id:
                        announcement = self.uaicp.create_message(
                            MessageType.CAPABILITY_ANNOUNCEMENT,
                            "broadcast",
                            {
                                "service_id": service.service_id,
                                "service_name": service.service_name,
                                "capabilities": service.capability_manifest,
                                "status": service.status.value
                            }
                        )
                        await self.uaicp.send_message(announcement)
                
            except Exception as e:
                self.log_error("Service announcement error", error=e)
            
            await asyncio.sleep(60)  # Announce every minute
    
    # UAICP Handlers
    
    async def _handle_capability_discovery(self, message: UAICPMessage) -> Optional[UAICPMessage]:
        """Handle capability discovery request"""
        self.log_debug("Handling capability discovery", message_id=message.message_id)
        
        # Extract requirements
        requirements = message.payload.get("requested_capabilities", [])
        
        # Find matching services
        matching_services = []
        for req in requirements:
            capability_type = req.get("capability_type", "")
            services = self.anp.discover_services([capability_type])
            matching_services.extend(services)
        
        # Create response
        response_payload = {
            "matching_agents": [
                {
                    "agent_id": service.agent_id,
                    "service_id": service.service_id,
                    "capabilities": service.capability_manifest
                }
                for service in matching_services
            ],
            "total_matches": len(matching_services)
        }
        
        return self.uaicp.create_message(
            MessageType.CAPABILITY_ANNOUNCEMENT,
            message.source_agent.agent_id,
            response_payload
        )
    
    async def _handle_capability_announcement(self, message: UAICPMessage) -> None:
        """Handle capability announcement"""
        self.log_debug("Handling capability announcement", message_id=message.message_id)
        
        # Register announced service
        service = ServiceRegistration(
            agent_id=message.source_agent.agent_id,
            service_id=message.payload.get("service_id", ""),
            service_name=message.payload.get("service_name", ""),
            capability_manifest=message.payload.get("capabilities", {})
        )
        
        self.anp.register_service(service)
    
    async def _handle_negotiation_proposal(self, message: UAICPMessage) -> None:
        """Handle negotiation proposal"""
        self.log_debug("Handling negotiation proposal", message_id=message.message_id)
        
        # Forward to ANP negotiation layer
        negotiation_id = message.payload.get("proposal_id", "")
        proposal = message.payload.get("service_contract", {})
        
        if negotiation_id:
            await self.anp.submit_proposal(negotiation_id, proposal)
    
    async def _handle_negotiation_response(self, message: UAICPMessage) -> None:
        """Handle negotiation response"""
        self.log_debug("Handling negotiation response", message_id=message.message_id)
        
        # Process negotiation response
        status = message.payload.get("status", "")
        if status == "accepted":
            negotiation_id = message.payload.get("proposal_id", "")
            agreement = message.payload.get("accepted_terms", {})
            if negotiation_id:
                await self.anp.finalize_agreement(negotiation_id, agreement)
    
    async def _handle_task_execution_request(self, message: UAICPMessage) -> Optional[UAICPMessage]:
        """Handle task execution request"""
        self.log_debug("Handling task execution request", message_id=message.message_id)
        
        # This would be forwarded to the appropriate agent
        # For now, return a simple acknowledgment
        return self.uaicp.create_message(
            MessageType.ACKNOWLEDGMENT,
            message.source_agent.agent_id,
            {
                "original_message_id": message.message_id,
                "status": "received",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def _handle_task_execution_response(self, message: UAICPMessage) -> None:
        """Handle task execution response"""
        self.log_debug("Handling task execution response", message_id=message.message_id)
        
        # Process execution results
        task_id = message.payload.get("task_id", "")
        status = message.payload.get("status", "")
        
        self.log_info(f"Task {task_id} completed with status: {status}")
    
    async def _handle_status_update(self, message: UAICPMessage) -> None:
        """Handle status update"""
        self.log_debug("Handling status update", message_id=message.message_id)
        
        # Update agent status
        agent_id = message.source_agent.agent_id
        status = message.payload.get("status", "")
        
        # Update trust score based on status
        if status == "online":
            self.anp.update_trust_score(agent_id, "performance_history", 0.8)
    
    async def _handle_heartbeat(self, message: UAICPMessage) -> None:
        """Handle heartbeat message"""
        agent_id = message.source_agent.agent_id
        self.connections[agent_id] = {
            "last_heartbeat": datetime.utcnow(),
            "status": "active"
        }
    
    # ANP Handlers
    
    async def _handle_identity_request(self, message: ANPMessage) -> Optional[ANPMessage]:
        """Handle identity request"""
        # Return our identity
        return ANPMessage(
            layer=1,
            message_type="identity_response",
            source_agent_id=self.agent_id,
            destination_agent_id=message.source_agent_id,
            payload={
                "identity": self.anp.identity.__dict__
            }
        )
    
    async def _handle_identity_response(self, message: ANPMessage) -> None:
        """Handle identity response"""
        identity_data = message.payload.get("identity", {})
        if identity_data:
            identity = AgentIdentity(**identity_data)
            self.anp.authenticate_agent(identity)
    
    async def _handle_trust_update(self, message: ANPMessage) -> None:
        """Handle trust score update"""
        agent_id = message.source_agent_id
        trust_components = message.payload.get("trust_components", {})
        
        for component, value in trust_components.items():
            self.anp.update_trust_score(agent_id, component, value)
    
    async def _handle_anp_negotiation_request(self, message: ANPMessage) -> None:
        """Handle ANP negotiation request"""
        negotiation_id = message.payload.get("negotiation_id", "")
        requirements = message.payload.get("requirements", {})
        
        self.log_info(f"Received negotiation request: {negotiation_id}")
    
    async def _handle_anp_negotiation_proposal(self, message: ANPMessage) -> None:
        """Handle ANP negotiation proposal"""
        negotiation_id = message.payload.get("negotiation_id", "")
        proposal = message.payload.get("proposal", {})
        
        self.log_info(f"Received negotiation proposal: {negotiation_id}")
    
    async def _handle_anp_negotiation_agreement(self, message: ANPMessage) -> None:
        """Handle ANP negotiation agreement"""
        negotiation_id = message.payload.get("negotiation_id", "")
        agreement = message.payload.get("agreement", {})
        
        self.log_info(f"Negotiation agreement reached: {negotiation_id}")
    
    async def _handle_service_announcement(self, message: ANPMessage) -> None:
        """Handle service announcement"""
        service_data = message.payload.get("service", {})
        if service_data:
            service = ServiceRegistration(**service_data)
            self.anp.register_service(service)
    
    async def _handle_service_query(self, message: ANPMessage) -> Optional[ANPMessage]:
        """Handle service query"""
        capabilities = message.payload.get("capabilities", [])
        filters = message.payload.get("filters", {})
        
        services = self.anp.discover_services(capabilities, filters)
        
        return ANPMessage(
            layer=3,
            message_type="service_response",
            source_agent_id=self.agent_id,
            destination_agent_id=message.source_agent_id,
            payload={
                "services": [service.__dict__ for service in services]
            }
        )
    
    async def _handle_service_update(self, message: ANPMessage) -> None:
        """Handle service status update"""
        service_id = message.payload.get("service_id", "")
        status = message.payload.get("status", "")
        
        if service_id and status:
            from velora.protocols.anp import ServiceStatus
            self.anp.update_service_status(service_id, ServiceStatus(status))
    
    # Connection management
    
    async def establish_connection(self, remote_agent_id: str) -> bool:
        """
        Establish connection with remote agent
        
        Args:
            remote_agent_id: Remote agent identifier
        
        Returns:
            True if connection established
        """
        try:
            # Exchange identities via ANP
            identity_request = ANPMessage(
                layer=1,
                message_type="identity_request",
                source_agent_id=self.agent_id,
                destination_agent_id=remote_agent_id
            )
            
            await self.anp.send_message(identity_request)
            
            # Send capability announcement via UAICP
            announcement = self.uaicp.create_message(
                MessageType.CAPABILITY_ANNOUNCEMENT,
                remote_agent_id,
                {
                    "agent_id": self.agent_id,
                    "capabilities": self.anp.identity.capability_manifest
                }
            )
            
            await self.uaicp.send_message(announcement)
            
            self.connections[remote_agent_id] = {
                "established_at": datetime.utcnow(),
                "status": "active"
            }
            
            self.log_info(f"Connection established with {remote_agent_id}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to establish connection with {remote_agent_id}", error=e)
            return False
    
    async def close_connection(self, remote_agent_id: str) -> None:
        """
        Close connection with remote agent
        
        Args:
            remote_agent_id: Remote agent identifier
        """
        if remote_agent_id in self.connections:
            # Send termination message
            termination = self.uaicp.create_message(
                MessageType.TERMINATION,
                remote_agent_id,
                {
                    "reason": "connection_closed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            await self.uaicp.send_message(termination)
            
            del self.connections[remote_agent_id]
            self.log_info(f"Connection closed with {remote_agent_id}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "agent_id": self.agent_id,
            "active_connections": len(self.connections),
            "registered_services": len(self.anp.service_registry),
            "known_agents": len(self.anp.known_agents),
            "active_negotiations": len(self.anp.active_negotiations)
        }