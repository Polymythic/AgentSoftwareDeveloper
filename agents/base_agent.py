"""
Base agent class for the multi-agent system.
"""
import os
import logging
import asyncio
import uuid
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

import openai
from pydantic import BaseModel

from shared.models import (
    AgentConfig, AgentState, MessageType, SlackMessage, 
    GitHubCommit, GitHubPR, CollaborationRequest, TaskAssignment
)
from database.manager import db_manager
from integrations.slack_client import SlackClient
from integrations.github_client import GitHubClient

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the base agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.name = config.name
        self.role = config.role
        self.model = config.model
        self.personality = config.personality
        self.job_description = config.job_description
        self.system_prompt = config.system_prompt
        self.goal = config.goal
        
        # Initialize state
        self.state = AgentState(
            agent_id=self.agent_id,
            agent_name=self.name,
            current_task=None,
            task_status="idle",
            context_window=[],
            last_activity=datetime.utcnow(),
            memory={},
            collaboration_history=[],
            github_activity=[],
            slack_activity=[]
        )
        
        # Initialize clients
        self.slack_client = None
        self.github_client = None
        
        # Initialize AI client
        self._setup_ai_client()
        
        # Load state from database
        self._load_state()
        
        logger.info(f"Initialized agent: {self.name} ({self.role.value})")
    
    def _setup_ai_client(self):
        """Set up the AI client based on the configured model."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OpenAI API key not found, AI functionality will be limited")
                return
            
            openai.api_key = api_key
            
            # Test the connection
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            logger.info(f"AI client initialized with model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {e}")
    
    def _load_state(self):
        """Load agent state from database."""
        try:
            stored_state = db_manager.get_agent_state(self.agent_id)
            if stored_state:
                self.state = stored_state
                logger.info(f"Loaded state for agent {self.name}")
            else:
                # Store initial state
                db_manager.store_agent_state(self.agent_id, self.state)
                logger.info(f"Created initial state for agent {self.name}")
                
        except Exception as e:
            logger.error(f"Failed to load agent state: {e}")
    
    def _save_state(self):
        """Save agent state to database."""
        try:
            self.state.last_activity = datetime.utcnow()
            db_manager.store_agent_state(self.agent_id, self.state)
        except Exception as e:
            logger.error(f"Failed to save agent state: {e}")
    
    def _add_to_context(self, content: Dict[str, Any]):
        """Add content to the agent's context window.
        
        Args:
            content: Content to add to context
        """
        self.state.context_window.append({
            "timestamp": datetime.utcnow().isoformat(),
            "content": content
        })
        
        # Limit context window size (keep last 50 items)
        if len(self.state.context_window) > 50:
            self.state.context_window = self.state.context_window[-50:]
        
        self._save_state()
    
    def _get_context_summary(self) -> str:
        """Get a summary of the agent's context window.
        
        Returns:
            Context summary as string
        """
        if not self.state.context_window:
            return "No recent context available."
        
        # Get the last 10 items for summary
        recent_context = self.state.context_window[-10:]
        
        summary_parts = []
        for item in recent_context:
            timestamp = item["timestamp"]
            content = item["content"]
            
            if isinstance(content, dict):
                content_type = content.get("type", "unknown")
                content_summary = content.get("summary", str(content))
                summary_parts.append(f"[{timestamp}] {content_type}: {content_summary}")
            else:
                summary_parts.append(f"[{timestamp}] {content}")
        
        return "\n".join(summary_parts)
    
    async def initialize_integrations(self, slack_token: str, slack_app_token: str, 
                                    github_token: str):
        """Initialize Slack and GitHub integrations.
        
        Args:
            slack_token: Slack bot token
            slack_app_token: Slack app token
            github_token: GitHub personal access token
        """
        try:
            # Initialize Slack client
            if slack_token and slack_app_token:
                self.slack_client = SlackClient(
                    bot_token=slack_token,
                    app_token=slack_app_token,
                    agent_name=self.name
                )
                await self.slack_client.start()
                logger.info(f"Slack integration initialized for {self.name}")
            
            # Initialize GitHub client
            if github_token:
                self.github_client = GitHubClient(
                    token=github_token,
                    agent_name=self.name,
                    agent_role=self.role
                )
                logger.info(f"GitHub integration initialized for {self.name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize integrations: {e}")
    
    async def process_message(self, message: str, channel: str, 
                            sender: str, message_type: MessageType = MessageType.STATUS_UPDATE) -> str:
        """Process an incoming message and generate a response.
        
        Args:
            message: Message content
            channel: Channel where message was received
            sender: Sender of the message
            message_type: Type of message
            
        Returns:
            Response message
        """
        try:
            # Add message to context
            self._add_to_context({
                "type": "incoming_message",
                "channel": channel,
                "sender": sender,
                "message": message,
                "message_type": message_type.value
            })
            
            # Generate response using AI
            response = await self._generate_response(message, message_type)
            
            # Add response to context
            self._add_to_context({
                "type": "outgoing_message",
                "channel": channel,
                "response": response,
                "message_type": message_type.value
            })
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_id,
                activity_type="slack",
                action="message_processed",
                details={
                    "channel": channel,
                    "sender": sender,
                    "message": message[:100],  # Truncate for logging
                    "response": response[:100],  # Truncate for logging
                    "message_type": message_type.value
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error processing your message: {str(e)}"
    
    async def _generate_response(self, message: str, message_type: MessageType) -> str:
        """Generate a response using the AI model.
        
        Args:
            message: Input message
            message_type: Type of message
            
        Returns:
            Generated response
        """
        try:
            # Prepare the prompt
            context_summary = self._get_context_summary()
            
            prompt = f"""
You are {self.name}, a {self.role.value} agent with the following characteristics:

Personality: {self.personality}
Job Description: {self.job_description}
Goal: {self.goal}

Current Context:
{context_summary}

Message Type: {message_type.value}
Incoming Message: {message}

Please respond appropriately based on your role and the message type. Be helpful, professional, and true to your personality.

Response:
"""
            
            # Generate response using OpenAI
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"I'm having trouble processing your request right now. Please try again later."
    
    async def send_slack_message(self, channel: str, message: str, 
                               thread_ts: Optional[str] = None) -> bool:
        """Send a message to Slack.
        
        Args:
            channel: Channel to send message to
            message: Message content
            thread_ts: Thread timestamp for replies
            
        Returns:
            True if successful, False otherwise
        """
        if not self.slack_client:
            logger.warning("Slack client not initialized")
            return False
        
        try:
            success = self.slack_client.send_message(channel, message, thread_ts)
            
            if success:
                # Add to context
                self._add_to_context({
                    "type": "slack_message_sent",
                    "channel": channel,
                    "message": message,
                    "thread_ts": thread_ts
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return False
    
    async def create_github_commit(self, repo_name: str, branch: str, 
                                 files: List[Dict[str, Any]], message: str) -> bool:
        """Create a commit on GitHub.
        
        Args:
            repo_name: Repository name
            branch: Branch name
            files: List of files to commit
            message: Commit message
            
        Returns:
            True if successful, False otherwise
        """
        if not self.github_client:
            logger.warning("GitHub client not initialized")
            return False
        
        try:
            repo = self.github_client.get_repository(repo_name)
            if not repo:
                return False
            
            # Create or update files
            for file_info in files:
                path = file_info["path"]
                content = file_info["content"]
                action = file_info.get("action", "create")
                
                if action == "create":
                    success = self.github_client.create_file(repo, path, content, message, branch)
                elif action == "update":
                    success = self.github_client.update_file(repo, path, content, message, branch)
                elif action == "delete":
                    success = self.github_client.delete_file(repo, path, message, branch)
                else:
                    logger.warning(f"Unknown file action: {action}")
                    continue
                
                if not success:
                    logger.error(f"Failed to {action} file {path}")
                    return False
            
            # Add to context
            self._add_to_context({
                "type": "github_commit",
                "repository": repo_name,
                "branch": branch,
                "message": message,
                "files": [f["path"] for f in files]
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating GitHub commit: {e}")
            return False
    
    async def create_pull_request(self, repo_name: str, title: str, body: str,
                                head_branch: str, base_branch: str = "main",
                                reviewers: Optional[List[str]] = None) -> Optional[str]:
        """Create a pull request on GitHub.
        
        Args:
            repo_name: Repository name
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch
            reviewers: List of reviewer usernames
            
        Returns:
            PR URL if successful, None otherwise
        """
        if not self.github_client:
            logger.warning("GitHub client not initialized")
            return None
        
        try:
            repo = self.github_client.get_repository(repo_name)
            if not repo:
                return None
            
            pr = self.github_client.create_pull_request(
                repo=repo,
                title=title,
                body=body,
                head_branch=head_branch,
                base_branch=base_branch,
                reviewers=reviewers
            )
            
            if pr:
                # Add to context
                self._add_to_context({
                    "type": "github_pr_created",
                    "repository": repo_name,
                    "pr_number": pr.number,
                    "title": title,
                    "url": pr.html_url
                })
                
                return pr.html_url
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return None
    
    async def review_pull_request(self, repo_name: str, pr_number: int,
                                body: str, event: str = "COMMENT") -> bool:
        """Review a pull request.
        
        Args:
            repo_name: Repository name
            pr_number: Pull request number
            body: Review body
            event: Review event
            
        Returns:
            True if successful, False otherwise
        """
        if not self.github_client:
            logger.warning("GitHub client not initialized")
            return False
        
        try:
            repo = self.github_client.get_repository(repo_name)
            if not repo:
                return False
            
            success = self.github_client.review_pull_request(
                repo=repo,
                pr_number=pr_number,
                body=body,
                event=event
            )
            
            if success:
                # Add to context
                self._add_to_context({
                    "type": "github_pr_reviewed",
                    "repository": repo_name,
                    "pr_number": pr_number,
                    "event": event
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Error reviewing pull request: {e}")
            return False
    
    async def assign_task(self, task: TaskAssignment) -> bool:
        """Assign a task to this agent.
        
        Args:
            task: Task assignment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store task in database
            success = db_manager.store_task(task)
            
            if success:
                # Update agent state
                self.state.current_task = task.task_id
                self.state.task_status = "working"
                self._save_state()
                
                # Add to context
                self._add_to_context({
                    "type": "task_assigned",
                    "task_id": task.task_id,
                    "title": task.title,
                    "description": task.description,
                    "priority": task.priority
                })
                
                logger.info(f"Task assigned to {self.name}: {task.title}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            return False
    
    async def complete_task(self, task_id: str, result: str) -> bool:
        """Mark a task as completed.
        
        Args:
            task_id: Task identifier
            result: Task completion result
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update task status
            success = db_manager.update_task_status(task_id, "completed")
            
            if success:
                # Update agent state
                if self.state.current_task == task_id:
                    self.state.current_task = None
                    self.state.task_status = "idle"
                    self._save_state()
                
                # Add to context
                self._add_to_context({
                    "type": "task_completed",
                    "task_id": task_id,
                    "result": result
                })
                
                logger.info(f"Task completed by {self.name}: {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return False
    
    async def request_collaboration(self, target_agent: str, request_type: MessageType,
                                  description: str, priority: str = "medium") -> bool:
        """Request collaboration with another agent.
        
        Args:
            target_agent: Target agent name
            request_type: Type of collaboration request
            description: Description of the collaboration needed
            priority: Priority level
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create collaboration request
            request = CollaborationRequest(
                requester_id=self.agent_id,
                target_agent_id=target_agent,
                request_type=request_type,
                description=description,
                priority=priority,
                timestamp=datetime.utcnow()
            )
            
            # Store in database
            success = db_manager.store_activity(
                agent_id=self.agent_id,
                activity_type="collaboration",
                action="request_sent",
                details={
                    "target_agent": target_agent,
                    "request_type": request_type.value,
                    "description": description,
                    "priority": priority
                }
            )
            
            if success:
                # Add to context
                self._add_to_context({
                    "type": "collaboration_requested",
                    "target_agent": target_agent,
                    "request_type": request_type.value,
                    "description": description
                })
                
                logger.info(f"Collaboration requested by {self.name} to {target_agent}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error requesting collaboration: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get the agent's health status.
        
        Returns:
            Health status dictionary
        """
        try:
            import psutil
            
            return {
                "status": "healthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time() - self.state.last_activity.timestamp(),
                "memory_usage": {
                    "rss": psutil.Process().memory_info().rss,
                    "vms": psutil.Process().memory_info().vms
                },
                "active_tasks": 1 if self.state.current_task else 0,
                "last_activity": self.state.last_activity.isoformat(),
                "context_window_size": len(self.state.context_window),
                "integrations": {
                    "slack": self.slack_client is not None,
                    "github": self.github_client is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                "status": "error",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def shutdown(self):
        """Shutdown the agent gracefully."""
        try:
            # Stop Slack client
            if self.slack_client:
                self.slack_client.stop()
            
            # Save final state
            self._save_state()
            
            logger.info(f"Agent {self.name} shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during agent shutdown: {e}") 