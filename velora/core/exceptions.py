"""
Custom exceptions for Velora
"""

from typing import Optional, Dict, Any


class VeloraException(Exception):
    """Base exception for all Velora exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "VELORA_ERROR"
        self.details = details or {}


class ConfigurationError(VeloraException):
    """Configuration related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class ProtocolError(VeloraException):
    """Protocol related errors"""
    
    def __init__(self, message: str, protocol: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["protocol"] = protocol
        super().__init__(message, "PROTOCOL_ERROR", details)


class AgentError(VeloraException):
    """Agent related errors"""
    
    def __init__(self, message: str, agent_id: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["agent_id"] = agent_id
        super().__init__(message, "AGENT_ERROR", details)


class AuthenticationError(VeloraException):
    """Authentication related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTH_ERROR", details)


class AuthorizationError(VeloraException):
    """Authorization related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHZ_ERROR", details)


class ValidationError(VeloraException):
    """Data validation errors"""
    
    def __init__(self, message: str, field: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", details)


class DataError(VeloraException):
    """Data processing errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATA_ERROR", details)


class NetworkError(VeloraException):
    """Network related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NETWORK_ERROR", details)


class TimeoutError(VeloraException):
    """Operation timeout errors"""
    
    def __init__(self, message: str, timeout: int, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["timeout"] = timeout
        super().__init__(message, "TIMEOUT_ERROR", details)


class ResourceNotFoundError(VeloraException):
    """Resource not found errors"""
    
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["resource_type"] = resource_type
        details["resource_id"] = resource_id
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message, "NOT_FOUND_ERROR", details)


class ConflictError(VeloraException):
    """Resource conflict errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT_ERROR", details)


class RateLimitError(VeloraException):
    """Rate limiting errors"""
    
    def __init__(self, message: str, limit: int, window: int, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["limit"] = limit
        details["window"] = window
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class SecurityError(VeloraException):
    """Security related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SECURITY_ERROR", details)


class IntegrationError(VeloraException):
    """External integration errors"""
    
    def __init__(self, message: str, system: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["system"] = system
        super().__init__(message, "INTEGRATION_ERROR", details)