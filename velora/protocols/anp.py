"""
Agent Network Protocol (ANP) Implementation

A three-layer system designed to enable large-scale interconnection and 
collaboration among AI agents with identity authentication, dynamic negotiation,
and capability discovery.
"""

import uuid
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
import base64
import random

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import Certificate, CertificateBuilder, Name, NameAttribute
from cryptography.x509.oid import NameOID
import secrets

from velora.core.logging import LoggerMixin
from velora.core.exceptions import ProtocolError, ValidationError, AuthenticationError


class NegotiationPhase(Enum):
    """Negotiation phases"""
    INITIALIZATION = "initialization"
    PROPOSAL = "proposal"
    COUNTER_PROPOSAL = "counter_proposal"
    AGREEMENT = "agreement"
    EXECUTION = "execution"


class ServiceStatus(Enum):
    """Service status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class AgentIdentity:
    """Agent identity information"""
    agent_id: str
    public_key: str
    certificate_chain: List[str] = field(default_factory=list)
    capability_manifest: Dict[str, Any] = field(default_factory=dict)
    trust_anchors: List[str] = field(default_factory=list)
    revocation_status: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Capability:
    """Agent capability definition"""
    capability_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    performance_profile: Dict[str, Any] = field(default_factory=dict)
    security_requirements: Dict[str, Any] = field(default_factory=dict)
    pricing_model: Dict[str, Any] = field(default_factory=dict)
    availability: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustScore:
    """Trust score components"""
    identity_verification: float = 0.0
    capability_attestation: float = 0.0
    performance_history: float = 0.0
    security_compliance: float = 0.0
    community_reputation: float = 0.0
    
    def calculate_weighted_score(self) -> float:
        """Calculate weighted trust score"""
        weights = {
            "identity_verification": 0.3,
            "capability_attestation": 0.25,
            "performance_history": 0.2,
            "security_compliance": 0.15,
            "community_reputation": 0.1
        }
        
        score = (
            self.identity_verification * weights["identity_verification"] +
            self.capability_attestation * weights["capability_attestation"] +
            self.performance_history * weights["performance_history"] +
            self.security_compliance * weights["security_compliance"] +
            self.community_reputation * weights["community_reputation"]
        )
        
        return min(1.0, max(0.0, score))


@dataclass
class ServiceRegistration:
    """Service registration information"""
    registration_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    service_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str = ""
    service_version: str = "1.0.0"
    service_category: str = ""
    service_description: str = ""
    capability_manifest: Dict[str, Any] = field(default_factory=dict)
    api_specification: Dict[str, Any] = field(default_factory=dict)
    pricing_information: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.ACTIVE
    registration_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class NegotiationContext:
    """Negotiation context"""
    negotiation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requester_id: str = ""
    provider_id: str = ""
    phase: NegotiationPhase = NegotiationPhase.INITIALIZATION
    proposals: List[Dict[str, Any]] = field(default_factory=list)
    counter_proposals: List[Dict[str, Any]] = field(default_factory=list)
    agreement: Optional[Dict[str, Any]] = None
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_update: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ANPMessage:
    """ANP message structure"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    layer: int = 1  # 1: Identity, 2: Negotiation, 3: Discovery
    message_type: str = ""
    source_agent_id: str = ""
    destination_agent_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None


class ANP(LoggerMixin):
    """
    Agent Network Protocol implementation
    
    Provides three layers:
    1. Identity & Authentication Layer
    2. Dynamic Negotiation Layer
    3. Capability Discovery Layer
    """
    
    def __init__(self, agent_id: str, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        """
        Initialize ANP protocol handler
        
        Args:
            agent_id: Unique agent identifier
            private_key: Ed25519 private key for identity
        """
        self.agent_id = agent_id
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
        # Layer 1: Identity & Authentication
        self.identity = self._create_identity()
        self.trust_scores: Dict[str, TrustScore] = {}
        self.known_agents: Dict[str, AgentIdentity] = {}
        
        # Layer 2: Dynamic Negotiation
        self.active_negotiations: Dict[str, NegotiationContext] = {}
        self.negotiation_templates: Dict[str, Dict[str, Any]] = {}
        
        # Layer 3: Capability Discovery
        self.service_registry: Dict[str, ServiceRegistration] = {}
        self.capability_index: Dict[str, Set[str]] = {}  # capability -> service_ids
        self.local_capabilities: List[Capability] = []
        
        # Message handlers
        self.message_handlers: Dict[Tuple[int, str], callable] = {}
        
        self.log_info(f"ANP initialized for agent {agent_id}")
    
    def _create_identity(self) -> AgentIdentity:
        """Create agent identity"""
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return AgentIdentity(
            agent_id=self.agent_id,
            public_key=base64.b64encode(public_key_bytes).decode(),
            metadata={
                "name": f"Agent-{self.agent_id[:8]}",
                "version": "1.0.0",
                "created_at": datetime.utcnow().isoformat()
            }
        )
    
    # Layer 1: Identity & Authentication
    
    def authenticate_agent(self, agent_identity: AgentIdentity) -> bool:
        """
        Authenticate an agent
        
        Args:
            agent_identity: Agent identity to authenticate
        
        Returns:
            True if authentication successful
        """
        try:
            # Verify public key format
            public_key_bytes = base64.b64decode(agent_identity.public_key)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Verify certificate chain if provided
            if agent_identity.certificate_chain:
                # In production, would verify full certificate chain
                pass
            
            # Check revocation status
            if agent_identity.revocation_status.get("revoked"):
                self.log_warning(
                    "Agent certificate revoked",
                    agent_id=agent_identity.agent_id
                )
                return False
            
            # Store agent identity
            self.known_agents[agent_identity.agent_id] = agent_identity
            
            # Initialize trust score
            if agent_identity.agent_id not in self.trust_scores:
                self.trust_scores[agent_identity.agent_id] = TrustScore(
                    identity_verification=0.5  # Base score
                )
            
            self.log_info(
                "Agent authenticated",
                agent_id=agent_identity.agent_id
            )
            return True
            
        except Exception as e:
            self.log_error(
                "Authentication failed",
                error=e,
                agent_id=agent_identity.agent_id
            )
            return False
    
    def calculate_trust_score(self, agent_id: str) -> float:
        """
        Calculate trust score for an agent
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Trust score (0.0 to 1.0)
        """
        if agent_id not in self.trust_scores:
            return 0.0
        
        return self.trust_scores[agent_id].calculate_weighted_score()
    
    def update_trust_score(
        self,
        agent_id: str,
        component: str,
        value: float
    ) -> None:
        """
        Update trust score component
        
        Args:
            agent_id: Agent identifier
            component: Trust score component name
            value: New value (0.0 to 1.0)
        """
        if agent_id not in self.trust_scores:
            self.trust_scores[agent_id] = TrustScore()
        
        trust_score = self.trust_scores[agent_id]
        if hasattr(trust_score, component):
            setattr(trust_score, component, max(0.0, min(1.0, value)))
            
            self.log_debug(
                "Trust score updated",
                agent_id=agent_id,
                component=component,
                value=value,
                total_score=trust_score.calculate_weighted_score()
            )
    
    # Layer 2: Dynamic Negotiation
    
    async def initiate_negotiation(
        self,
        provider_id: str,
        service_requirements: Dict[str, Any]
    ) -> str:
        """
        Initiate service negotiation
        
        Args:
            provider_id: Service provider agent ID
            service_requirements: Required service specifications
        
        Returns:
            Negotiation ID
        """
        negotiation = NegotiationContext(
            requester_id=self.agent_id,
            provider_id=provider_id,
            phase=NegotiationPhase.INITIALIZATION
        )
        
        self.active_negotiations[negotiation.negotiation_id] = negotiation
        
        # Send negotiation request
        message = ANPMessage(
            layer=2,
            message_type="negotiation_request",
            source_agent_id=self.agent_id,
            destination_agent_id=provider_id,
            payload={
                "negotiation_id": negotiation.negotiation_id,
                "requirements": service_requirements
            }
        )
        
        await self.send_message(message)
        
        self.log_info(
            "Negotiation initiated",
            negotiation_id=negotiation.negotiation_id,
            provider_id=provider_id
        )
        
        return negotiation.negotiation_id
    
    async def submit_proposal(
        self,
        negotiation_id: str,
        proposal: Dict[str, Any]
    ) -> None:
        """
        Submit a proposal in negotiation
        
        Args:
            negotiation_id: Negotiation identifier
            proposal: Service proposal
        """
        if negotiation_id not in self.active_negotiations:
            raise ProtocolError(
                f"Unknown negotiation: {negotiation_id}",
                "ANP"
            )
        
        negotiation = self.active_negotiations[negotiation_id]
        negotiation.proposals.append(proposal)
        negotiation.phase = NegotiationPhase.PROPOSAL
        negotiation.last_update = datetime.utcnow().isoformat()
        
        # Send proposal message
        destination = (
            negotiation.requester_id
            if negotiation.provider_id == self.agent_id
            else negotiation.provider_id
        )
        
        message = ANPMessage(
            layer=2,
            message_type="negotiation_proposal",
            source_agent_id=self.agent_id,
            destination_agent_id=destination,
            payload={
                "negotiation_id": negotiation_id,
                "proposal": proposal
            }
        )
        
        await self.send_message(message)
        
        self.log_info(
            "Proposal submitted",
            negotiation_id=negotiation_id
        )
    
    async def finalize_agreement(
        self,
        negotiation_id: str,
        agreement: Dict[str, Any]
    ) -> None:
        """
        Finalize negotiation agreement
        
        Args:
            negotiation_id: Negotiation identifier
            agreement: Final agreement terms
        """
        if negotiation_id not in self.active_negotiations:
            raise ProtocolError(
                f"Unknown negotiation: {negotiation_id}",
                "ANP"
            )
        
        negotiation = self.active_negotiations[negotiation_id]
        negotiation.agreement = agreement
        negotiation.phase = NegotiationPhase.AGREEMENT
        negotiation.last_update = datetime.utcnow().isoformat()
        
        # Send agreement message
        destination = (
            negotiation.requester_id
            if negotiation.provider_id == self.agent_id
            else negotiation.provider_id
        )
        
        message = ANPMessage(
            layer=2,
            message_type="negotiation_agreement",
            source_agent_id=self.agent_id,
            destination_agent_id=destination,
            payload={
                "negotiation_id": negotiation_id,
                "agreement": agreement
            }
        )
        
        await self.send_message(message)
        
        self.log_info(
            "Agreement finalized",
            negotiation_id=negotiation_id
        )
    
    # Layer 3: Capability Discovery
    
    def register_service(self, service: ServiceRegistration) -> str:
        """
        Register a service in the registry
        
        Args:
            service: Service registration information
        
        Returns:
            Registration ID
        """
        service.agent_id = self.agent_id
        self.service_registry[service.service_id] = service
        
        # Index capabilities
        for capability in service.capability_manifest.get("capabilities", []):
            capability_name = capability.get("name", "")
            if capability_name:
                if capability_name not in self.capability_index:
                    self.capability_index[capability_name] = set()
                self.capability_index[capability_name].add(service.service_id)
        
        self.log_info(
            "Service registered",
            service_id=service.service_id,
            service_name=service.service_name
        )
        
        return service.registration_id
    
    def discover_services(
        self,
        capability_requirements: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ServiceRegistration]:
        """
        Discover services by capability
        
        Args:
            capability_requirements: Required capabilities
            filters: Additional filters
        
        Returns:
            List of matching services
        """
        matching_services = []
        
        # Find services with required capabilities
        service_ids = set()
        for capability in capability_requirements:
            if capability in self.capability_index:
                if not service_ids:
                    service_ids = self.capability_index[capability].copy()
                else:
                    service_ids &= self.capability_index[capability]
        
        # Apply filters and collect services
        for service_id in service_ids:
            service = self.service_registry.get(service_id)
            if service and service.status == ServiceStatus.ACTIVE:
                if self._apply_service_filters(service, filters):
                    matching_services.append(service)
        
        self.log_debug(
            "Services discovered",
            requirements=capability_requirements,
            found=len(matching_services)
        )
        
        return matching_services
    
    def _apply_service_filters(
        self,
        service: ServiceRegistration,
        filters: Optional[Dict[str, Any]]
    ) -> bool:
        """Apply filters to service"""
        if not filters:
            return True
        
        # Apply category filter
        if "category" in filters:
            if service.service_category != filters["category"]:
                return False
        
        # Apply version filter
        if "min_version" in filters:
            if service.service_version < filters["min_version"]:
                return False
        
        # Apply trust score filter
        if "min_trust_score" in filters:
            trust_score = self.calculate_trust_score(service.agent_id)
            if trust_score < filters["min_trust_score"]:
                return False
        
        return True
    
    def update_service_status(
        self,
        service_id: str,
        status: ServiceStatus
    ) -> None:
        """
        Update service status
        
        Args:
            service_id: Service identifier
            status: New status
        """
        if service_id in self.service_registry:
            self.service_registry[service_id].status = status
            self.service_registry[service_id].last_heartbeat = datetime.utcnow().isoformat()
            
            self.log_debug(
                "Service status updated",
                service_id=service_id,
                status=status.value
            )
    
    def register_capability(self, capability: Capability) -> None:
        """
        Register a local capability
        
        Args:
            capability: Capability definition
        """
        self.local_capabilities.append(capability)
        
        # Update identity capability manifest
        self.identity.capability_manifest[capability.capability_id] = asdict(capability)
        
        self.log_info(
            "Capability registered",
            capability_id=capability.capability_id,
            name=capability.name
        )
    
    # Message handling
    
    async def send_message(self, message: ANPMessage) -> None:
        """
        Send ANP message
        
        Args:
            message: Message to send
        """
        # Sign message
        self._sign_message(message)
        
        # In production, would send via network
        self.log_debug(
            "Sending ANP message",
            message_id=message.message_id,
            layer=message.layer,
            type=message.message_type,
            destination=message.destination_agent_id
        )
    
    def _sign_message(self, message: ANPMessage) -> None:
        """Sign message with private key"""
        message_data = json.dumps({
            "message_id": message.message_id,
            "timestamp": message.timestamp,
            "layer": message.layer,
            "message_type": message.message_type,
            "source_agent_id": message.source_agent_id,
            "destination_agent_id": message.destination_agent_id,
            "payload": message.payload
        }, sort_keys=True)
        
        signature = self.private_key.sign(message_data.encode())
        message.signature = base64.b64encode(signature).decode()
    
    async def receive_message(self, message: ANPMessage) -> Optional[ANPMessage]:
        """
        Process received ANP message
        
        Args:
            message: Received message
        
        Returns:
            Response message if applicable
        """
        # Verify signature
        if not self._verify_message(message):
            self.log_warning(
                "Invalid message signature",
                message_id=message.message_id,
                source=message.source_agent_id
            )
            return None
        
        # Route to appropriate handler
        handler_key = (message.layer, message.message_type)
        handler = self.message_handlers.get(handler_key)
        
        if handler:
            try:
                response = await handler(message)
                return response
            except Exception as e:
                self.log_error(
                    "Message handler error",
                    error=e,
                    layer=message.layer,
                    type=message.message_type
                )
                return None
        else:
            self.log_warning(
                "No handler for message",
                layer=message.layer,
                type=message.message_type
            )
            return None
    
    def _verify_message(self, message: ANPMessage) -> bool:
        """Verify message signature"""
        if not message.signature:
            return False
        
        # Get sender's public key
        if message.source_agent_id not in self.known_agents:
            return False
        
        agent = self.known_agents[message.source_agent_id]
        
        try:
            public_key_bytes = base64.b64decode(agent.public_key)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            message_data = json.dumps({
                "message_id": message.message_id,
                "timestamp": message.timestamp,
                "layer": message.layer,
                "message_type": message.message_type,
                "source_agent_id": message.source_agent_id,
                "destination_agent_id": message.destination_agent_id,
                "payload": message.payload
            }, sort_keys=True)
            
            signature = base64.b64decode(message.signature)
            public_key.verify(signature, message_data.encode())
            
            return True
            
        except Exception:
            return False
    
    def register_handler(
        self,
        layer: int,
        message_type: str,
        handler: callable
    ) -> None:
        """
        Register message handler
        
        Args:
            layer: Protocol layer (1-3)
            message_type: Message type
            handler: Async handler function
        """
        self.message_handlers[(layer, message_type)] = handler
        self.log_debug(
            f"Registered handler for layer {layer}, type {message_type}"
        )