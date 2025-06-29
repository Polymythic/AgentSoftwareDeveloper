"""
Slack integration client for the multi-agent system.
"""
import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from shared.models import SlackMessage, MessageType
from database.manager import db_manager

logger = logging.getLogger(__name__)


class SlackClient:
    """Slack client for agent communication."""
    
    def __init__(self, bot_token: str, app_token: str, agent_name: str):
        """Initialize the Slack client.
        
        Args:
            bot_token: Slack bot token
            app_token: Slack app token
            agent_name: Name of the agent using this client
        """
        self.bot_token = bot_token
        self.app_token = app_token
        self.agent_name = agent_name
        self.client = WebClient(token=bot_token)
        self.app = App(token=bot_token)
        self.handler = None
        self.is_connected = False
        
        # Set up message handlers
        self._setup_message_handlers()
    
    def _setup_message_handlers(self):
        """Set up message event handlers."""
        
        @self.app.message(".*")
        def handle_message(message, say, logger):
            """Handle incoming messages."""
            try:
                # Ignore messages from bots to prevent loops
                if message.get("bot_id"):
                    return
                
                # Process the message
                self._process_incoming_message(message)
                
            except Exception as e:
                logger.error(f"Error handling message: {e}")
        
        @self.app.event("app_mention")
        def handle_mention(event, say, logger):
            """Handle app mentions."""
            try:
                # Process the mention
                self._process_mention(event, say)
                
            except Exception as e:
                logger.error(f"Error handling mention: {e}")
    
    def _process_incoming_message(self, message: Dict[str, Any]):
        """Process incoming messages.
        
        Args:
            message: Slack message object
        """
        try:
            # Extract message details
            channel = message.get("channel")
            text = message.get("text", "")
            user = message.get("user")
            timestamp = message.get("ts")
            thread_ts = message.get("thread_ts")
            
            # Determine message type
            message_type = self._determine_message_type(text)
            
            # Store message in database
            db_message = {
                "message_id": f"{channel}_{timestamp}",
                "agent_id": self.agent_name,
                "channel": channel,
                "message_type": message_type.value,
                "content": text,
                "metadata": {
                    "user": user,
                    "timestamp": timestamp,
                    "thread_ts": thread_ts
                },
                "thread_ts": thread_ts,
                "is_processed": False,
                "created_at": datetime.utcnow()
            }
            
            # Store in database
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="slack",
                action="message_received",
                details={
                    "channel": channel,
                    "text": text[:100],  # Truncate for logging
                    "user": user,
                    "message_type": message_type.value
                }
            )
            
            logger.info(f"Processed incoming message from {user} in {channel}")
            
        except Exception as e:
            logger.error(f"Error processing incoming message: {e}")
    
    def _process_mention(self, event: Dict[str, Any], say):
        """Process app mentions.
        
        Args:
            event: Slack event object
            say: Slack say function
        """
        try:
            text = event.get("text", "")
            channel = event.get("channel")
            user = event.get("user")
            
            # Remove the bot mention from the text
            mention_text = text.replace(f"<@{self.client.auth_test()['user_id']}>", "").strip()
            
            # Handle the mention based on content
            response = self._handle_mention_content(mention_text, user)
            
            # Send response
            say(text=response, thread_ts=event.get("ts"))
            
            # Log activity
            db_manager.store_activity(
                agent_id=self.agent_name,
                activity_type="slack",
                action="mention_handled",
                details={
                    "channel": channel,
                    "user": user,
                    "mention_text": mention_text,
                    "response": response[:100]  # Truncate for logging
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing mention: {e}")
            say(text="Sorry, I encountered an error processing your request.", thread_ts=event.get("ts"))
    
    def _handle_mention_content(self, text: str, user: str) -> str:
        """Handle mention content and generate response.
        
        Args:
            text: Mention text content
            user: User who mentioned the bot
            
        Returns:
            Response text
        """
        text_lower = text.lower()
        
        if "status" in text_lower or "how are you" in text_lower:
            return f"Hello! I'm {self.agent_name} and I'm currently active and ready to help with software development tasks."
        
        elif "help" in text_lower:
            return f"I'm {self.agent_name}, a software development agent. I can help with coding, code reviews, architecture discussions, and collaboration. What would you like to work on?"
        
        elif "task" in text_lower:
            return "I can help you with task management. Would you like me to create a new task, review existing tasks, or help with task prioritization?"
        
        elif "collaborate" in text_lower or "work together" in text_lower:
            return "I'd be happy to collaborate! I can work with other agents on code reviews, architecture discussions, debugging, or any other development tasks."
        
        else:
            return f"Thanks for mentioning me! I'm {self.agent_name} and I'm here to help with software development. You can ask me about my status, request help, or ask me to collaborate on tasks."
    
    def _determine_message_type(self, text: str) -> MessageType:
        """Determine the type of message based on content.
        
        Args:
            text: Message text
            
        Returns:
            Message type
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["review", "code review", "pr review"]):
            return MessageType.CODE_REVIEW
        
        elif any(word in text_lower for word in ["task", "assign", "work on"]):
            return MessageType.TASK_ASSIGNMENT
        
        elif any(word in text_lower for word in ["status", "update", "progress"]):
            return MessageType.STATUS_UPDATE
        
        elif any(word in text_lower for word in ["help", "collaborate", "work together"]):
            return MessageType.COLLABORATION_REQUEST
        
        elif any(word in text_lower for word in ["bug", "debug", "error", "issue"]):
            return MessageType.DEBUGGING_REQUEST
        
        elif any(word in text_lower for word in ["architecture", "design", "structure"]):
            return MessageType.ARCHITECTURE_DISCUSSION
        
        else:
            return MessageType.STATUS_UPDATE
    
    async def start(self):
        """Start the Slack client."""
        try:
            self.handler = SocketModeHandler(self.app, self.app_token)
            await self.handler.start_async()
            self.is_connected = True
            logger.info(f"Slack client started for {self.agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to start Slack client: {e}")
            raise
    
    def stop(self):
        """Stop the Slack client."""
        try:
            if self.handler:
                self.handler.close()
            self.is_connected = False
            logger.info(f"Slack client stopped for {self.agent_name}")
            
        except Exception as e:
            logger.error(f"Error stopping Slack client: {e}")
    
    def send_message(self, channel: str, text: str, thread_ts: Optional[str] = None, 
                    attachments: Optional[List[Dict[str, Any]]] = None,
                    blocks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Send a message to a Slack channel.
        
        Args:
            channel: Channel ID or name
            text: Message text
            thread_ts: Thread timestamp for replies
            attachments: Message attachments
            blocks: Message blocks
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare message parameters
            params = {
                "channel": channel,
                "text": text
            }
            
            if thread_ts:
                params["thread_ts"] = thread_ts
            
            if attachments:
                params["attachments"] = attachments
            
            if blocks:
                params["blocks"] = blocks
            
            # Send message
            response = self.client.chat_postMessage(**params)
            
            if response["ok"]:
                # Store message in database
                db_manager.store_activity(
                    agent_id=self.agent_name,
                    activity_type="slack",
                    action="message_sent",
                    details={
                        "channel": channel,
                        "text": text[:100],  # Truncate for logging
                        "thread_ts": thread_ts,
                        "ts": response.get("ts")
                    }
                )
                
                logger.info(f"Message sent to {channel}")
                return True
            else:
                logger.error(f"Failed to send message: {response.get('error')}")
                return False
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_direct_message(self, user_id: str, text: str, **kwargs) -> bool:
        """Send a direct message to a user.
        
        Args:
            user_id: User ID
            text: Message text
            **kwargs: Additional message parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open DM channel
            response = self.client.conversations_open(users=[user_id])
            
            if response["ok"]:
                channel_id = response["channel"]["id"]
                return self.send_message(channel_id, text, **kwargs)
            else:
                logger.error(f"Failed to open DM channel: {response.get('error')}")
                return False
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending DM: {e}")
            return False
    
    def get_channel_info(self, channel: str) -> Optional[Dict[str, Any]]:
        """Get information about a channel.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            Channel information or None if not found
        """
        try:
            response = self.client.conversations_info(channel=channel)
            
            if response["ok"]:
                return response["channel"]
            else:
                logger.error(f"Failed to get channel info: {response.get('error')}")
                return None
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return None
        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            return None
    
    def get_channel_members(self, channel: str) -> List[str]:
        """Get list of channel members.
        
        Args:
            channel: Channel ID or name
            
        Returns:
            List of user IDs
        """
        try:
            response = self.client.conversations_members(channel=channel)
            
            if response["ok"]:
                return response["members"]
            else:
                logger.error(f"Failed to get channel members: {response.get('error')}")
                return []
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return []
        except Exception as e:
            logger.error(f"Error getting channel members: {e}")
            return []
    
    def create_channel(self, name: str, is_private: bool = False) -> Optional[str]:
        """Create a new Slack channel.
        
        Args:
            name: Channel name
            is_private: Whether the channel should be private
            
        Returns:
            Channel ID if successful, None otherwise
        """
        try:
            params = {"name": name}
            
            if is_private:
                params["is_private"] = True
            
            response = self.client.conversations_create(**params)
            
            if response["ok"]:
                channel_id = response["channel"]["id"]
                logger.info(f"Created channel {name} with ID {channel_id}")
                return channel_id
            else:
                logger.error(f"Failed to create channel: {response.get('error')}")
                return None
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return None
        except Exception as e:
            logger.error(f"Error creating channel: {e}")
            return None
    
    def invite_to_channel(self, channel: str, users: List[str]) -> bool:
        """Invite users to a channel.
        
        Args:
            channel: Channel ID
            users: List of user IDs to invite
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.client.conversations_invite(
                channel=channel,
                users=",".join(users)
            )
            
            if response["ok"]:
                logger.info(f"Invited users to channel {channel}")
                return True
            else:
                logger.error(f"Failed to invite users: {response.get('error')}")
                return False
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error inviting users: {e}")
            return False 