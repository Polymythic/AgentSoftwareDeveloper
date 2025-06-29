"""
FastAPI application for agent management and monitoring.
"""
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agents.main import AgentRunner
from shared.models import HealthCheck, TaskAssignment, CollaborationRequest, MessageType
from database.manager import db_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Multi-Agent System API",
    description="API for managing and monitoring multi-agent software development system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent runner
agent_runner: Optional[AgentRunner] = None


class TaskRequest(BaseModel):
    """Request model for task assignment."""
    title: str
    description: str
    assigned_agent: str
    priority: str = "medium"
    estimated_duration: Optional[str] = None
    dependencies: List[str] = []
    acceptance_criteria: List[str] = []


class CollaborationRequestModel(BaseModel):
    """Request model for collaboration."""
    target_agent: str
    request_type: str
    description: str
    priority: str = "medium"


@app.on_event("startup")
async def startup_event():
    """Initialize the agent runner on startup."""
    global agent_runner
    try:
        agent_runner = AgentRunner()
        logger.info("Agent runner initialized")
    except Exception as e:
        logger.error(f"Failed to initialize agent runner: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown the agent runner on shutdown."""
    global agent_runner
    if agent_runner:
        await agent_runner.stop_all_agents()
        logger.info("Agent runner shutdown complete")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Multi-Agent System API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "agents_running": len(agent_runner.agents) if agent_runner else 0
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def get_agents():
    """Get all configured agents."""
    try:
        if not agent_runner or not agent_runner.config:
            return {"agents": []}
        
        agents = []
        for agent_config in agent_runner.config.agents:
            agents.append({
                "name": agent_config.name,
                "role": agent_config.role.value,
                "model": agent_config.model,
                "personality": agent_config.personality,
                "goal": agent_config.goal,
                "is_running": agent_config.name in agent_runner.agents
            })
        
        return {"agents": agents}
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get specific agent information."""
    try:
        if not agent_runner:
            raise HTTPException(status_code=503, detail="Agent runner not initialized")
        
        # Get agent status
        status = agent_runner.get_agent_status(agent_name)
        
        # Get agent configuration
        if agent_runner.config:
            for agent_config in agent_runner.config.agents:
                if agent_config.name == agent_name:
                    return {
                        "name": agent_config.name,
                        "role": agent_config.role.value,
                        "model": agent_config.model,
                        "personality": agent_config.personality,
                        "job_description": agent_config.job_description,
                        "goal": agent_config.goal,
                        "status": status
                    }
        
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_name}/start")
async def start_agent(agent_name: str, background_tasks: BackgroundTasks):
    """Start a specific agent."""
    try:
        if not agent_runner:
            raise HTTPException(status_code=503, detail="Agent runner not initialized")
        
        background_tasks.add_task(agent_runner.start_agent, agent_name)
        
        return {
            "message": f"Starting agent {agent_name}",
            "agent_name": agent_name
        }
        
    except Exception as e:
        logger.error(f"Failed to start agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_name}/stop")
async def stop_agent(agent_name: str, background_tasks: BackgroundTasks):
    """Stop a specific agent."""
    try:
        if not agent_runner:
            raise HTTPException(status_code=503, detail="Agent runner not initialized")
        
        background_tasks.add_task(agent_runner.stop_agent, agent_name)
        
        return {
            "message": f"Stopping agent {agent_name}",
            "agent_name": agent_name
        }
        
    except Exception as e:
        logger.error(f"Failed to stop agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{agent_name}/restart")
async def restart_agent(agent_name: str, background_tasks: BackgroundTasks):
    """Restart a specific agent."""
    try:
        if not agent_runner:
            raise HTTPException(status_code=503, detail="Agent runner not initialized")
        
        background_tasks.add_task(agent_runner.restart_agent, agent_name)
        
        return {
            "message": f"Restarting agent {agent_name}",
            "agent_name": agent_name
        }
        
    except Exception as e:
        logger.error(f"Failed to restart agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{agent_name}/tasks")
async def get_agent_tasks(agent_name: str):
    """Get tasks assigned to an agent."""
    try:
        tasks = db_manager.get_agent_tasks(agent_name)
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Failed to get tasks for agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks")
async def create_task(task_request: TaskRequest):
    """Create a new task."""
    try:
        import uuid
        
        task = TaskAssignment(
            task_id=str(uuid.uuid4()),
            title=task_request.title,
            description=task_request.description,
            assigned_agent=task_request.assigned_agent,
            assigned_by="api",
            priority=task_request.priority,
            estimated_duration=task_request.estimated_duration,
            dependencies=task_request.dependencies,
            acceptance_criteria=task_request.acceptance_criteria,
            status="assigned"
        )
        
        success = db_manager.store_task(task)
        
        if success:
            return {
                "message": "Task created successfully",
                "task_id": task.task_id,
                "task": task.dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create task")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collaboration")
async def request_collaboration(collab_request: CollaborationRequestModel):
    """Request collaboration between agents."""
    try:
        if not agent_runner:
            raise HTTPException(status_code=503, detail="Agent runner not initialized")
        
        # Find the requesting agent (assuming it's the first running agent)
        requesting_agent = None
        for agent_name, agent in agent_runner.agents.items():
            requesting_agent = agent
            break
        
        if not requesting_agent:
            raise HTTPException(status_code=400, detail="No agents are currently running")
        
        # Convert string to MessageType enum
        try:
            message_type = MessageType(collab_request.request_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid request type: {collab_request.request_type}")
        
        success = await requesting_agent.request_collaboration(
            target_agent=collab_request.target_agent,
            request_type=message_type,
            description=collab_request.description,
            priority=collab_request.priority
        )
        
        if success:
            return {
                "message": "Collaboration request sent",
                "requester": requesting_agent.name,
                "target": collab_request.target_agent,
                "type": collab_request.request_type
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send collaboration request")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to request collaboration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/database/stats")
async def get_database_stats():
    """Get database statistics."""
    try:
        stats = db_manager.get_database_stats()
        return {"database_stats": stats}
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics."""
    try:
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            metrics = generate_latest()
            return metrics
        except ImportError:
            # Return basic metrics if prometheus_client is not available
            return {
                "status": "prometheus_client not available",
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent system logs."""
    try:
        # This would typically read from a log file or database
        # For now, return a placeholder
        return {
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "Log retrieval not implemented yet"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "agents.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 