"""
SQLAlchemy database models for the multi-agent system.
"""
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Agent(Base):
    """Database model for agent information."""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    personality = Column(Text, nullable=False)
    job_description = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    goal = Column(Text, nullable=False)
    slack_username = Column(String(255), nullable=False)
    github_username = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    states = relationship("AgentState", back_populates="agent")
    messages = relationship("Message", back_populates="agent")
    activities = relationship("AgentActivity", back_populates="agent")
    
    __table_args__ = (
        Index('idx_agent_id', 'agent_id'),
        Index('idx_agent_name', 'name'),
        Index('idx_agent_role', 'role'),
    )


class AgentState(Base):
    """Database model for agent state persistence."""
    __tablename__ = "agent_states"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    current_task = Column(String(500), nullable=True)
    task_status = Column(String(100), default="idle")
    context_window = Column(JSON, default=list)
    memory = Column(JSON, default=dict)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="states")
    
    __table_args__ = (
        Index('idx_agent_state_agent_id', 'agent_id'),
        Index('idx_agent_state_last_activity', 'last_activity'),
    )


class Message(Base):
    """Database model for messages between agents."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, index=True, nullable=False)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    channel = Column(String(255), nullable=False)
    message_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    thread_ts = Column(String(255), nullable=True)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="messages")
    
    __table_args__ = (
        Index('idx_message_id', 'message_id'),
        Index('idx_message_agent_id', 'agent_id'),
        Index('idx_message_channel', 'channel'),
        Index('idx_message_type', 'message_type'),
        Index('idx_message_created_at', 'created_at'),
    )


class AgentActivity(Base):
    """Database model for tracking agent activities."""
    __tablename__ = "agent_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    activity_type = Column(String(100), nullable=False)  # slack, github, task, collaboration
    action = Column(String(255), nullable=False)  # message_sent, commit_made, pr_created, etc.
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="activities")
    
    __table_args__ = (
        Index('idx_activity_agent_id', 'agent_id'),
        Index('idx_activity_type', 'activity_type'),
        Index('idx_activity_timestamp', 'timestamp'),
    )


class Task(Base):
    """Database model for task management."""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    assigned_agent = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    assigned_by = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    priority = Column(String(50), default="medium")
    status = Column(String(100), default="assigned")
    estimated_duration = Column(String(100), nullable=True)
    dependencies = Column(JSON, default=list)
    acceptance_criteria = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_task_assigned_agent', 'assigned_agent'),
        Index('idx_task_status', 'status'),
        Index('idx_task_priority', 'priority'),
    )


class Collaboration(Base):
    """Database model for collaboration requests."""
    __tablename__ = "collaborations"
    
    id = Column(Integer, primary_key=True, index=True)
    collaboration_id = Column(String(255), unique=True, index=True, nullable=False)
    requester_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    target_agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    request_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(50), default="medium")
    status = Column(String(100), default="pending")
    deadline = Column(DateTime(timezone=True), nullable=True)
    context = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_collaboration_id', 'collaboration_id'),
        Index('idx_collaboration_requester', 'requester_id'),
        Index('idx_collaboration_target', 'target_agent_id'),
        Index('idx_collaboration_status', 'status'),
    )


class GitHubActivity(Base):
    """Database model for GitHub activities."""
    __tablename__ = "github_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(255), ForeignKey("agents.agent_id"), nullable=False)
    activity_type = Column(String(100), nullable=False)  # commit, pr, review, comment
    repository = Column(String(255), nullable=False)
    branch = Column(String(255), nullable=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_github_agent_id', 'agent_id'),
        Index('idx_github_activity_type', 'activity_type'),
        Index('idx_github_repository', 'repository'),
        Index('idx_github_timestamp', 'timestamp'),
    )


class SystemLog(Base):
    """Database model for system logging."""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    component = Column(String(100), nullable=False)  # agent, slack, github, database, etc.
    message = Column(Text, nullable=False)
    metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_log_level', 'level'),
        Index('idx_log_component', 'component'),
        Index('idx_log_timestamp', 'timestamp'),
    ) 