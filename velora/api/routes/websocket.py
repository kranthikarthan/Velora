"""
WebSocket API routes for real-time communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

from velora.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


@router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time events"""
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif message.get("type") == "subscribe":
                    # Handle event subscription
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "subscribed",
                        "events": message.get("events", []),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    finally:
        # Remove from active connections
        active_connections.discard(websocket)
        logger.info("WebSocket connection closed")


async def broadcast_event(event: Dict):
    """Broadcast event to all connected WebSocket clients"""
    if not active_connections:
        return
    
    # Add timestamp if not present
    if "timestamp" not in event:
        event["timestamp"] = datetime.utcnow().isoformat()
    
    # Send to all connected clients
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except Exception as e:
            logger.error(f"Failed to send to WebSocket: {e}")
            disconnected.add(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        active_connections.discard(conn)