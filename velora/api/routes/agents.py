"""
Agent management API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from velora.api.app import get_velora_core
from velora.api.models import (
    AgentCreate,
    AgentInfo,
    AgentMetrics,
    SuccessResponse,
    ErrorResponse
)
from velora.core import VeloraCore
from velora.core.exceptions import AgentError, ResourceNotFoundError

router = APIRouter()


@router.get("/", response_model=List[AgentInfo])
async def list_agents(
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    velora: VeloraCore = Depends(get_velora_core)
):
    """List all agents"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    agents = velora.agent_manager.list_agents(agent_type)
    return [
        AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            state=agent.state.value,
            type=agent.configuration.agent_type.value,
            capabilities=[cap.name for cap in agent.configuration.capabilities],
            metrics=agent.metrics,
            uptime_seconds=agent.metrics.get("uptime_seconds", 0)
        )
        for agent in agents
    ]


@router.post("/", response_model=AgentInfo)
async def create_agent(
    agent_data: AgentCreate,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Create a new agent"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        agent = await velora.agent_manager.create_agent(
            agent_type=agent_data.agent_type,
            agent_id=agent_data.agent_id
        )
        
        # Start the agent
        await agent.start()
        
        return AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            state=agent.state.value,
            type=agent.configuration.agent_type.value,
            capabilities=[cap.name for cap in agent.configuration.capabilities],
            metrics=agent.metrics,
            uptime_seconds=0
        )
    
    except AgentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Get agent by ID"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        agent = velora.agent_manager.get_agent(agent_id)
        return AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            state=agent.state.value,
            type=agent.configuration.agent_type.value,
            capabilities=[cap.name for cap in agent.configuration.capabilities],
            metrics=agent.metrics,
            uptime_seconds=agent.metrics.get("uptime_seconds", 0)
        )
    
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )


@router.post("/{agent_id}/start", response_model=SuccessResponse)
async def start_agent(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Start an agent"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        await velora.agent_manager.start_agent(agent_id)
        return SuccessResponse(message=f"Agent {agent_id} started")
    
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent: {str(e)}"
        )


@router.post("/{agent_id}/stop", response_model=SuccessResponse)
async def stop_agent(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Stop an agent"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        await velora.agent_manager.stop_agent(agent_id)
        return SuccessResponse(message=f"Agent {agent_id} stopped")
    
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop agent: {str(e)}"
        )


@router.delete("/{agent_id}", response_model=SuccessResponse)
async def remove_agent(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Remove an agent"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        await velora.agent_manager.remove_agent(agent_id)
        return SuccessResponse(message=f"Agent {agent_id} removed")
    
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove agent: {str(e)}"
        )


@router.get("/{agent_id}/status")
async def get_agent_status(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Get agent status"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        agent = velora.agent_manager.get_agent(agent_id)
        return agent.get_status()
    
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )


@router.get("/{agent_id}/health")
async def get_agent_health(
    agent_id: str,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Get agent health"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        agent = velora.agent_manager.get_agent(agent_id)
        return await agent.health_check()
    
    except ResourceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )


@router.post("/scale/{agent_type}", response_model=SuccessResponse)
async def scale_agents(
    agent_type: str,
    target_count: int = Query(..., ge=0, le=100, description="Target number of agents"),
    velora: VeloraCore = Depends(get_velora_core)
):
    """Scale agents of a specific type"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        await velora.agent_manager.scale_agents(agent_type, target_count)
        return SuccessResponse(
            message=f"Scaled {agent_type} agents to {target_count}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scale agents: {str(e)}"
        )


@router.get("/metrics/summary", response_model=AgentMetrics)
async def get_agent_metrics(velora: VeloraCore = Depends(get_velora_core)):
    """Get agent metrics summary"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    metrics = velora.agent_manager.get_metrics()
    return AgentMetrics(**metrics)