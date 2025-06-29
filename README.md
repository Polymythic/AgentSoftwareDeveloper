# Multi-Agent Software Development System

A Docker-based multi-agent system for collaborative software development with Slack communication, SQLite state management, and GitHub integration.

## Features

- **Multi-Agent Architecture**: Deploy multiple agents with distinct personalities and roles
- **Slack Integration**: Agents communicate and collaborate through Slack channels
- **State Management**: SQLite database for persistent agent state and context
- **GitHub Integration**: Agents can commit code and review PRs as separate entities
- **Configurable Agents**: YAML-based configuration for agent personalities, models, and goals
- **Docker Deployment**: Easy containerization and scaling of agents

## Architecture

```
├── agents/                 # Agent implementations
├── config/                 # Agent configuration files
├── database/              # SQLite database and schemas
├── docker/                # Docker configuration
├── integrations/          # Slack and GitHub integrations
├── shared/                # Shared utilities and models
└── config.yaml           # Main configuration file
```

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd AgentSoftwareDeveloper
   ```

2. **Configure agents**:
   - Edit `config.yaml` to define your agents
   - Set up Slack bot tokens and GitHub tokens

3. **Deploy with Docker**:
   ```bash
   docker-compose up -d
   ```

4. **Monitor agents**:
   - Check Slack channels for agent communication
   - Monitor GitHub for commits and PRs
   - View logs: `docker-compose logs -f`

## Configuration

Each agent is configured via `config.yaml` with:
- **name**: Agent identifier
- **model**: AI model to use (e.g., gpt-4, claude-3)
- **personality**: Agent's behavioral traits
- **job_description**: Role and responsibilities
- **system_prompt**: Core instructions
- **goal**: Primary objective

## Agent Communication

Agents communicate through:
- **Slack channels** for real-time collaboration
- **SQLite database** for state persistence
- **GitHub** for code collaboration and version control

## Development

- **Python 3.9+** required
- **Docker** for containerization
- **Slack API** for communication
- **GitHub API** for repository management
