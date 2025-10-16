# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SQL Server Agent is a natural language interface for SQL Server database analysis. It uses the Agno framework to create an AI agent that can understand natural language queries and execute SQL operations on SQL Server databases.

**AgentOS** (`agent_os.py`) is the single interface:
- Production-ready agent server with web UI and 50+ API endpoints
- Handles multi-user sessions automatically
- Web interface at `http://localhost:7777`
- REST API with automatic documentation at `http://localhost:7777/docs`

## Code Modification Guidelines

**CRITICAL - Read Before Making Changes**:

1. **Modify existing functions, don't create new ones**: When updating functionality, always modify the existing function directly. Do NOT create backup functions or new functions alongside old ones.

2. **Why this matters**: Creating new functions while keeping old ones causes code breaks. If you create a new function but other parts of the codebase still call the old function, your changes won't take effect. This creates fragmented logic and bugs.

3. **Write human code, not AI code**: Code should read naturally. Other developers should not be able to tell it was AI-generated. Avoid overly verbose comments, unnecessary abstractions, or patterns that scream "AI wrote this."

4. **Only create new functions when absolutely necessary**: New functions are acceptable only when adding genuinely new capabilities, not when refactoring or fixing existing behavior.

## Architecture

### Core Components

**Agent Layer** (`src/agent/sql_agent.py`):
- Single function `create_sql_agent()` creates the Agno Agent
- Configured with SQLTools for SQL Server database operations
- Supports both OpenAI (for development) and Azure OpenAI (for production deployment)
- Agent is read-only by design - instructions explicitly forbid UPDATE/DELETE/INSERT operations
- Constructs SQL Server connection strings from environment variables
- Supports both Windows Authentication (trusted connection) and SQL Server Authentication

**AgentOS** (`agent_os.py`):
- Production-ready Agno OS runtime serving the SQL agent
- Provides 50+ built-in API endpoints for agent interaction, sessions, memories, knowledge
- Web UI at `http://localhost:7777` for agent management and chat
- Primary endpoint: `POST /agents/sql-assistant/runs` (form-encoded)
- Automatic multi-user session management
- Built-in monitoring, logging, and API documentation at `/docs`
- Runs on port 7777 by default (configurable via `AGNO_OS_PORT`)
- Optional bearer-token authentication via `OS_SECURITY_KEY` environment variable

### Environment Configuration

The agent reads configuration from `.env`:

**Database Connection**:
- `SQLSERVER_HOST`: SQL Server host and port (e.g., `localhost,1433`)
- `SQLSERVER_DATABASE`: Database name
- `SQLSERVER_TRUSTED_CONNECTION`: Set to `yes` for Windows Auth, `no` for SQL Auth
- `SQLSERVER_USERNAME`, `SQLSERVER_PASSWORD`: Required when using SQL Auth

**Session Storage**:
- `SESSION_DB_FILE`: SQLite database file for sessions (defaults to `agno_sessions.db`)

**Model Provider**:
- `MODEL_PROVIDER`: Set to `openai` or `azure` (defaults to `openai`)

**OpenAI Configuration** (when `MODEL_PROVIDER=openai`):
- `OPENAI_API_KEY`: Required
- `OPENAI_MODEL_ID`: Optional (defaults to `gpt-4`)

**Azure Configuration** (when `MODEL_PROVIDER=azure`):
- `AZURE_CLIENT_ID`: Required (for token authentication)
- `AZURE_CLIENT_SECRET`: Required (for token authentication)
- `AZURE_PROJECT_ID`: Required
- `AZURE_MODEL_ID`: Optional (defaults to `gpt-4.1`)
- `AZURE_DEPLOYMENT`: Optional (defaults to `gpt-4.1_2025-04-14`)
- `AZURE_API_VERSION`: Optional (defaults to `2025-01-01-preview`)
- `AZURE_ENDPOINT`: Optional (defaults to organization endpoint)

**AgentOS Configuration**:
- `AGNO_OS_PORT`: Port for AgentOS server (defaults to 7777)
- `OS_SECURITY_KEY`: Optional bearer token for API authentication (auto-detected by AgentOS)

### Model Configuration Strategy

The codebase uses environment-driven model configuration for easy switching:

**Development (WSL)**: Set `MODEL_PROVIDER=openai` in `.env`
- Uses OpenAI API with API key authentication
- No code changes needed when moving to organization

**Organization Deployment**: Set `MODEL_PROVIDER=azure` in `.env`
- Uses Azure OpenAI with AD token authentication
- Azure AD token retrieved via OAuth2 client credentials flow
- Requires `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_PROJECT_ID`, etc.
- **Token Limitation**: Azure tokens expire after 1 hour. AgentOS creates the agent once at startup, so for Azure deployments, restart the server every ~55 minutes or use OpenAI (no expiry).

**Adding New Providers**: Update `get_model()` function in `sql_agent.py:47-79` to add support for other model providers

## Development Commands

### Package Manager

This project uses **uv** as the package manager, not pip.

**Activating virtual environment**:
```bash
.venv\Scripts\activate
```

**Running Python files**:
```bash
# Using uv run
uv run agent_os.py

# Or using the virtual environment Python directly
.venv\Scripts\python.exe agent_os.py
```

### Running the Application

**Start AgentOS Server**:
```bash
uv run agent_os.py
# or
.venv\Scripts\python.exe agent_os.py
```

**Access the Application**:
- Web UI: `http://localhost:7777`
- API docs: `http://localhost:7777/docs`
- Primary API endpoint: `POST http://localhost:7777/agents/sql-assistant/runs`

**Test Agent Directly** (for debugging):
```bash
uv run src/agent/sql_agent.py
# Runs a test query: "Show me all available tables in the database"
```

### Dependencies

Install dependencies using uv:
```bash
uv sync
```

Key dependencies:
- `agno`: AI agent framework providing Agent, SQLTools, and model integrations
- `pyodbc`: SQL Server connectivity (requires ODBC Driver 17 for SQL Server)
- `SQLAlchemy`: Database abstraction layer
- `fastapi`, `uvicorn`: REST API server
- `openai`: OpenAI API client

### Database Prerequisites

SQL Server ODBC Driver must be installed:
- Windows: ODBC Driver 17 for SQL Server (typically pre-installed)
- Linux: Install via package manager (e.g., `msodbcsql17`)

Connection strings are auto-constructed using the format:
```
mssql+pyodbc://{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

## Key Implementation Details

### Agno Agent Instructions

The agent is configured with specific instructions in `sql_agent.py:129-135`:
- Expert SQL Server analyst persona
- Must explain queries before execution
- Use LIMIT/TOP for large datasets
- Provide actionable insights
- **Read-only operations only** (critical safety constraint)

### Path Resolution

`sql_agent.py` includes path manipulation to ensure proper imports:
```python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```
This allows running the script directly while maintaining the package structure.

### Logging

Uses Agno's built-in logger:
```python
from agno.utils.log import logger
```
Logging level set to INFO via `logging.basicConfig(level=logging.INFO)`

### Azure Token Management

Azure AD tokens expire after 1 hour. The current implementation:
- Fetches a new token at agent creation via `get_access_token()` (sql_agent.py:21-44)
- AgentOS creates the agent once at startup
- For production Azure deployments, restart the server every ~55 minutes
- Alternative: Use OpenAI provider which has no token expiry

### Session Management

AgentOS handles multi-user conversation sessions automatically:
- Each user has unique `user_id` (provided per API request)
- Each conversation has unique `session_id` (provided per API request)
- Sessions stored in SQLite database (`agno_sessions.db`)
- Last 10 message exchanges included in context automatically
- Users can ask follow-up questions referencing previous queries
- Sessions isolated per user - no data leakage between users
- Datetime automatically added to context for time-aware queries

### AgentOS API Usage

**Run Agent with Natural Language Query**:
```bash
curl -X POST 'http://localhost:7777/agents/sql-assistant/runs' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'message=Show me all tables in the database' \
  -d 'user_id=john' \
  -d 'session_id=john_session_1' \
  -d 'stream=false'
```

**With Authentication** (if `OS_SECURITY_KEY` is set):
```bash
curl -X POST 'http://localhost:7777/agents/sql-assistant/runs' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'Authorization: Bearer YOUR_SECURITY_KEY' \
  -d 'message=Analyze sales data' \
  -d 'user_id=mary' \
  -d 'session_id=mary_session_1'
```

**Follow-up Query** (use same session_id):
```bash
curl -X POST 'http://localhost:7777/agents/sql-assistant/runs' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'message=What about last month?' \
  -d 'user_id=john' \
  -d 'session_id=john_session_1'
```

**Additional AgentOS Endpoints**:
- View all sessions: `GET /sessions`
- View session history: `GET /sessions/{session_id}`
- Manage memories: `GET/POST /memories`
- Full API documentation: `http://localhost:7777/docs`

## Deployment Considerations

**Switching Between Environments**:

WSL Development → Organization:
1. Change `MODEL_PROVIDER=openai` to `MODEL_PROVIDER=azure` in `.env`
2. Set Azure credentials: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
3. Set Azure config: `AZURE_PROJECT_ID`, `AZURE_DEPLOYMENT`, `AZURE_ENDPOINT`
4. **Important**: Restart AgentOS server every ~55 minutes to refresh Azure tokens

**Azure Token Expiry Handling**:
- Azure AD tokens expire after 1 hour
- AgentOS creates the agent once at startup with a fresh token
- For production: Use container orchestrator (Docker/Kubernetes) with health checks to restart every ~55 minutes
- Alternative: Use OpenAI provider (no token expiry) for production

**Adding New Model Providers**:
1. Add new provider logic in `get_model()` function (`sql_agent.py:47-79`)
2. Add new elif block for the provider
3. Configure environment variables in `.env`
4. Update `MODEL_PROVIDER` to use the new provider

**Security**:
- Never commit `.env` file (should be in `.gitignore`)
- Agent is read-only by design, but validate user permissions at database level
- AgentOS server runs on `0.0.0.0` - restrict access in production environments
- Azure AD token in `get_access_token()` is critical for organization deployment
- Use `OS_SECURITY_KEY` for API bearer-token authentication in production
