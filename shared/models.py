"""
Shared data models for the multi-agent system.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Enumeration of possible agent roles."""
    ARCHITECT = "architect"
    FRONTEND = "frontend"
    BACKEND = "backend"
    QA = "qa"
    DEVOPS = "devops"
    PRODUCT_MANAGER = "product_manager"


class MessageType(str, Enum):
    """Enumeration of message types."""
    TASK_ASSIGNMENT = "task_assignment"
    CODE_REVIEW = "code_review"
    STATUS_UPDATE = "status_update"
    COLLABORATION_REQUEST = "collaboration_request"
    DEBUGGING_REQUEST = "debugging_request"
    ARCHITECTURE_DISCUSSION = "architecture_discussion"


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    name: str = Field(..., description="Unique agent identifier")
    model: str = Field(..., description="AI model to use (e.g., gpt-4, claude-3)")
    personality: str = Field(..., description="Agent's behavioral traits")
    job_description: str = Field(..., description="Role and responsibilities")
    system_prompt: str = Field(..., description="Core instructions for the agent")
    goal: str = Field(..., description="Primary objective")
    slack_username: str = Field(..., description="Slack username for the agent")
    github_username: str = Field(..., description="GitHub username for the agent")
    docker_image: str = Field(..., description="Docker image to use")
    environment_variables: List[str] = Field(default_factory=list, description="Environment variables")
    role: AgentRole = Field(..., description="Agent's role in the system")


class SlackMessage(BaseModel):
    """Model for Slack messages."""
    channel: str = Field(..., description="Slack channel ID or name")
    text: str = Field(..., description="Message text")
    thread_ts: Optional[str] = Field(None, description="Thread timestamp for replies")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="Message attachments")
    blocks: Optional[List[Dict[str, Any]]] = Field(None, description="Message blocks")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GitHubCommit(BaseModel):
    """Model for GitHub commits."""
    repository: str = Field(..., description="Repository name")
    branch: str = Field(..., description="Branch name")
    message: str = Field(..., description="Commit message")
    files: List[Dict[str, Any]] = Field(..., description="Files to commit")
    agent_name: str = Field(..., description="Agent making the commit")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GitHubPR(BaseModel):
    """Model for GitHub pull requests."""
    repository: str = Field(..., description="Repository name")
    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    head_branch: str = Field(..., description="Source branch")
    base_branch: str = Field(..., description="Target branch")
    agent_name: str = Field(..., description="Agent creating the PR")
    reviewers: List[str] = Field(default_factory=list, description="Requested reviewers")
    labels: List[str] = Field(default_factory=list, description="PR labels")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """Model for agent state persistence."""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_name: str = Field(..., description="Agent name")
    current_task: Optional[str] = Field(None, description="Current task being worked on")
    task_status: str = Field("idle", description="Current task status")
    context_window: List[Dict[str, Any]] = Field(default_factory=list, description="Context window data")
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    memory: Dict[str, Any] = Field(default_factory=dict, description="Agent's persistent memory")
    collaboration_history: List[Dict[str, Any]] = Field(default_factory=list, description="Collaboration history")
    github_activity: List[Dict[str, Any]] = Field(default_factory=list, description="GitHub activity history")
    slack_activity: List[Dict[str, Any]] = Field(default_factory=list, description="Slack activity history")


class CollaborationRequest(BaseModel):
    """Model for collaboration requests between agents."""
    requester_id: str = Field(..., description="Agent requesting collaboration")
    target_agent_id: str = Field(..., description="Agent to collaborate with")
    request_type: MessageType = Field(..., description="Type of collaboration request")
    description: str = Field(..., description="Description of the collaboration needed")
    priority: str = Field("medium", description="Priority level")
    deadline: Optional[datetime] = Field(None, description="Deadline for the request")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskAssignment(BaseModel):
    """Model for task assignments."""
    task_id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    assigned_agent: str = Field(..., description="Agent assigned to the task")
    assigned_by: str = Field(..., description="Agent assigning the task")
    priority: str = Field("medium", description="Task priority")
    estimated_duration: Optional[str] = Field(None, description="Estimated duration")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Acceptance criteria")
    status: str = Field("assigned", description="Task status")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SystemConfig(BaseModel):
    """Model for system-wide configuration."""
    name: str = Field(..., description="System name")
    version: str = Field(..., description="System version")
    environment: str = Field(..., description="Environment (development, staging, production)")
    database: Dict[str, Any] = Field(..., description="Database configuration")
    slack: Dict[str, Any] = Field(..., description="Slack configuration")
    github: Dict[str, Any] = Field(..., description="GitHub configuration")
    agents: List[AgentConfig] = Field(..., description="Agent configurations")
    docker: Dict[str, Any] = Field(..., description="Docker configuration")
    logging: Dict[str, Any] = Field(..., description="Logging configuration")
    security: Dict[str, Any] = Field(..., description="Security configuration")


class HealthCheck(BaseModel):
    """Model for health check responses."""
    status: str = Field(..., description="Health status")
    agent_name: str = Field(..., description="Agent name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime: float = Field(..., description="Uptime in seconds")
    memory_usage: Dict[str, Any] = Field(..., description="Memory usage information")
    active_tasks: int = Field(..., description="Number of active tasks")
    last_activity: datetime = Field(..., description="Last activity timestamp") 