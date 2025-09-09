"""
Protocol management API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from velora.api.app import get_velora_core
from velora.api.models import (
    MessageSend,
    MessageInfo,
    ServiceRegister,
    ServiceQuery,
    ServiceInfo,
    ProtocolStats,
    SuccessResponse
)
from velora.core import VeloraCore
from velora.protocols.anp import ServiceRegistration, ServiceStatus

router = APIRouter()


@router.get("/stats", response_model=ProtocolStats)
async def get_protocol_stats(velora: VeloraCore = Depends(get_velora_core)):
    """Get protocol statistics"""
    if not velora.protocol_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol manager not initialized"
        )
    
    health = await velora.protocol_manager.health_check()
    
    return ProtocolStats(
        agent_id=velora.protocol_manager.agent_id,
        active_connections=health.get("active_connections", 0),
        registered_services=health.get("registered_services", 0),
        known_agents=health.get("known_agents", 0),
        active_negotiations=health.get("active_negotiations", 0)
    )


@router.post("/message/send", response_model=MessageInfo)
async def send_message(
    message_data: MessageSend,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Send a message via UAICP"""
    if not velora.protocol_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol manager not initialized"
        )
    
    try:
        # Create and send message
        message = velora.protocol_manager.uaicp.create_message(
            message_type=message_data.message_type,
            destination_agent_id=message_data.destination_agent,
            payload=message_data.payload,
            priority=message_data.priority
        )
        
        # Send with optional timeout
        response = await velora.protocol_manager.uaicp.send_message(
            message,
            timeout=message_data.timeout
        )
        
        return MessageInfo(
            message_id=message.message_id,
            message_type=message.message_type,
            source_agent=velora.protocol_manager.agent_id,
            destination_agent=message_data.destination_agent,
            timestamp=message.timestamp,
            status="sent" if not response else "acknowledged",
            response=response.payload if response else None
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.post("/service/register", response_model=ServiceInfo)
async def register_service(
    service_data: ServiceRegister,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Register a service via ANP"""
    if not velora.protocol_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol manager not initialized"
        )
    
    try:
        # Create service registration
        service = ServiceRegistration(
            agent_id=velora.protocol_manager.agent_id,
            service_name=service_data.service_name,
            service_version=service_data.service_version,
            service_category=service_data.service_category,
            service_description=service_data.service_description,
            capability_manifest={"capabilities": service_data.capabilities},
            api_specification=service_data.api_specification or {},
            pricing_information=service_data.pricing_information or {}
        )
        
        # Register service
        registration_id = velora.protocol_manager.anp.register_service(service)
        
        return ServiceInfo(
            service_id=service.service_id,
            agent_id=service.agent_id,
            service_name=service.service_name,
            service_version=service.service_version,
            service_category=service.service_category,
            status=service.status.value,
            capabilities=service_data.capabilities,
            registration_timestamp=service.registration_timestamp,
            last_heartbeat=service.last_heartbeat
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register service: {str(e)}"
        )


@router.post("/service/discover", response_model=List[ServiceInfo])
async def discover_services(
    query: ServiceQuery,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Discover services via ANP"""
    if not velora.protocol_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol manager not initialized"
        )
    
    try:
        # Discover services
        services = velora.protocol_manager.anp.discover_services(
            capability_requirements=query.capabilities,
            filters=query.filters
        )
        
        return [
            ServiceInfo(
                service_id=service.service_id,
                agent_id=service.agent_id,
                service_name=service.service_name,
                service_version=service.service_version,
                service_category=service.service_category,
                status=service.status.value,
                capabilities=service.capability_manifest.get("capabilities", []),
                registration_timestamp=service.registration_timestamp,
                last_heartbeat=service.last_heartbeat
            )
            for service in services
        ]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover services: {str(e)}"
        )


@router.get("/services", response_model=List[ServiceInfo])
async def list_services(velora: VeloraCore = Depends(get_velora_core)):
    """List all registered services"""
    if not velora.protocol_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol manager not initialized"
        )
    
    services = []
    for service in velora.protocol_manager.anp.service_registry.values():
        services.append(
            ServiceInfo(
                service_id=service.service_id,
                agent_id=service.agent_id,
                service_name=service.service_name,
                service_version=service.service_version,
                service_category=service.service_category,
                status=service.status.value,
                capabilities=service.capability_manifest.get("capabilities", []),
                registration_timestamp=service.registration_timestamp,
                last_heartbeat=service.last_heartbeat
            )
        )
    
    return services


@router.post("/connect/{agent_id}", response_model=SuccessResponse)
async def connect_to_agent(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Establish connection with remote agent"""
    if not velora.protocol_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol manager not initialized"
        )
    
    try:
        success = await velora.protocol_manager.establish_connection(agent_id)
        if success:
            return SuccessResponse(message=f"Connected to agent {agent_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to agent {agent_id}"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection failed: {str(e)}"
        )


@router.post("/disconnect/{agent_id}", response_model=SuccessResponse)
async def disconnect_from_agent(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Close connection with remote agent"""
    if not velora.protocol_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protocol manager not initialized"
        )
    
    try:
        await velora.protocol_manager.close_connection(agent_id)
        return SuccessResponse(message=f"Disconnected from agent {agent_id}")
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disconnection failed: {str(e)}"
        )