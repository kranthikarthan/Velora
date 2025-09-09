"""
Universal AI Communication Protocol (UAICP) Implementation

A meta-protocol designed to enable seamless communication between AI agents
across different platforms, languages, and domains.
"""

import uuid
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import secrets

from velora.core.logging import LoggerMixin
from velora.core.exceptions import ProtocolError, ValidationError, SecurityError


class MessageType(Enum):
    """UAICP message types"""
    # Discovery messages
    CAPABILITY_DISCOVERY_REQUEST = "capability_discovery_request"
    CAPABILITY_ANNOUNCEMENT = "capability_announcement"
    
    # Negotiation messages
    NEGOTIATION_PROPOSAL = "negotiation_proposal"
    NEGOTIATION_RESPONSE = "negotiation_response"
    
    # Execution messages
    TASK_EXECUTION_REQUEST = "task_execution_request"
    TASK_EXECUTION_RESPONSE = "task_execution_response"
    
    # Status messages
    STATUS_UPDATE = "status_update"
    PERFORMANCE_REPORT = "performance_report"
    ERROR_REPORT = "error_report"
    
    # Control messages
    HEARTBEAT = "heartbeat"
    ACKNOWLEDGMENT = "acknowledgment"
    TERMINATION = "termination"


@dataclass
class AgentInfo:
    """Agent information"""
    agent_id: str
    capability_hash: str
    trust_score: float = 0.0
    public_key: Optional[str] = None


@dataclass
class SecurityInfo:
    """Security information for messages"""
    signature: Optional[str] = None
    encryption: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    nonce: str = field(default_factory=lambda: secrets.token_hex(16))


@dataclass
class RoutingInfo:
    """Routing information for messages"""
    priority: int = 5  # 1-10, higher is more priority
    ttl: int = 30  # Time to live in seconds
    retry_count: int = 0
    max_retries: int = 3
    route_path: List[str] = field(default_factory=list)


@dataclass
class UAICPMessage:
    """UAICP message structure"""
    version: str = "1.0"
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_agent: AgentInfo = None
    destination_agent: AgentInfo = None
    message_type: MessageType = None
    payload: Dict[str, Any] = field(default_factory=dict)
    security: SecurityInfo = field(default_factory=SecurityInfo)
    routing: RoutingInfo = field(default_factory=RoutingInfo)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "version": self.version,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "source_agent": asdict(self.source_agent) if self.source_agent else None,
            "destination_agent": asdict(self.destination_agent) if self.destination_agent else None,
            "message_type": self.message_type.value if self.message_type else None,
            "payload": self.payload,
            "security": asdict(self.security),
            "routing": asdict(self.routing)
        }
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UAICPMessage":
        """Create message from dictionary"""
        msg = cls()
        msg.version = data.get("version", "1.0")
        msg.message_id = data.get("message_id", str(uuid.uuid4()))
        msg.timestamp = data.get("timestamp", datetime.utcnow().isoformat())
        
        if data.get("source_agent"):
            msg.source_agent = AgentInfo(**data["source_agent"])
        if data.get("destination_agent"):
            msg.destination_agent = AgentInfo(**data["destination_agent"])
        
        if data.get("message_type"):
            msg.message_type = MessageType(data["message_type"])
        
        msg.payload = data.get("payload", {})
        
        if data.get("security"):
            msg.security = SecurityInfo(**data["security"])
        if data.get("routing"):
            msg.routing = RoutingInfo(**data["routing"])
        
        return msg
    
    @classmethod
    def from_json(cls, json_str: str) -> "UAICPMessage":
        """Create message from JSON string"""
        return cls.from_dict(json.loads(json_str))


class UAICP(LoggerMixin):
    """
    Universal AI Communication Protocol implementation
    
    Handles message creation, validation, encryption, and routing
    """
    
    def __init__(self, agent_id: str, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        """
        Initialize UAICP protocol handler
        
        Args:
            agent_id: Unique agent identifier
            private_key: Ed25519 private key for signing
        """
        self.agent_id = agent_id
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.capability_hash = self._generate_capability_hash()
        
        # Message handlers
        self.message_handlers: Dict[MessageType, callable] = {}
        
        # Pending messages and responses
        self.pending_messages: Dict[str, UAICPMessage] = {}
        self.response_futures: Dict[str, asyncio.Future] = {}
        
        # Security
        self.trusted_agents: Dict[str, AgentInfo] = {}
        
        self.log_info(f"UAICP initialized for agent {agent_id}")
    
    def _generate_capability_hash(self) -> str:
        """Generate capability hash for the agent"""
        # In production, this would hash actual capabilities
        data = f"{self.agent_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def create_message(
        self,
        message_type: MessageType,
        destination_agent_id: str,
        payload: Dict[str, Any],
        priority: int = 5
    ) -> UAICPMessage:
        """
        Create a new UAICP message
        
        Args:
            message_type: Type of message
            destination_agent_id: Destination agent ID
            payload: Message payload
            priority: Message priority (1-10)
        
        Returns:
            Created UAICP message
        """
        source = AgentInfo(
            agent_id=self.agent_id,
            capability_hash=self.capability_hash,
            trust_score=1.0,
            public_key=self._export_public_key()
        )
        
        destination = AgentInfo(
            agent_id=destination_agent_id,
            capability_hash="",  # Will be filled by destination
            trust_score=self.get_trust_score(destination_agent_id)
        )
        
        routing = RoutingInfo(priority=priority)
        
        message = UAICPMessage(
            source_agent=source,
            destination_agent=destination,
            message_type=message_type,
            payload=payload,
            routing=routing
        )
        
        # Sign the message
        self._sign_message(message)
        
        self.log_debug(
            "Message created",
            message_id=message.message_id,
            message_type=message_type.value,
            destination=destination_agent_id
        )
        
        return message
    
    def _export_public_key(self) -> str:
        """Export public key as base64 string"""
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(public_bytes).decode()
    
    def _import_public_key(self, key_str: str) -> ed25519.Ed25519PublicKey:
        """Import public key from base64 string"""
        key_bytes = base64.b64decode(key_str)
        return ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)
    
    def _sign_message(self, message: UAICPMessage) -> None:
        """Sign a message with private key"""
        # Create message digest
        message_data = json.dumps({
            "message_id": message.message_id,
            "timestamp": message.timestamp,
            "source_agent": message.source_agent.agent_id if message.source_agent else None,
            "destination_agent": message.destination_agent.agent_id if message.destination_agent else None,
            "message_type": message.message_type.value if message.message_type else None,
            "payload": message.payload
        }, sort_keys=True)
        
        # Sign the digest
        signature = self.private_key.sign(message_data.encode())
        message.security.signature = base64.b64encode(signature).decode()
    
    def verify_message(self, message: UAICPMessage) -> bool:
        """
        Verify message signature
        
        Args:
            message: Message to verify
        
        Returns:
            True if signature is valid
        """
        if not message.security.signature or not message.source_agent:
            return False
        
        try:
            # Get public key
            if message.source_agent.public_key:
                public_key = self._import_public_key(message.source_agent.public_key)
            elif message.source_agent.agent_id in self.trusted_agents:
                public_key = self._import_public_key(
                    self.trusted_agents[message.source_agent.agent_id].public_key
                )
            else:
                self.log_warning(
                    "Cannot verify message - no public key",
                    agent_id=message.source_agent.agent_id
                )
                return False
            
            # Create message digest
            message_data = json.dumps({
                "message_id": message.message_id,
                "timestamp": message.timestamp,
                "source_agent": message.source_agent.agent_id,
                "destination_agent": message.destination_agent.agent_id if message.destination_agent else None,
                "message_type": message.message_type.value if message.message_type else None,
                "payload": message.payload
            }, sort_keys=True)
            
            # Verify signature
            signature = base64.b64decode(message.security.signature)
            public_key.verify(signature, message_data.encode())
            
            return True
            
        except Exception as e:
            self.log_warning(
                "Message verification failed",
                error=str(e),
                message_id=message.message_id
            )
            return False
    
    def encrypt_message(
        self,
        message: UAICPMessage,
        recipient_public_key: Union[str, x25519.X25519PublicKey]
    ) -> None:
        """
        Encrypt message payload using X25519 + AES-256-GCM
        
        Args:
            message: Message to encrypt
            recipient_public_key: Recipient's X25519 public key
        """
        # Generate ephemeral key pair
        ephemeral_private = x25519.X25519PrivateKey.generate()
        ephemeral_public = ephemeral_private.public_key()
        
        # Import recipient key if string
        if isinstance(recipient_public_key, str):
            recipient_key_bytes = base64.b64decode(recipient_public_key)
            recipient_public_key = x25519.X25519PublicKey.from_public_bytes(recipient_key_bytes)
        
        # Perform ECDH
        shared_secret = ephemeral_private.exchange(recipient_public_key)
        
        # Derive encryption key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'uaicp-encryption',
            backend=default_backend()
        )
        key = hkdf.derive(shared_secret)
        
        # Encrypt payload
        nonce = secrets.token_bytes(12)
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        payload_bytes = json.dumps(message.payload).encode()
        ciphertext = encryptor.update(payload_bytes) + encryptor.finalize()
        
        # Store encryption info
        message.security.encryption = {
            "algorithm": "X25519-AES256-GCM",
            "ephemeral_public_key": base64.b64encode(
                ephemeral_public.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            ).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "tag": base64.b64encode(encryptor.tag).decode()
        }
        
        # Replace payload with encrypted data
        message.payload = {
            "encrypted": base64.b64encode(ciphertext).decode()
        }
    
    def decrypt_message(
        self,
        message: UAICPMessage,
        private_key: Optional[x25519.X25519PrivateKey] = None
    ) -> None:
        """
        Decrypt message payload
        
        Args:
            message: Message to decrypt
            private_key: X25519 private key (uses default if not provided)
        """
        if not message.security.encryption:
            return
        
        enc = message.security.encryption
        
        # Get ephemeral public key
        ephemeral_public_bytes = base64.b64decode(enc["ephemeral_public_key"])
        ephemeral_public = x25519.X25519PublicKey.from_public_bytes(ephemeral_public_bytes)
        
        # Use provided key or generate one (in production, would use stored key)
        if not private_key:
            # This is a placeholder - in production, would retrieve the actual key
            private_key = x25519.X25519PrivateKey.generate()
        
        # Perform ECDH
        shared_secret = private_key.exchange(ephemeral_public)
        
        # Derive decryption key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'uaicp-encryption',
            backend=default_backend()
        )
        key = hkdf.derive(shared_secret)
        
        # Decrypt payload
        nonce = base64.b64decode(enc["nonce"])
        tag = base64.b64decode(enc["tag"])
        ciphertext = base64.b64decode(message.payload["encrypted"])
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Restore payload
        message.payload = json.loads(plaintext.decode())
    
    async def send_message(
        self,
        message: UAICPMessage,
        timeout: Optional[int] = None
    ) -> Optional[UAICPMessage]:
        """
        Send a message and optionally wait for response
        
        Args:
            message: Message to send
            timeout: Timeout in seconds for response
        
        Returns:
            Response message if timeout is specified, None otherwise
        """
        # Store message
        self.pending_messages[message.message_id] = message
        
        # If timeout specified, create future for response
        if timeout:
            future = asyncio.Future()
            self.response_futures[message.message_id] = future
        
        # Emit message (would be sent via network in production)
        await self._emit_message(message)
        
        # Wait for response if timeout specified
        if timeout:
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                del self.response_futures[message.message_id]
                raise ProtocolError(
                    f"Message timeout after {timeout} seconds",
                    "UAICP",
                    {"message_id": message.message_id}
                )
            finally:
                # Clean up
                if message.message_id in self.pending_messages:
                    del self.pending_messages[message.message_id]
        
        return None
    
    async def _emit_message(self, message: UAICPMessage) -> None:
        """Emit message (placeholder for network send)"""
        self.log_debug(
            "Emitting message",
            message_id=message.message_id,
            destination=message.destination_agent.agent_id if message.destination_agent else "broadcast"
        )
        # In production, this would send via network
    
    async def receive_message(self, message: UAICPMessage) -> Optional[UAICPMessage]:
        """
        Process received message
        
        Args:
            message: Received message
        
        Returns:
            Response message if applicable
        """
        # Verify message
        if not self.verify_message(message):
            self.log_warning(
                "Invalid message signature",
                message_id=message.message_id,
                source=message.source_agent.agent_id if message.source_agent else "unknown"
            )
            return self._create_error_response(message, "Invalid signature")
        
        # Check if this is a response to a pending message
        if message.message_type == MessageType.ACKNOWLEDGMENT:
            original_id = message.payload.get("original_message_id")
            if original_id in self.response_futures:
                self.response_futures[original_id].set_result(message)
                return None
        
        # Process message based on type
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                response = await handler(message)
                return response
            except Exception as e:
                self.log_error(
                    "Message handler error",
                    error=e,
                    message_type=message.message_type.value
                )
                return self._create_error_response(message, str(e))
        else:
            self.log_warning(
                "No handler for message type",
                message_type=message.message_type.value
            )
            return None
    
    def _create_error_response(self, original: UAICPMessage, error: str) -> UAICPMessage:
        """Create error response message"""
        return self.create_message(
            MessageType.ERROR_REPORT,
            original.source_agent.agent_id if original.source_agent else "unknown",
            {
                "original_message_id": original.message_id,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def register_handler(self, message_type: MessageType, handler: callable) -> None:
        """
        Register message handler
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle message
        """
        self.message_handlers[message_type] = handler
        self.log_debug(f"Registered handler for {message_type.value}")
    
    def get_trust_score(self, agent_id: str) -> float:
        """Get trust score for an agent"""
        if agent_id in self.trusted_agents:
            return self.trusted_agents[agent_id].trust_score
        return 0.0
    
    def update_trust_score(self, agent_id: str, score: float) -> None:
        """Update trust score for an agent"""
        if agent_id in self.trusted_agents:
            self.trusted_agents[agent_id].trust_score = max(0.0, min(1.0, score))
    
    def add_trusted_agent(self, agent_info: AgentInfo) -> None:
        """Add agent to trusted list"""
        self.trusted_agents[agent_info.agent_id] = agent_info
        self.log_info(f"Added trusted agent: {agent_info.agent_id}")