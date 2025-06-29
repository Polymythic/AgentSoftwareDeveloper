# Multi-Agent System Setup Guide

This guide will help you set up and deploy the multi-agent software development system.

## Prerequisites

- **Python 3.9+**
- **Docker and Docker Compose**
- **Git**
- **Slack Workspace** (for agent communication)
- **GitHub Account** (for code collaboration)
- **OpenAI API Key** (for AI model access)

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd AgentSoftwareDeveloper
```

### 2. Set Up Environment Variables

Copy the example environment file and configure your tokens:

```bash
cp env.example .env
```

Edit `.env` with your actual tokens:

```bash
# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-actual-slack-bot-token
SLACK_APP_TOKEN=xapp-your-actual-slack-app-token

# GitHub Integration
GITHUB_TOKEN=ghp-your-actual-github-token
GITHUB_REPO=your-username/your-repository

# OpenAI Integration
OPENAI_API_KEY=sk-your-actual-openai-api-key

# Security
JWT_SECRET=your-secure-jwt-secret
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Test the System

Run the test script to verify everything is working:

```bash
python test_system.py
```

### 5. Start the System

#### Option A: Run All Agents
```bash
python start.py
```

#### Option B: Run Specific Agent
```bash
AGENT_NAME=code-architect python start.py
```

#### Option C: Run API Server
```bash
RUN_API=true python start.py
```

## Docker Deployment

### 1. Build and Run with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### 2. Individual Agent Containers

```bash
# Build the image
docker build -t multi-agent:latest .

# Run a specific agent
docker run -d \
  --name code-architect-agent \
  -e AGENT_NAME=code-architect \
  -e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/database:/app/database \
  -v $(pwd)/logs:/app/logs \
  multi-agent:latest
```

## Slack Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Multi-Agent System")
4. Select your workspace

### 2. Configure Bot Token Scopes

Add these OAuth scopes:
- `channels:read`
- `channels:write`
- `chat:write`
- `chat:write.public`
- `groups:read`
- `groups:write`
- `im:read`
- `im:write`
- `mpim:read`
- `mpim:write`

### 3. Install App to Workspace

1. Go to "OAuth & Permissions"
2. Click "Install to Workspace"
3. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

### 4. Enable Socket Mode

1. Go to "Socket Mode"
2. Enable Socket Mode
3. Create an app-level token (starts with `xapp-`)

### 5. Create Channels

Create these channels in your Slack workspace:
- `#agent-collaboration` - General agent communication
- `#code-reviews` - Code review discussions
- `#task-assignment` - Task distribution
- `#debugging` - Debugging discussions

## GitHub Setup

### 1. Create Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token" → "Fine-grained tokens"
3. Set permissions:
   - Repository access: "All repositories" or specific repos
   - Repository permissions:
     - Contents: "Read and write"
     - Pull requests: "Read and write"
     - Issues: "Read and write"
     - Metadata: "Read-only"

### 2. Configure Repository

Ensure your repository has:
- Proper branch protection rules
- Required status checks for PRs
- Code review requirements

## Configuration

### Agent Configuration

Edit `config.yaml` to customize your agents:

```yaml
agents:
  - name: "code-architect"
    model: "gpt-4"
    personality: "Analytical and strategic..."
    job_description: "Senior software architect..."
    system_prompt: "You are a senior software architect..."
    goal: "Create robust, scalable architectures..."
    slack_username: "architect-bot"
    github_username: "code-architect-agent"
    role: "architect"
```

### Adding New Agents

1. Add agent configuration to `config.yaml`
2. Create agent-specific logic in `agents/` directory (optional)
3. Update `docker-compose.yml` if using Docker

### Customizing Agent Personalities

Each agent can have unique:
- **Personality**: Behavioral traits and communication style
- **Job Description**: Role and responsibilities
- **System Prompt**: Core instructions for the AI model
- **Goal**: Primary objective and success criteria

## Monitoring and Management

### API Endpoints

The system provides REST API endpoints:

- `GET /health` - System health check
- `GET /agents` - List all agents
- `GET /agents/{name}` - Get agent details
- `POST /agents/{name}/start` - Start agent
- `POST /agents/{name}/stop` - Stop agent
- `POST /tasks` - Create new task
- `POST /collaboration` - Request collaboration
- `GET /metrics` - Prometheus metrics

### Monitoring Dashboards

- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3000` (admin/admin)

### Logs

- Application logs: `logs/agents.log`
- Docker logs: `docker-compose logs -f`

## Troubleshooting

### Common Issues

1. **Slack Connection Failed**
   - Verify bot token and app token
   - Check Socket Mode is enabled
   - Ensure bot is invited to channels

2. **GitHub API Errors**
   - Verify personal access token
   - Check repository permissions
   - Ensure repository exists and is accessible

3. **OpenAI API Errors**
   - Verify API key is valid
   - Check API quota and billing
   - Ensure model name is correct

4. **Database Errors**
   - Check database file permissions
   - Verify SQLite is working
   - Check disk space

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python start.py
```

### Health Checks

Check system health:

```bash
curl http://localhost:8000/health
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` files
2. **API Keys**: Rotate tokens regularly
3. **Network Security**: Use VPN for production deployments
4. **Access Control**: Implement proper authentication for API endpoints
5. **Data Privacy**: Ensure compliance with data protection regulations

## Production Deployment

### Recommended Setup

1. **Load Balancer**: Use nginx or similar
2. **Database**: Consider PostgreSQL for production
3. **Monitoring**: Set up alerting and dashboards
4. **Backup**: Regular database and configuration backups
5. **SSL/TLS**: Enable HTTPS for all communications

### Scaling

- Run multiple instances of each agent
- Use Kubernetes for orchestration
- Implement proper service discovery
- Set up horizontal pod autoscaling

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Test individual components
4. Create an issue in the repository

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 