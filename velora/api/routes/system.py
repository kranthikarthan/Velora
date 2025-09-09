"""
System management API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from velora.api.app import get_velora_core
from velora.api.models import SystemStatus, HealthCheck, SuccessResponse, ErrorResponse
from velora.core import VeloraCore

router = APIRouter()


@router.get("/status", response_model=SystemStatus)
async def get_system_status(velora: VeloraCore = Depends(get_velora_core)):
    """Get system status"""
    return velora.get_status()


@router.get("/health", response_model=HealthCheck)
async def health_check(velora: VeloraCore = Depends(get_velora_core)):
    """Perform health check"""
    health = await velora.health_check()
    return health


@router.post("/restart", response_model=SuccessResponse)
async def restart_system(velora: VeloraCore = Depends(get_velora_core)):
    """Restart the system"""
    try:
        await velora.restart()
        return SuccessResponse(message="System restart initiated")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart system: {str(e)}"
        )


@router.get("/config")
async def get_configuration(velora: VeloraCore = Depends(get_velora_core)):
    """Get system configuration (non-sensitive)"""
    settings = velora.settings
    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "uaicp_version": settings.uaicp_version,
        "anp_version": settings.anp_version,
        "agent_heartbeat_interval": settings.agent_heartbeat_interval,
        "metrics_enabled": settings.metrics_enabled,
        "log_level": settings.log_level
    }


@router.get("/metrics")
async def get_metrics(velora: VeloraCore = Depends(get_velora_core)):
    """Get system metrics"""
    metrics = {
        "uptime_seconds": velora.get_uptime(),
        "agent_metrics": {},
        "protocol_metrics": {},
        "data_metrics": {}
    }
    
    # Get agent metrics
    if velora.agent_manager:
        metrics["agent_metrics"] = velora.agent_manager.get_metrics()
    
    # Get protocol metrics
    if velora.protocol_manager:
        health = await velora.protocol_manager.health_check()
        metrics["protocol_metrics"] = health
    
    return metrics