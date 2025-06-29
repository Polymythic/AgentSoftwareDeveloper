"""
Database manager for the multi-agent system.
"""
import os
import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base
from shared.models import AgentConfig, AgentState, Message, TaskAssignment, CollaborationRequest

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for the multi-agent system."""
    
    def __init__(self, db_path: str = "./database/agents.db"):
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the database connection and create tables."""
        try:
            # Ensure database directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create SQLAlchemy engine
            self.engine = create_engine(
                f"sqlite:///{self.db_path}",
                connect_args={"check_same_thread": False},
                echo=False
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            logger.info(f"Database initialized successfully at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup.
        
        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def store_agent_state(self, agent_id: str, state: AgentState) -> bool:
        """Store agent state in the database.
        
        Args:
            agent_id: Unique agent identifier
            state: Agent state to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                # Check if state exists
                existing_state = session.query(Base.classes.agent_states).filter(
                    Base.classes.agent_states.c.agent_id == agent_id
                ).first()
                
                if existing_state:
                    # Update existing state
                    session.execute(
                        text("""
                            UPDATE agent_states 
                            SET current_task = :current_task,
                                task_status = :task_status,
                                context_window = :context_window,
                                memory = :memory,
                                last_activity = :last_activity,
                                updated_at = :updated_at
                            WHERE agent_id = :agent_id
                        """),
                        {
                            "agent_id": agent_id,
                            "current_task": state.current_task,
                            "task_status": state.task_status,
                            "context_window": json.dumps(state.context_window),
                            "memory": json.dumps(state.memory),
                            "last_activity": state.last_activity,
                            "updated_at": datetime.utcnow()
                        }
                    )
                else:
                    # Insert new state
                    session.execute(
                        text("""
                            INSERT INTO agent_states 
                            (agent_id, current_task, task_status, context_window, memory, last_activity, created_at, updated_at)
                            VALUES (:agent_id, :current_task, :task_status, :context_window, :memory, :last_activity, :created_at, :updated_at)
                        """),
                        {
                            "agent_id": agent_id,
                            "current_task": state.current_task,
                            "task_status": state.task_status,
                            "context_window": json.dumps(state.context_window),
                            "memory": json.dumps(state.memory),
                            "last_activity": state.last_activity,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to store agent state: {e}")
            return False
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Retrieve agent state from the database.
        
        Args:
            agent_id: Unique agent identifier
            
        Returns:
            Agent state if found, None otherwise
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text("SELECT * FROM agent_states WHERE agent_id = :agent_id"),
                    {"agent_id": agent_id}
                ).fetchone()
                
                if result:
                    return AgentState(
                        agent_id=result.agent_id,
                        agent_name=result.agent_name,
                        current_task=result.current_task,
                        task_status=result.task_status,
                        context_window=json.loads(result.context_window) if result.context_window else [],
                        last_activity=result.last_activity,
                        memory=json.loads(result.memory) if result.memory else {},
                        collaboration_history=[],
                        github_activity=[],
                        slack_activity=[]
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve agent state: {e}")
            return None
    
    def store_message(self, message: Message) -> bool:
        """Store a message in the database.
        
        Args:
            message: Message to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                        INSERT INTO messages 
                        (message_id, agent_id, channel, message_type, content, metadata, thread_ts, is_processed, created_at)
                        VALUES (:message_id, :agent_id, :channel, :message_type, :content, :metadata, :thread_ts, :is_processed, :created_at)
                    """),
                    {
                        "message_id": message.message_id,
                        "agent_id": message.agent_id,
                        "channel": message.channel,
                        "message_type": message.message_type,
                        "content": message.content,
                        "metadata": json.dumps(message.metadata),
                        "thread_ts": message.thread_ts,
                        "is_processed": message.is_processed,
                        "created_at": message.created_at
                    }
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return False
    
    def get_recent_messages(self, channel: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages from a channel.
        
        Args:
            channel: Channel name or ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        try:
            with self.get_session() as session:
                results = session.execute(
                    text("""
                        SELECT * FROM messages 
                        WHERE channel = :channel 
                        ORDER BY created_at DESC 
                        LIMIT :limit
                    """),
                    {"channel": channel, "limit": limit}
                ).fetchall()
                
                return [
                    {
                        "message_id": row.message_id,
                        "agent_id": row.agent_id,
                        "channel": row.channel,
                        "message_type": row.message_type,
                        "content": row.content,
                        "metadata": json.loads(row.metadata) if row.metadata else {},
                        "thread_ts": row.thread_ts,
                        "created_at": row.created_at
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to retrieve recent messages: {e}")
            return []
    
    def store_activity(self, agent_id: str, activity_type: str, action: str, details: Dict[str, Any]) -> bool:
        """Store agent activity in the database.
        
        Args:
            agent_id: Agent identifier
            activity_type: Type of activity (slack, github, task, collaboration)
            action: Specific action performed
            details: Additional details about the activity
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                        INSERT INTO agent_activities 
                        (agent_id, activity_type, action, details, timestamp)
                        VALUES (:agent_id, :activity_type, :action, :details, :timestamp)
                    """),
                    {
                        "agent_id": agent_id,
                        "activity_type": activity_type,
                        "action": action,
                        "details": json.dumps(details),
                        "timestamp": datetime.utcnow()
                    }
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to store activity: {e}")
            return False
    
    def get_agent_activities(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent activities for an agent.
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of activities to retrieve
            
        Returns:
            List of activity dictionaries
        """
        try:
            with self.get_session() as session:
                results = session.execute(
                    text("""
                        SELECT * FROM agent_activities 
                        WHERE agent_id = :agent_id 
                        ORDER BY timestamp DESC 
                        LIMIT :limit
                    """),
                    {"agent_id": agent_id, "limit": limit}
                ).fetchall()
                
                return [
                    {
                        "activity_type": row.activity_type,
                        "action": row.action,
                        "details": json.loads(row.details) if row.details else {},
                        "timestamp": row.timestamp
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to retrieve agent activities: {e}")
            return []
    
    def store_task(self, task: TaskAssignment) -> bool:
        """Store a task assignment in the database.
        
        Args:
            task: Task assignment to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                        INSERT INTO tasks 
                        (task_id, title, description, assigned_agent, assigned_by, priority, status, 
                         estimated_duration, dependencies, acceptance_criteria, created_at, updated_at)
                        VALUES (:task_id, :title, :description, :assigned_agent, :assigned_by, :priority, :status,
                                :estimated_duration, :dependencies, :acceptance_criteria, :created_at, :updated_at)
                    """),
                    {
                        "task_id": task.task_id,
                        "title": task.title,
                        "description": task.description,
                        "assigned_agent": task.assigned_agent,
                        "assigned_by": task.assigned_by,
                        "priority": task.priority,
                        "status": task.status,
                        "estimated_duration": task.estimated_duration,
                        "dependencies": json.dumps(task.dependencies),
                        "acceptance_criteria": json.dumps(task.acceptance_criteria),
                        "created_at": task.created_at,
                        "updated_at": task.updated_at
                    }
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to store task: {e}")
            return False
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status.
        
        Args:
            task_id: Task identifier
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                session.execute(
                    text("""
                        UPDATE tasks 
                        SET status = :status, updated_at = :updated_at
                        WHERE task_id = :task_id
                    """),
                    {
                        "task_id": task_id,
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            return False
    
    def get_agent_tasks(self, agent_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks assigned to an agent.
        
        Args:
            agent_id: Agent identifier
            status: Filter by task status (optional)
            
        Returns:
            List of task dictionaries
        """
        try:
            with self.get_session() as session:
                query = """
                    SELECT * FROM tasks 
                    WHERE assigned_agent = :agent_id
                """
                params = {"agent_id": agent_id}
                
                if status:
                    query += " AND status = :status"
                    params["status"] = status
                
                query += " ORDER BY created_at DESC"
                
                results = session.execute(text(query), params).fetchall()
                
                return [
                    {
                        "task_id": row.task_id,
                        "title": row.title,
                        "description": row.description,
                        "assigned_agent": row.assigned_agent,
                        "assigned_by": row.assigned_by,
                        "priority": row.priority,
                        "status": row.status,
                        "estimated_duration": row.estimated_duration,
                        "dependencies": json.loads(row.dependencies) if row.dependencies else [],
                        "acceptance_criteria": json.loads(row.acceptance_criteria) if row.acceptance_criteria else [],
                        "created_at": row.created_at,
                        "updated_at": row.updated_at
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Failed to retrieve agent tasks: {e}")
            return []
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database.
        
        Args:
            backup_path: Path for the backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self.get_session() as session:
                stats = {}
                
                # Count agents
                result = session.execute(text("SELECT COUNT(*) as count FROM agents")).fetchone()
                stats["total_agents"] = result.count if result else 0
                
                # Count active agents
                result = session.execute(text("SELECT COUNT(*) as count FROM agents WHERE is_active = 1")).fetchone()
                stats["active_agents"] = result.count if result else 0
                
                # Count messages
                result = session.execute(text("SELECT COUNT(*) as count FROM messages")).fetchone()
                stats["total_messages"] = result.count if result else 0
                
                # Count tasks
                result = session.execute(text("SELECT COUNT(*) as count FROM tasks")).fetchone()
                stats["total_tasks"] = result.count if result else 0
                
                # Count activities
                result = session.execute(text("SELECT COUNT(*) as count FROM agent_activities")).fetchone()
                stats["total_activities"] = result.count if result else 0
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global database manager instance
db_manager = DatabaseManager() 