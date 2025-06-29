"""
Main agent runner for the multi-agent system.
"""
import os
import sys
import asyncio
import logging
import signal
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.models import AgentConfig, SystemConfig
from agents.base_agent import BaseAgent
from database.manager import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agents.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class AgentRunner:
    """Main agent runner that manages agent lifecycle."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the agent runner.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config: Optional[SystemConfig] = None
        self.agents: Dict[str, BaseAgent] = {}
        self.running = False
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load system configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            self.config = SystemConfig(**config_data)
            logger.info(f"Configuration loaded: {self.config.name} v{self.config.version}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent configuration
        """
        if not self.config:
            raise ValueError("Configuration not loaded")
            
        for agent_config in self.config.agents:
            if agent_config.name == agent_name:
                return agent_config
        
        raise ValueError(f"Agent configuration not found: {agent_name}")
    
    async def initialize_agent(self, agent_name: str) -> BaseAgent:
        """Initialize a single agent.
        
        Args:
            agent_name: Name of the agent to initialize
            
        Returns:
            Initialized agent instance
        """
        try:
            # Get agent configuration
            agent_config = self._get_agent_config(agent_name)
            
            # Create agent instance
            agent = BaseAgent(agent_config)
            
            # Initialize integrations
            slack_token = os.getenv("SLACK_BOT_TOKEN", "")
            slack_app_token = os.getenv("SLACK_APP_TOKEN", "")
            github_token = os.getenv("GITHUB_TOKEN", "")
            
            await agent.initialize_integrations(
                slack_token=slack_token,
                slack_app_token=slack_app_token,
                github_token=github_token
            )
            
            self.agents[agent_name] = agent
            logger.info(f"Agent initialized: {agent_name}")
            
            return agent
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {agent_name}: {e}")
            raise
    
    async def start_agent(self, agent_name: str):
        """Start a single agent.
        
        Args:
            agent_name: Name of the agent to start
        """
        try:
            if agent_name not in self.agents:
                await self.initialize_agent(agent_name)
            
            agent = self.agents[agent_name]
            
            # Send startup message to Slack
            if agent.slack_client and self.config and "default_channel" in self.config.slack:
                await agent.send_slack_message(
                    channel=self.config.slack["default_channel"],
                    message=f"🚀 {agent.name} is now online and ready to help with {agent.role.value} tasks!"
                )
            
            logger.info(f"Agent started: {agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_name}: {e}")
    
    async def stop_agent(self, agent_name: str):
        """Stop a single agent.
        
        Args:
            agent_name: Name of the agent to stop
        """
        try:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                
                # Send shutdown message to Slack
                if agent.slack_client and self.config and "default_channel" in self.config.slack:
                    await agent.send_slack_message(
                        channel=self.config.slack["default_channel"],
                        message=f"👋 {agent.name} is going offline. Goodbye!"
                    )
                
                # Shutdown agent
                await agent.shutdown()
                
                del self.agents[agent_name]
                logger.info(f"Agent stopped: {agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_name}: {e}")
    
    async def start_all_agents(self):
        """Start all configured agents."""
        try:
            logger.info("Starting all agents...")
            
            if not self.config:
                raise ValueError("Configuration not loaded")
                
            for agent_config in self.config.agents:
                if agent_config.name not in self.agents:
                    await self.start_agent(agent_config.name)
            
            self.running = True
            logger.info(f"All agents started: {list(self.agents.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to start all agents: {e}")
            raise
    
    async def stop_all_agents(self):
        """Stop all running agents."""
        try:
            logger.info("Stopping all agents...")
            
            for agent_name in list(self.agents.keys()):
                await self.stop_agent(agent_name)
            
            self.running = False
            logger.info("All agents stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop all agents: {e}")
    
    async def restart_agent(self, agent_name: str):
        """Restart a single agent.
        
        Args:
            agent_name: Name of the agent to restart
        """
        try:
            logger.info(f"Restarting agent: {agent_name}")
            
            await self.stop_agent(agent_name)
            await asyncio.sleep(2)  # Brief pause
            await self.start_agent(agent_name)
            
            logger.info(f"Agent restarted: {agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_name}: {e}")
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get status of a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent status dictionary
        """
        try:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                return agent.get_health_status()
            else:
                return {
                    "status": "not_running",
                    "agent_name": agent_name,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {
                "status": "error",
                "agent_name": agent_name,
                "error": str(e)
            }
    
    def get_all_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents.
        
        Returns:
            Dictionary with status of all agents
        """
        try:
            status = {}
            
            if not self.config:
                return status
                
            for agent_config in self.config.agents:
                status[agent_config.name] = self.get_agent_status(agent_config.name)
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting all agent status: {e}")
            return {}
    
    async def run_forever(self):
        """Run the agent system forever."""
        try:
            # Start all agents
            await self.start_all_agents()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.stop_all_agents()


def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    # The main loop will handle the shutdown


async def main():
    """Main entry point."""
    try:
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Get agent name from environment
        agent_name = os.getenv("AGENT_NAME")
        
        if agent_name:
            # Run single agent
            logger.info(f"Starting single agent: {agent_name}")
            runner = AgentRunner()
            await runner.start_agent(agent_name)
            
            # Keep running
            while True:
                await asyncio.sleep(1)
                
        else:
            # Run all agents
            logger.info("Starting all agents")
            runner = AgentRunner()
            await runner.run_forever()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Run the main function
    asyncio.run(main()) 