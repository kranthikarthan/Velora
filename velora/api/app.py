"""
FastAPI application for Velora API Gateway
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
import uvicorn

from velora.core import VeloraCore, get_settings
from velora.core.logging import setup_logging, get_logger
from velora.api.routes import agents, protocols, tasks, system, websocket
from velora.api.models import (
    SystemStatus,
    HealthCheck,
    AgentCreate,
    TaskSubmit,
    MessageSend
)

# Global Velora instance
velora_core: Optional[VeloraCore] = None
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    """
    global velora_core
    
    # Startup
    logger.info("Starting Velora API Gateway")
    
    # Initialize Velora Core
    velora_core = VeloraCore()
    await velora_core.setup()
    await velora_core.start()
    
    logger.info("Velora API Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Velora API Gateway")
    
    if velora_core:
        await velora_core.stop()
    
    logger.info("Velora API Gateway shut down")


def create_app() -> FastAPI:
    """
    Create FastAPI application
    
    Returns:
        FastAPI application instance
    """
    settings = get_settings()
    
    # Setup logging
    setup_logging(settings.log_level)
    
    # Create FastAPI app
    app = FastAPI(
        title="Velora API Gateway",
        description="AI Interoperability Layer REST API",
        version=settings.app_version,
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Include routers
    app.include_router(system.router, prefix="/api/v1/system", tags=["System"])
    app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
    app.include_router(protocols.router, prefix="/api/v1/protocols", tags=["Protocols"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
    app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "Velora API Gateway",
            "version": settings.app_version,
            "status": "running",
            "documentation": "/docs"
        }
    
    # Health check endpoint
    @app.get("/health", response_model=HealthCheck)
    async def health_check():
        """Health check endpoint"""
        if not velora_core:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Velora Core not initialized"
            )
        
        health = await velora_core.health_check()
        return HealthCheck(**health)
    
    # Status endpoint
    @app.get("/status", response_model=SystemStatus)
    async def get_status():
        """Get system status"""
        if not velora_core:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Velora Core not initialized"
            )
        
        status = velora_core.get_status()
        return SystemStatus(**status)
    
    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle general exceptions"""
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.debug else None
            }
        )
    
    return app


def get_velora_core() -> VeloraCore:
    """
    Dependency to get Velora Core instance
    
    Returns:
        VeloraCore instance
    """
    if not velora_core:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Velora Core not initialized"
        )
    return velora_core


def run_server():
    """Run the API server"""
    settings = get_settings()
    app = create_app()
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.is_development
    )


if __name__ == "__main__":
    run_server()