"""
Task management API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime

from velora.api.app import get_velora_core
from velora.api.models import (
    TaskSubmit,
    TaskInfo,
    SuccessResponse,
    ErrorResponse
)
from velora.core import VeloraCore
from velora.agents.base import TaskContext
from velora.core.exceptions import AgentError, ResourceNotFoundError

router = APIRouter()


@router.post("/submit", response_model=TaskInfo)
async def submit_task(
    task_data: TaskSubmit,
    velora: VeloraCore = Depends(get_velora_core)
):
    """Submit a task for processing"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        # Find or select agent
        agent = None
        
        if task_data.agent_id:
            # Use specified agent
            agent = velora.agent_manager.get_agent(task_data.agent_id)
        elif task_data.agent_type:
            # Auto-select agent of specified type
            agent = await velora.agent_manager.get_available_agent(task_data.agent_type)
            if not agent:
                raise AgentError(
                    f"No available agent of type {task_data.agent_type}",
                    "task_submit"
                )
        else:
            # Try to find any available agent
            for agent_type in ["data_processor", "protocol_translator", "api_integration"]:
                agent = await velora.agent_manager.get_available_agent(agent_type)
                if agent:
                    break
        
        if not agent:
            raise AgentError("No available agents", "task_submit")
        
        # Create task context
        task = TaskContext(
            task_type=task_data.task_type,
            input_data=task_data.input_data,
            parameters=task_data.parameters,
            constraints=task_data.constraints,
            priority=task_data.priority
        )
        
        # Submit task
        task_id = await agent.submit_task(task)
        
        return TaskInfo(
            task_id=task_id,
            agent_id=agent.agent_id,
            task_type=task_data.task_type,
            status="queued",
            submitted_at=datetime.utcnow()
        )
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AgentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskInfo)
async def get_task_status(
    task_id: str,
    agent_id: Optional[str] = Query(None, description="Agent ID if known"),
    velora: VeloraCore = Depends(get_velora_core)
):
    """Get task status"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        # Find task in agent
        if agent_id:
            agent = velora.agent_manager.get_agent(agent_id)
            
            # Check active tasks
            if task_id in agent.active_tasks:
                task = agent.active_tasks[task_id]
                return TaskInfo(
                    task_id=task_id,
                    agent_id=agent_id,
                    task_type=task.task_type,
                    status="processing",
                    submitted_at=datetime.utcnow()
                )
            
            # Check completed tasks
            for result in agent.completed_tasks:
                if result.task_id == task_id:
                    return TaskInfo(
                        task_id=task_id,
                        agent_id=agent_id,
                        task_type="",
                        status=result.status,
                        submitted_at=result.start_time,
                        started_at=result.start_time,
                        completed_at=result.end_time,
                        result=result.output_data,
                        error=result.error
                    )
        else:
            # Search all agents
            for agent in velora.agent_manager.list_agents():
                if task_id in agent.active_tasks:
                    task = agent.active_tasks[task_id]
                    return TaskInfo(
                        task_id=task_id,
                        agent_id=agent.agent_id,
                        task_type=task.task_type,
                        status="processing",
                        submitted_at=datetime.utcnow()
                    )
                
                for result in agent.completed_tasks:
                    if result.task_id == task_id:
                        return TaskInfo(
                            task_id=task_id,
                            agent_id=agent.agent_id,
                            task_type="",
                            status=result.status,
                            submitted_at=result.start_time,
                            started_at=result.start_time,
                            completed_at=result.end_time,
                            result=result.output_data,
                            error=result.error
                        )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/agent/{agent_id}/tasks", response_model=List[TaskInfo])
async def get_agent_tasks(
    agent_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    velora: VeloraCore = Depends(get_velora_core)
):
    """Get tasks for a specific agent"""
    if not velora.agent_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    
    try:
        agent = velora.agent_manager.get_agent(agent_id)
        tasks = []
        
        # Add active tasks
        for task_id, task in agent.active_tasks.items():
            task_info = TaskInfo(
                task_id=task_id,
                agent_id=agent_id,
                task_type=task.task_type,
                status="processing",
                submitted_at=datetime.utcnow()
            )
            if not status_filter or task_info.status == status_filter:
                tasks.append(task_info)
        
        # Add completed tasks
        for result in agent.completed_tasks:
            task_info = TaskInfo(
                task_id=result.task_id,
                agent_id=agent_id,
                task_type="",
                status=result.status,
                submitted_at=result.start_time,
                started_at=result.start_time,
                completed_at=result.end_time,
                result=result.output_data,
                error=result.error
            )
            if not status_filter or task_info.status == status_filter:
                tasks.append(task_info)
        
        return tasks
    
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )