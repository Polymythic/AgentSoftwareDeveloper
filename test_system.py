#!/usr/bin/env python3
"""
Test script for the multi-agent system.
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


async def test_configuration():
    """Test configuration loading."""
    try:
        logger.info("Testing configuration loading...")
        
        from agents.main import AgentRunner
        
        runner = AgentRunner()
        
        if runner.config:
            logger.info(f"✅ Configuration loaded successfully: {runner.config.name} v{runner.config.version}")
            logger.info(f"   Found {len(runner.config.agents)} agents configured")
            
            for agent_config in runner.config.agents:
                logger.info(f"   - {agent_config.name} ({agent_config.role.value})")
            
            return True
        else:
            logger.error("❌ Failed to load configuration")
            return False
            
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False


async def test_database():
    """Test database initialization."""
    try:
        logger.info("Testing database initialization...")
        
        from database.manager import db_manager
        
        # Test database connection
        stats = db_manager.get_database_stats()
        logger.info(f"✅ Database initialized successfully")
        logger.info(f"   Stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False


async def test_agent_creation():
    """Test agent creation."""
    try:
        logger.info("Testing agent creation...")
        
        from shared.models import AgentConfig, AgentRole
        from agents.base_agent import BaseAgent
        
        # Create a test agent config
        test_config = AgentConfig(
            name="test-agent",
            model="gpt-4",
            personality="Test personality",
            job_description="Test job description",
            system_prompt="You are a test agent.",
            goal="Test goal",
            slack_username="test-bot",
            github_username="test-agent",
            docker_image="test:latest",
            role=AgentRole.BACKEND
        )
        
        # Create agent
        agent = BaseAgent(test_config)
        
        logger.info(f"✅ Agent created successfully: {agent.name}")
        logger.info(f"   Role: {agent.role.value}")
        logger.info(f"   Goal: {agent.goal}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent creation test failed: {e}")
        return False


async def test_integrations():
    """Test integration setup."""
    try:
        logger.info("Testing integration setup...")
        
        from shared.models import AgentConfig, AgentRole
        from agents.base_agent import BaseAgent
        
        # Create a test agent config
        test_config = AgentConfig(
            name="test-agent",
            model="gpt-4",
            personality="Test personality",
            job_description="Test job description",
            system_prompt="You are a test agent.",
            goal="Test goal",
            slack_username="test-bot",
            github_username="test-agent",
            docker_image="test:latest",
            role=AgentRole.BACKEND
        )
        
        # Create agent
        agent = BaseAgent(test_config)
        
        # Test integration initialization (without real tokens)
        await agent.initialize_integrations(
            slack_token="",
            slack_app_token="",
            github_token=""
        )
        
        logger.info("✅ Integration setup test completed")
        logger.info(f"   Slack client: {'✅' if agent.slack_client else '❌'}")
        logger.info(f"   GitHub client: {'✅' if agent.github_client else '❌'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False


async def test_api():
    """Test API endpoints."""
    try:
        logger.info("Testing API endpoints...")
        
        # This would test the FastAPI endpoints
        # For now, just check if the module can be imported
        from agents.api import app
        
        logger.info("✅ API module imported successfully")
        logger.info(f"   App title: {app.title}")
        logger.info(f"   App version: {app.version}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting multi-agent system tests...")
    
    tests = [
        ("Configuration", test_configuration),
        ("Database", test_database),
        ("Agent Creation", test_agent_creation),
        ("Integrations", test_integrations),
        ("API", test_api),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test_name} test...")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! The system is ready to use.")
        return 0
    else:
        logger.error("⚠️  Some tests failed. Please check the configuration and dependencies.")
        return 1


if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("database", exist_ok=True)
    
    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 