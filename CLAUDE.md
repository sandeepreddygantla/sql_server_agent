# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SQL Server Agent is a natural language interface for SQL Server database analysis. It uses the Agno framework to create an AI agent that can understand natural language queries and execute SQL operations on SQL Server databases.

The project has two main interfaces:
1. **CLI Mode** (`cli.py`): Interactive command-line interface for direct user queries
2. **MCP Server** (`src/mcp/server.py`): FastAPI REST API server exposing agent functionality via HTTP endpoints

## Code Modification Guidelines

**CRITICAL - Read Before Making Changes**:

1. **Modify existing functions, don't create new ones**: When updating functionality, always modify the existing function directly. Do NOT create backup functions or new functions alongside old ones.

2. **Why this matters**: Creating new functions while keeping old ones causes code breaks. If you create a new function but other parts of the codebase still call the old function, your changes won't take effect. This creates fragmented logic and bugs.

3. **Write human code, not AI code**: Code should read naturally. Other developers should not be able to tell it was AI-generated. Avoid overly verbose comments, unnecessary abstractions, or patterns that scream "AI wrote this."

4. **Only create new functions when absolutely necessary**: New functions are acceptable only when adding genuinely new capabilities, not when refactoring or fixing existing behavior.

## Architecture

### Core Components

**Agent Layer** (`src/agent/sql_agent.py`):
- Creates an Agno Agent configured with SQLTools for database operations
- Supports both OpenAI (for development) and Azure OpenAI (for production deployment)
- Agent is read-only by design - instructions explicitly forbid UPDATE/DELETE/INSERT operations
- Uses streaming responses by default for better UX
- Constructs SQL Server connection strings from environment variables, supporting both Windows Authentication (trusted connection) and SQL Server Authentication

**MCP Server** (`src/mcp/server.py`):
- FastAPI application exposing `/query`, `/health`, and root endpoints
- Initializes a single global `sql_agent` instance on startup
- POST `/query` accepts `{"query": "natural language question"}` and returns agent response
- Runs on port 8000 by default with auto-reload enabled

**CLI Interface** (`cli.py`):
- Simple REPL loop for interactive queries
- Uses `agent.print_response()` with markdown formatting
- Exit with 'exit', 'quit', or 'q'

### Environment Configuration

The agent reads configuration from `.env`:

**Database Connection**:
- `SQLSERVER_HOST`: SQL Server host and port (e.g., `localhost,1433`)
- `SQLSERVER_DATABASE`: Database name
- `SQLSERVER_TRUSTED_CONNECTION`: Set to `yes` for Windows Auth, `no` for SQL Auth
- `SQLSERVER_USERNAME`, `SQLSERVER_PASSWORD`: Required when using SQL Auth

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

### Model Configuration Strategy

The codebase uses environment-driven model configuration for easy switching:

**Development (WSL)**: Set `MODEL_PROVIDER=openai` in `.env`
- Uses OpenAI API with API key authentication
- No code changes needed when moving to organization

**Organization Deployment**: Set `MODEL_PROVIDER=azure` in `.env`
- Uses Azure OpenAI with AD token authentication
- Azure AD token retrieved via OAuth2 client credentials flow
- Requires `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_PROJECT_ID`, etc.
- Tokens automatically refresh every hour (before 5-minute expiry threshold)

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
uv run cli.py

# Or using the virtual environment Python directly
.venv\Scripts\python.exe cli.py
```

### Running the Application

**CLI Mode**:
```bash
uv run cli.py
# or
.venv\Scripts\python.exe cli.py
```

**MCP Server**:
```bash
uv run src/mcp/server.py
# or
.venv\Scripts\python.exe src/mcp/server.py
```

**Test Agent Directly**:
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

The agent is configured with specific instructions in `sql_agent.py:76-82`:
- Expert SQL Server analyst persona
- Must explain queries before execution
- Use LIMIT/TOP for large datasets
- Provide actionable insights
- **Read-only operations only** (critical safety constraint)

### Path Resolution

Both `sql_agent.py` and `server.py` include path manipulation to ensure proper imports:
```python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```
This allows running scripts from their directories while maintaining package structure.

### Logging

Uses Agno's built-in logger:
```python
from agno.utils.log import logger
```
Logging level set to INFO via `logging.basicConfig(level=logging.INFO)`

### Response Streaming

Agent is configured with `stream=True` for better responsiveness during long-running queries. CLI uses `agent.print_response()` which handles streaming automatically. MCP server uses `stream=False` in `agent.run()` to return complete responses via HTTP.

### Automatic Token Refresh

`SQLAgentManager` class (`sql_agent.py:82-158`) wraps the agent and handles Azure AD token refresh:
- Tracks token expiry time (1 hour from creation)
- Checks token before each query via `_refresh_if_needed()`
- Refreshes 5 minutes before expiry
- Recreates agent with fresh token automatically
- Only active for Azure provider (OpenAI doesn't need token refresh)
- `sql_agent()` function returns `SQLAgentManager` instance for transparent token management

## Deployment Considerations

**Switching Between Environments**:

WSL Development → Organization:
1. Change `MODEL_PROVIDER=openai` to `MODEL_PROVIDER=azure` in `.env`
2. Set Azure credentials: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
3. Set Azure config: `AZURE_PROJECT_ID`, `AZURE_DEPLOYMENT`, `AZURE_ENDPOINT`
4. Agent will automatically handle token refresh every hour

**Adding New Model Providers**:
1. Add new provider logic in `get_model()` function (`sql_agent.py:30-62`)
2. Add new elif block for the provider
3. Configure environment variables in `.env`
4. Update `MODEL_PROVIDER` to use the new provider

**Security**:
- Never commit `.env` file (should be in `.gitignore`)
- Agent is read-only by design, but validate user permissions at database level
- MCP server runs on `0.0.0.0` - restrict access in production environments
- Azure AD token in `get_access_token()` is critical for organization deployment
