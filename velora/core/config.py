"""
Configuration management for Velora
"""

from functools import lru_cache
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
import os


class Settings(BaseSettings):
    """Main configuration settings for Velora"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Application settings
    app_name: str = Field(default="Velora", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=4, description="Number of worker processes")
    
    # Database settings
    database_url: str = Field(
        default="postgresql://velora:velora@localhost:5432/velora",
        description="PostgreSQL database URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and message queuing"
    )
    neo4j_url: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j graph database URL"
    )
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password", description="Neo4j password")
    mongodb_url: str = Field(
        default="mongodb://localhost:27017/velora",
        description="MongoDB URL for document storage"
    )
    
    # Message Queue settings
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    kafka_topic_prefix: str = Field(default="velora", description="Kafka topic prefix")
    
    # Security settings
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    cors_allow_methods: List[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_allow_headers: List[str] = Field(default=["*"], description="Allowed CORS headers")
    
    # Protocol settings
    uaicp_version: str = Field(default="1.0", description="UAICP protocol version")
    anp_version: str = Field(default="1.0", description="ANP protocol version")
    max_message_size: int = Field(default=10485760, description="Maximum message size in bytes (10MB)")
    message_timeout: int = Field(default=30, description="Message timeout in seconds")
    
    # Agent settings
    agent_heartbeat_interval: int = Field(default=30, description="Agent heartbeat interval in seconds")
    agent_max_retries: int = Field(default=3, description="Maximum agent retry attempts")
    agent_retry_delay: int = Field(default=5, description="Agent retry delay in seconds")
    
    # Performance settings
    connection_pool_size: int = Field(default=20, description="Database connection pool size")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    
    # Monitoring settings
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    tracing_enabled: bool = Field(default=True, description="Enable distributed tracing")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Cloud provider settings
    cloud_provider: str = Field(default="local", description="Cloud provider (local, aws, azure, gcp)")
    aws_region: Optional[str] = Field(default=None, description="AWS region")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key")
    azure_subscription_id: Optional[str] = Field(default=None, description="Azure subscription ID")
    gcp_project_id: Optional[str] = Field(default=None, description="GCP project ID")
    
    # Legacy system settings
    mainframe_host: Optional[str] = Field(default=None, description="Mainframe host")
    mainframe_port: Optional[int] = Field(default=23, description="Mainframe port")
    mainframe_region: Optional[str] = Field(default=None, description="Mainframe CICS region")
    payment_gateway_url: Optional[str] = Field(default=None, description="Payment gateway URL")
    
    # AI/ML settings
    model_cache_dir: str = Field(default="/tmp/velora/models", description="Model cache directory")
    max_model_size: int = Field(default=5368709120, description="Maximum model size in bytes (5GB)")
    inference_timeout: int = Field(default=60, description="Inference timeout in seconds")
    batch_size: int = Field(default=32, description="Default batch size for ML operations")
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"
    
    def get_database_settings(self) -> Dict[str, Any]:
        """Get database connection settings"""
        return {
            "url": self.database_url,
            "pool_size": self.connection_pool_size,
            "echo": self.debug,
        }
    
    def get_redis_settings(self) -> Dict[str, Any]:
        """Get Redis connection settings"""
        return {
            "url": self.redis_url,
            "decode_responses": True,
            "max_connections": self.connection_pool_size,
        }
    
    def get_kafka_settings(self) -> Dict[str, Any]:
        """Get Kafka connection settings"""
        return {
            "bootstrap_servers": self.kafka_bootstrap_servers.split(","),
            "client_id": f"{self.app_name}-{self.environment}",
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create global settings instance
settings = get_settings()