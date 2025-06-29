#!/usr/bin/env python3
"""
Startup script for the multi-agent system.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    try:
        # Check if we should run the API server
        run_api = os.getenv("RUN_API", "false").lower() == "true"
        
        if run_api:
            logger.info("Starting API server...")
            from agents.api import app
            import uvicorn
            
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
        else:
            logger.info("Starting agent system...")
            from agents.main import main as run_agents
            await run_agents()
            
    except Exception as e:
        logger.error(f"Error in startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("database", exist_ok=True)
    
    # Run the main function
    asyncio.run(main()) 