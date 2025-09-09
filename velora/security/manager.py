"""
Security Manager - Orchestrates all security components
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from velora.core.config import Settings, get_settings
from velora.core.logging import LoggerMixin
from velora.core.exceptions import SecurityError
from velora.security.auth import (
    AuthenticationManager,
    AuthorizationManager,
    Identity,
    Permission,
    AuthContext
)
from velora.security.encryption import EncryptionEngine, EncryptedData
from velora.security.threat import ThreatDetectionEngine, ThreatEvent


class SecurityManager(LoggerMixin):
    """
    Central security manager for Velora
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize security manager"""
        self.settings = settings or get_settings()
        
        # Initialize components
        self.auth_manager = AuthenticationManager(self.settings)
        self.authz_manager = AuthorizationManager()
        self.encryption_engine = EncryptionEngine()
        self.threat_detector = ThreatDetectionEngine()
        
        # Security policies
        self.policies = self._initialize_policies()
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
        
        self.is_running = False
        
        self.log_info("Security manager initialized")
    
    def _initialize_policies(self) -> Dict[str, Any]:
        """Initialize security policies"""
        return {
            "password_policy": {
                "min_length": 12,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special": True,
                "max_age_days": 90
            },
            "session_policy": {
                "max_duration_minutes": 480,  # 8 hours
                "idle_timeout_minutes": 30,
                "max_concurrent_sessions": 3
            },
            "encryption_policy": {
                "algorithm": "AES-256-GCM",
                "key_rotation_days": 30,
                "require_encryption_at_rest": True,
                "require_encryption_in_transit": True
            },
            "access_control": {
                "default_deny": True,
                "require_mfa_for_admin": True,
                "ip_whitelist_enabled": False,
                "ip_whitelist": []
            }
        }
    
    async def initialize(self) -> None:
        """Initialize security manager"""
        try:
            # Create default identities
            self._create_default_identities()
            
            # Start threat detection
            await self.threat_detector.start()
            
            self.is_running = True
            
            self.log_info("Security manager initialized successfully")
            
        except Exception as e:
            self.log_error(f"Failed to initialize security manager: {e}")
            raise SecurityError(f"Security initialization failed: {str(e)}")
    
    def _create_default_identities(self) -> None:
        """Create default system identities"""
        # Admin identity
        self.auth_manager.register_identity(
            identity_id="admin",
            identity_type="user",
            name="System Administrator",
            password="changeme123!",  # Should be changed on first login
            permissions={
                Permission.SYSTEM_ADMIN,
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_MONITOR
            }
        )
        
        # Default agent identity
        agent_keypair = self.encryption_engine.generate_signing_keypair()
        public_key_hex = agent_keypair.public_key.public_bytes_raw().hex()
        
        self.auth_manager.register_identity(
            identity_id="default-agent",
            identity_type="agent",
            name="Default Agent",
            public_key=public_key_hex,
            permissions={
                Permission.TASK_SUBMIT,
                Permission.TASK_READ,
                Permission.PROTOCOL_SEND,
                Permission.PROTOCOL_RECEIVE,
                Permission.SERVICE_REGISTER,
                Permission.SERVICE_DISCOVER
            }
        )
    
    async def authenticate(
        self,
        credentials: Dict[str, Any]
    ) -> AuthContext:
        """
        Authenticate a user or agent
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            Authentication context
        """
        auth_type = credentials.get("type", "password")
        
        # Check for blocked IP
        source_ip = credentials.get("ip")
        if source_ip and self.threat_detector.is_ip_blocked(source_ip):
            self._audit_log("authentication", "blocked", {
                "ip": source_ip,
                "reason": "IP blocked"
            })
            raise SecurityError("Access denied")
        
        try:
            if auth_type == "password":
                # Password authentication
                context = self.auth_manager.authenticate_password(
                    credentials["identity_id"],
                    credentials["password"]
                )
            elif auth_type == "key":
                # Public key authentication
                context = self.auth_manager.authenticate_key(
                    credentials["identity_id"],
                    credentials["signature"],
                    credentials["message"]
                )
            elif auth_type == "token":
                # Token authentication
                identity = self.auth_manager.verify_token(credentials["token"])
                context = AuthContext(
                    identity=identity,
                    authenticated_at=datetime.utcnow()
                )
            else:
                raise ValueError(f"Unsupported authentication type: {auth_type}")
            
            # Update context with additional info
            context.ip_address = source_ip
            context.user_agent = credentials.get("user_agent")
            
            # Audit successful authentication
            self._audit_log("authentication", "success", {
                "identity_id": context.identity.id,
                "auth_type": auth_type,
                "ip": source_ip
            })
            
            return context
            
        except Exception as e:
            # Track failed authentication
            if source_ip:
                threat = self.threat_detector.track_failed_authentication(
                    credentials.get("identity_id", "unknown"),
                    source_ip
                )
                if threat:
                    await self.threat_detector._handle_threat(threat)
            
            # Audit failed authentication
            self._audit_log("authentication", "failed", {
                "identity_id": credentials.get("identity_id"),
                "auth_type": auth_type,
                "ip": source_ip,
                "error": str(e)
            })
            
            raise SecurityError(f"Authentication failed: {str(e)}")
    
    def authorize(
        self,
        identity: Identity,
        permission: Permission,
        resource: Optional[str] = None
    ) -> bool:
        """
        Check authorization for an action
        
        Args:
            identity: Identity to check
            permission: Required permission
            resource: Optional resource identifier
        
        Returns:
            True if authorized
        """
        authorized = self.authz_manager.check_permission(
            identity,
            permission,
            resource
        )
        
        # Audit authorization check
        self._audit_log("authorization", "check", {
            "identity_id": identity.id,
            "permission": permission.value,
            "resource": resource,
            "result": authorized
        })
        
        return authorized
    
    def require_permission(
        self,
        identity: Identity,
        permission: Permission,
        resource: Optional[str] = None
    ) -> None:
        """
        Require permission or raise exception
        
        Args:
            identity: Identity to check
            permission: Required permission
            resource: Optional resource identifier
        """
        self.authz_manager.require_permission(identity, permission, resource)
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """
        Analyze request for security threats
        
        Args:
            request_data: Request information
        
        Returns:
            ThreatEvent if threat detected
        """
        threat = await self.threat_detector.analyze_request(request_data)
        
        if threat:
            # Audit threat detection
            self._audit_log("threat_detection", "threat_detected", {
                "threat_id": threat.event_id,
                "threat_type": threat.threat_type.value,
                "threat_level": threat.threat_level.name,
                "source_ip": threat.source_ip
            })
        
        return threat
    
    def encrypt_data(
        self,
        data: bytes,
        classification: str = "confidential"
    ) -> EncryptedData:
        """
        Encrypt data based on classification
        
        Args:
            data: Data to encrypt
            classification: Data classification level
        
        Returns:
            Encrypted data
        """
        # Select encryption based on classification
        if classification == "top_secret":
            # Use asymmetric encryption for highest security
            system_keypair = self.encryption_engine.key_pairs.get("system_encryption")
            if system_keypair:
                encrypted = self.encryption_engine.encrypt_asymmetric(
                    data,
                    system_keypair.public_key,
                    system_keypair.private_key
                )
            else:
                encrypted = self.encryption_engine.encrypt_symmetric(data)
        else:
            # Use symmetric encryption for standard data
            encrypted = self.encryption_engine.encrypt_symmetric(data)
        
        # Add metadata
        encrypted.metadata = {
            "classification": classification,
            "encrypted_at": datetime.utcnow().isoformat()
        }
        
        # Audit encryption
        self._audit_log("encryption", "data_encrypted", {
            "classification": classification,
            "algorithm": encrypted.algorithm,
            "size": len(data)
        })
        
        return encrypted
    
    def decrypt_data(
        self,
        encrypted_data: EncryptedData
    ) -> bytes:
        """
        Decrypt data
        
        Args:
            encrypted_data: Encrypted data container
        
        Returns:
            Decrypted data
        """
        # Audit decryption attempt
        self._audit_log("encryption", "data_decrypted", {
            "algorithm": encrypted_data.algorithm,
            "key_id": encrypted_data.key_id
        })
        
        return self.encryption_engine.decrypt_symmetric(encrypted_data)
    
    def validate_password(self, password: str) -> bool:
        """
        Validate password against policy
        
        Args:
            password: Password to validate
        
        Returns:
            True if password meets policy
        """
        policy = self.policies["password_policy"]
        
        if len(password) < policy["min_length"]:
            return False
        
        if policy["require_uppercase"] and not any(c.isupper() for c in password):
            return False
        
        if policy["require_lowercase"] and not any(c.islower() for c in password):
            return False
        
        if policy["require_numbers"] and not any(c.isdigit() for c in password):
            return False
        
        if policy["require_special"] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False
        
        return True
    
    def _audit_log(
        self,
        category: str,
        action: str,
        details: Dict[str, Any]
    ) -> None:
        """Add entry to audit log"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "action": action,
            "details": details
        }
        
        self.audit_log.append(entry)
        
        # Keep only last 10000 entries
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-10000:]
        
        # Log significant events
        if category in ["threat_detection", "authentication"]:
            self.log_info(f"Audit: {category}/{action}", **details)
    
    def get_audit_log(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries
        
        Args:
            category: Optional category filter
            limit: Maximum number of entries
        
        Returns:
            List of audit log entries
        """
        if category:
            filtered = [e for e in self.audit_log if e["category"] == category]
        else:
            filtered = self.audit_log
        
        return filtered[-limit:]
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security system status"""
        return {
            "is_running": self.is_running,
            "components": {
                "authentication": "active",
                "authorization": "active",
                "encryption": "active",
                "threat_detection": "active" if self.threat_detector.is_running else "inactive"
            },
            "statistics": {
                "active_sessions": len(self.auth_manager.sessions),
                "registered_identities": len(self.auth_manager.identities),
                "blocked_ips": len(self.threat_detector.blocked_ips),
                "active_threats": len(self.threat_detector.active_threats)
            },
            "threat_report": self.threat_detector.get_threat_report(),
            "policies": {
                name: {
                    k: v for k, v in policy.items()
                    if not isinstance(v, (list, dict))
                }
                for name, policy in self.policies.items()
            }
        }
    
    async def rotate_keys(self) -> None:
        """Rotate all cryptographic keys"""
        self.log_info("Starting key rotation")
        
        # Rotate encryption keys
        self.encryption_engine.rotate_keys()
        
        # Audit key rotation
        self._audit_log("key_management", "keys_rotated", {
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self.log_info("Key rotation completed")
    
    async def stop(self) -> None:
        """Stop security manager"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop threat detector
        await self.threat_detector.stop()
        
        self.log_info("Security manager stopped")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health = {
            "status": "healthy",
            "components": {}
        }
        
        # Check authentication
        health["components"]["authentication"] = {
            "status": "healthy",
            "active_sessions": len(self.auth_manager.sessions)
        }
        
        # Check encryption
        health["components"]["encryption"] = {
            "status": "healthy",
            "keys_available": len(self.encryption_engine.key_pairs) > 0
        }
        
        # Check threat detection
        health["components"]["threat_detection"] = {
            "status": "healthy" if self.threat_detector.is_running else "unhealthy",
            "active_threats": len(self.threat_detector.active_threats)
        }
        
        # Overall status
        if any(c["status"] == "unhealthy" for c in health["components"].values()):
            health["status"] = "degraded"
        
        return health