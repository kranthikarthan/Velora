"""
Authentication and Authorization modules for Velora
"""

import jwt
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from passlib.context import CryptContext
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519

from velora.core.config import Settings, get_settings
from velora.core.logging import LoggerMixin
from velora.core.exceptions import AuthenticationError, AuthorizationError


class AuthLevel(Enum):
    """Authentication levels"""
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class Permission(Enum):
    """System permissions"""
    # Agent permissions
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"
    
    # Task permissions
    TASK_SUBMIT = "task:submit"
    TASK_READ = "task:read"
    TASK_CANCEL = "task:cancel"
    
    # Protocol permissions
    PROTOCOL_SEND = "protocol:send"
    PROTOCOL_RECEIVE = "protocol:receive"
    PROTOCOL_NEGOTIATE = "protocol:negotiate"
    
    # Service permissions
    SERVICE_REGISTER = "service:register"
    SERVICE_DISCOVER = "service:discover"
    SERVICE_INVOKE = "service:invoke"
    
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_CONFIG = "system:config"


@dataclass
class Identity:
    """Identity information"""
    id: str
    type: str  # user, agent, service
    name: str
    auth_level: AuthLevel
    permissions: Set[Permission] = field(default_factory=set)
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_authenticated: Optional[datetime] = None
    public_key: Optional[str] = None
    trust_score: float = 0.5


@dataclass
class AuthToken:
    """Authentication token"""
    token: str
    identity_id: str
    issued_at: datetime
    expires_at: datetime
    refresh_token: Optional[str] = None
    scopes: List[str] = field(default_factory=list)


@dataclass
class AuthContext:
    """Authentication context"""
    identity: Identity
    token: Optional[AuthToken] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    authenticated_at: Optional[datetime] = None


class AuthenticationManager(LoggerMixin):
    """
    Manages authentication for the system
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize authentication manager"""
        self.settings = settings or get_settings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Identity store
        self.identities: Dict[str, Identity] = {}
        
        # Active sessions
        self.sessions: Dict[str, AuthContext] = {}
        
        # Token blacklist
        self.blacklisted_tokens: Set[str] = set()
        
        # Initialize with system identity
        self._create_system_identity()
        
        self.log_info("Authentication manager initialized")
    
    def _create_system_identity(self) -> None:
        """Create system identity"""
        system_identity = Identity(
            id="system",
            type="system",
            name="Velora System",
            auth_level=AuthLevel.CRITICAL,
            permissions={Permission.SYSTEM_ADMIN}
        )
        self.identities["system"] = system_identity
    
    def register_identity(
        self,
        identity_id: str,
        identity_type: str,
        name: str,
        password: Optional[str] = None,
        public_key: Optional[str] = None,
        permissions: Optional[Set[Permission]] = None
    ) -> Identity:
        """
        Register a new identity
        
        Args:
            identity_id: Unique identifier
            identity_type: Type of identity (user, agent, service)
            name: Display name
            password: Optional password for authentication
            public_key: Optional public key for cryptographic auth
            permissions: Set of permissions
        
        Returns:
            Created identity
        """
        if identity_id in self.identities:
            raise AuthenticationError(f"Identity {identity_id} already exists")
        
        # Determine auth level based on type
        auth_level = AuthLevel.BASIC
        if identity_type == "agent":
            auth_level = AuthLevel.STANDARD
        elif identity_type == "service":
            auth_level = AuthLevel.ELEVATED
        
        # Create identity
        identity = Identity(
            id=identity_id,
            type=identity_type,
            name=name,
            auth_level=auth_level,
            permissions=permissions or set(),
            public_key=public_key
        )
        
        # Store password hash if provided
        if password:
            password_hash = self.pwd_context.hash(password)
            identity.attributes["password_hash"] = password_hash
        
        self.identities[identity_id] = identity
        
        self.log_info(f"Registered identity: {identity_id} (type: {identity_type})")
        return identity
    
    def authenticate_password(
        self,
        identity_id: str,
        password: str
    ) -> AuthContext:
        """
        Authenticate using password
        
        Args:
            identity_id: Identity identifier
            password: Password
        
        Returns:
            Authentication context
        """
        identity = self.identities.get(identity_id)
        if not identity:
            raise AuthenticationError("Invalid credentials")
        
        password_hash = identity.attributes.get("password_hash")
        if not password_hash:
            raise AuthenticationError("Password authentication not configured")
        
        if not self.pwd_context.verify(password, password_hash):
            raise AuthenticationError("Invalid credentials")
        
        # Update last authenticated
        identity.last_authenticated = datetime.utcnow()
        
        # Create auth context
        context = AuthContext(
            identity=identity,
            session_id=secrets.token_urlsafe(32),
            authenticated_at=datetime.utcnow()
        )
        
        # Generate token
        context.token = self.generate_token(identity)
        
        # Store session
        self.sessions[context.session_id] = context
        
        self.log_info(f"Password authentication successful: {identity_id}")
        return context
    
    def authenticate_key(
        self,
        identity_id: str,
        signature: bytes,
        message: bytes
    ) -> AuthContext:
        """
        Authenticate using public key signature
        
        Args:
            identity_id: Identity identifier
            signature: Digital signature
            message: Signed message
        
        Returns:
            Authentication context
        """
        identity = self.identities.get(identity_id)
        if not identity:
            raise AuthenticationError("Invalid credentials")
        
        if not identity.public_key:
            raise AuthenticationError("Key authentication not configured")
        
        try:
            # Verify signature
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(identity.public_key)
            )
            public_key.verify(signature, message)
        except Exception as e:
            raise AuthenticationError(f"Signature verification failed: {e}")
        
        # Update last authenticated
        identity.last_authenticated = datetime.utcnow()
        
        # Create auth context
        context = AuthContext(
            identity=identity,
            session_id=secrets.token_urlsafe(32),
            authenticated_at=datetime.utcnow()
        )
        
        # Generate token
        context.token = self.generate_token(identity)
        
        # Store session
        self.sessions[context.session_id] = context
        
        self.log_info(f"Key authentication successful: {identity_id}")
        return context
    
    def generate_token(
        self,
        identity: Identity,
        expires_in: Optional[int] = None
    ) -> AuthToken:
        """
        Generate authentication token
        
        Args:
            identity: Identity to generate token for
            expires_in: Token expiration in seconds
        
        Returns:
            Authentication token
        """
        if expires_in is None:
            expires_in = self.settings.access_token_expire_minutes * 60
        
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(seconds=expires_in)
        
        # Create token payload
        payload = {
            "sub": identity.id,
            "type": identity.type,
            "name": identity.name,
            "auth_level": identity.auth_level.value,
            "permissions": [p.value for p in identity.permissions],
            "iat": issued_at.timestamp(),
            "exp": expires_at.timestamp(),
            "jti": secrets.token_urlsafe(16)
        }
        
        # Generate JWT
        token = jwt.encode(
            payload,
            self.settings.secret_key,
            algorithm="HS256"
        )
        
        # Generate refresh token
        refresh_token = secrets.token_urlsafe(32)
        
        auth_token = AuthToken(
            token=token,
            identity_id=identity.id,
            issued_at=issued_at,
            expires_at=expires_at,
            refresh_token=refresh_token,
            scopes=[p.value for p in identity.permissions]
        )
        
        self.log_debug(f"Generated token for {identity.id}")
        return auth_token
    
    def verify_token(self, token: str) -> Identity:
        """
        Verify authentication token
        
        Args:
            token: JWT token
        
        Returns:
            Identity associated with token
        """
        if token in self.blacklisted_tokens:
            raise AuthenticationError("Token has been revoked")
        
        try:
            # Decode JWT
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=["HS256"]
            )
            
            # Get identity
            identity_id = payload["sub"]
            identity = self.identities.get(identity_id)
            
            if not identity:
                raise AuthenticationError("Invalid token")
            
            return identity
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")
    
    def revoke_token(self, token: str) -> None:
        """Revoke a token"""
        self.blacklisted_tokens.add(token)
        self.log_info("Token revoked")
    
    def get_session(self, session_id: str) -> Optional[AuthContext]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: str) -> None:
        """End a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.log_info(f"Session ended: {session_id}")


class AuthorizationManager(LoggerMixin):
    """
    Manages authorization and access control
    """
    
    def __init__(self):
        """Initialize authorization manager"""
        # Role definitions
        self.roles: Dict[str, Set[Permission]] = {
            "admin": {
                Permission.SYSTEM_ADMIN,
                Permission.SYSTEM_MONITOR,
                Permission.SYSTEM_CONFIG,
                Permission.AGENT_CREATE,
                Permission.AGENT_READ,
                Permission.AGENT_UPDATE,
                Permission.AGENT_DELETE,
                Permission.AGENT_EXECUTE,
                Permission.TASK_SUBMIT,
                Permission.TASK_READ,
                Permission.TASK_CANCEL,
                Permission.PROTOCOL_SEND,
                Permission.PROTOCOL_RECEIVE,
                Permission.PROTOCOL_NEGOTIATE,
                Permission.SERVICE_REGISTER,
                Permission.SERVICE_DISCOVER,
                Permission.SERVICE_INVOKE
            },
            "operator": {
                Permission.SYSTEM_MONITOR,
                Permission.AGENT_READ,
                Permission.AGENT_UPDATE,
                Permission.AGENT_EXECUTE,
                Permission.TASK_SUBMIT,
                Permission.TASK_READ,
                Permission.TASK_CANCEL,
                Permission.PROTOCOL_SEND,
                Permission.PROTOCOL_RECEIVE,
                Permission.SERVICE_DISCOVER,
                Permission.SERVICE_INVOKE
            },
            "user": {
                Permission.AGENT_READ,
                Permission.TASK_SUBMIT,
                Permission.TASK_READ,
                Permission.SERVICE_DISCOVER,
                Permission.SERVICE_INVOKE
            },
            "agent": {
                Permission.TASK_SUBMIT,
                Permission.TASK_READ,
                Permission.PROTOCOL_SEND,
                Permission.PROTOCOL_RECEIVE,
                Permission.PROTOCOL_NEGOTIATE,
                Permission.SERVICE_REGISTER,
                Permission.SERVICE_DISCOVER,
                Permission.SERVICE_INVOKE
            }
        }
        
        # Resource access policies
        self.policies: Dict[str, Dict[str, Any]] = {}
        
        self.log_info("Authorization manager initialized")
    
    def check_permission(
        self,
        identity: Identity,
        permission: Permission,
        resource: Optional[str] = None
    ) -> bool:
        """
        Check if identity has permission
        
        Args:
            identity: Identity to check
            permission: Required permission
            resource: Optional resource identifier
        
        Returns:
            True if authorized
        """
        # System identity has all permissions
        if identity.id == "system":
            return True
        
        # Check direct permissions
        if permission in identity.permissions:
            return True
        
        # Check role-based permissions
        role = identity.attributes.get("role")
        if role and role in self.roles:
            if permission in self.roles[role]:
                return True
        
        # Check resource-specific policies
        if resource:
            policy = self.policies.get(resource)
            if policy:
                return self._evaluate_policy(identity, permission, policy)
        
        return False
    
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
        if not self.check_permission(identity, permission, resource):
            raise AuthorizationError(
                f"Identity {identity.id} lacks permission {permission.value}"
            )
    
    def grant_permission(
        self,
        identity: Identity,
        permission: Permission
    ) -> None:
        """Grant permission to identity"""
        identity.permissions.add(permission)
        self.log_info(f"Granted {permission.value} to {identity.id}")
    
    def revoke_permission(
        self,
        identity: Identity,
        permission: Permission
    ) -> None:
        """Revoke permission from identity"""
        identity.permissions.discard(permission)
        self.log_info(f"Revoked {permission.value} from {identity.id}")
    
    def assign_role(
        self,
        identity: Identity,
        role: str
    ) -> None:
        """Assign role to identity"""
        if role not in self.roles:
            raise ValueError(f"Unknown role: {role}")
        
        identity.attributes["role"] = role
        self.log_info(f"Assigned role {role} to {identity.id}")
    
    def create_policy(
        self,
        resource: str,
        policy: Dict[str, Any]
    ) -> None:
        """
        Create resource access policy
        
        Args:
            resource: Resource identifier
            policy: Policy definition
        """
        self.policies[resource] = policy
        self.log_info(f"Created policy for resource: {resource}")
    
    def _evaluate_policy(
        self,
        identity: Identity,
        permission: Permission,
        policy: Dict[str, Any]
    ) -> bool:
        """Evaluate resource policy"""
        # Check allow list
        allow_list = policy.get("allow", [])
        if identity.id in allow_list:
            return True
        
        # Check deny list
        deny_list = policy.get("deny", [])
        if identity.id in deny_list:
            return False
        
        # Check conditions
        conditions = policy.get("conditions", {})
        for condition, value in conditions.items():
            if condition == "min_trust_score":
                if identity.trust_score < value:
                    return False
            elif condition == "auth_level":
                required_level = AuthLevel[value.upper()]
                if identity.auth_level.value < required_level.value:
                    return False
        
        # Check permission requirements
        required_permissions = policy.get("required_permissions", [])
        for req_perm in required_permissions:
            if Permission[req_perm] not in identity.permissions:
                return False
        
        return True