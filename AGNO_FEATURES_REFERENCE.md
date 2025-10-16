# Agno Framework Features Reference

This document provides a comprehensive reference of Agno framework capabilities for future feature implementation in the SQL Server Agent project.

## Table of Contents
1. [Sessions](#sessions)
2. [Memory](#memory)
3. [Session State](#session-state)
4. [Context Management](#context-management)
5. [Async Operations](#async-operations)
6. [Performance Optimization](#performance-optimization)
7. [Implementation Examples](#implementation-examples)

---

## Sessions

Sessions enable multi-turn conversations by persisting conversation history across agent runs.

### Basic Persistent Sessions

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    session_id="unique_session_id",
    add_history_to_context=True,
)
```

**Key Parameters:**
- `db`: Database instance for storing session data
- `session_id`: Unique identifier for the conversation
- `add_history_to_context`: Includes conversation history in context

### Session History Control

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    session_id="session_id",
    add_history_to_context=True,
    num_history_runs=10,  # Last 10 message exchanges
    read_chat_history=True,
)
```

**Parameters:**
- `num_history_runs`: Number of previous runs to include (default: all)
- `read_chat_history`: Enable reading chat history from database

### Session Summaries

For long conversations, session summaries help maintain context without overwhelming the model.

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    session_id="long_session",
    enable_session_summaries=True,
    add_session_summary_to_context=True,
)
```

**Benefits:**
- Reduces token usage for long conversations
- Maintains context across many interactions
- Automatically summarizes previous exchanges

### Multi-Session History Search

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    search_session_history=True,
    num_history_sessions=2,  # Search last 2 sessions
    num_history_runs=3,      # 3 runs per session
)
```

**Use Case:** Agent can reference previous sessions (e.g., "What did we discuss last week?")

### Session Caching

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    session_id="cached_session",
    cache_session=True,  # Cache in memory for faster access
)

# Access cached session
session = agent.get_session()
```

**Benefits:**
- Faster session retrieval
- Reduced database queries
- Better performance for high-frequency interactions

---

## Memory

Memory allows agents to learn and retain user-specific information across sessions.

### Types of Memory

1. **Automatic Memory** (Recommended)
   - Agent automatically creates/updates memories
   - Best for most use cases

2. **Agentic Memory**
   - Agent decides when to create memories
   - More control over what gets stored

### Enabling Automatic Memory

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="memories.db"),
    user_id="user_123",
    enable_user_memories=True,  # Enable automatic memory
)
```

### Custom Memory Configuration

```python
from agno.memory import MemoryManager

memory_manager = MemoryManager(
    model=OpenAIChat(id="gpt-4"),
    instructions=["Only store important user preferences"],
    privacy_rules=["Never store sensitive personal data"],
)

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="memories.db"),
    memory_manager=memory_manager,
)
```

### Memory Context Control

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="memories.db"),
    user_id="user_123",
    enable_user_memories=True,
    add_memories_to_context=False,  # Don't auto-add to context
)
```

### Retrieving Memories

```python
# Get all user memories
memories = agent.get_user_memories(user_id="user_123")

# Iterate through memories
for memory in memories:
    print(memory.memory)
```

### Multi-Agent Memory Sharing

```python
db = SqliteDb(db_file="shared_memories.db")

agent1 = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=db,
    user_id="user_123",
    enable_user_memories=True,
)

agent2 = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=db,  # Same database
    user_id="user_123",  # Same user
    enable_user_memories=True,
)
# Both agents share memories for user_123
```

---

## Session State

Session state allows storing custom data per session (like variables in a conversation).

### Basic Session State

```python
agent.print_response(
    "What is my name?",
    session_id="user_session",
    user_id="user_123",
    session_state={"user_name": "John", "age": 30},
)

# Later in the same session
agent.print_response(
    "How old am I?",
    session_id="user_session",
    user_id="user_123",
)
# Agent remembers age from session_state
```

### Dynamic Instructions from State

```python
def get_instructions(session_state):
    if session_state and session_state.get("user_name"):
        return f"Address the user as {session_state.get('user_name')}."
    return "Address the user politely."

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    instructions=get_instructions,
)
```

### Session State in Context

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    add_session_state_to_context=True,  # Add state to context
)
```

### Multiple Users with Session State

```python
# User 1
agent.print_response(
    "Add milk",
    session_id="user1_session",
    user_id="user1",
    session_state={"shopping_list": ["bread", "eggs"]},
)

# User 2 (different session)
agent.print_response(
    "Add apples",
    session_id="user2_session",
    user_id="user2",
    session_state={"shopping_list": ["bananas"]},
)
```

### Advanced State Management

```python
from agno.tools import tool

@tool
def add_to_list(item: str, session_state: dict) -> str:
    """Add item to shopping list."""
    if "shopping_list" not in session_state:
        session_state["shopping_list"] = []

    session_state["shopping_list"].append(item.lower())
    return f"Added {item} to list"

@tool
def get_list(session_state: dict) -> str:
    """Get shopping list."""
    items = session_state.get("shopping_list", [])
    return f"Your list: {', '.join(items)}" if items else "List is empty"

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    tools=[add_to_list, get_list],
)
```

---

## Context Management

### Adding Datetime to Context

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    add_datetime_to_context=True,
    timezone_identifier="America/New_York",
)
```

**Use Case:** Agent knows current date/time for queries like "What's today's date?"

### Static Instructions

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    instructions=[
        "You are a helpful SQL analyst.",
        "Always explain queries before executing.",
        "Use TOP clause for large datasets.",
    ],
)
```

### Dynamic Instructions

```python
def get_dynamic_instructions(session_state):
    user_role = session_state.get("role", "viewer")

    if user_role == "admin":
        return "You can perform any database operation."
    else:
        return "You can only read data, no modifications allowed."

agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    instructions=get_dynamic_instructions,
)
```

### Adding Custom Context

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    add_context_to_messages=True,
    additional_context="Database schema: users(id, name, email), orders(id, user_id, total)",
)
```

---

## Async Operations

For high-performance applications, use async methods.

### Basic Async Usage

```python
async def query_agent():
    response = await agent.arun("Tell me about sales data")
    print(response.content)

# Run async function
import asyncio
asyncio.run(query_agent())
```

### Async Print Response

```python
async def query_with_print():
    await agent.aprint_response("Analyze top customers")
```

### Async Pretty Print

```python
from agno.utils.pprint import apprint_run_response

async def query_with_pprint():
    response = await agent.arun("Show revenue trends")
    await apprint_run_response(response)
```

---

## Performance Optimization

### 1. Session Caching

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    cache_session=True,
)
```

### 2. Limit History

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    num_history_runs=5,  # Only last 5 exchanges
)
```

### 3. Session Summaries

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    enable_session_summaries=True,  # Compress long conversations
)
```

### 4. Disable Auto-Memory Context

```python
agent = Agent(
    model=OpenAIChat(id="gpt-4"),
    db=SqliteDb(db_file="sessions.db"),
    enable_user_memories=True,
    add_memories_to_context=False,  # Don't add automatically
)
```

---

## Implementation Examples

### Example 1: SQL Agent with Sessions

```python
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from agno.tools.sql import SQLTools

def create_sql_agent(session_id: str, user_id: str):
    return Agent(
        name="SQL Analyst",
        model=OpenAIChat(id="gpt-4"),
        db=SqliteDb(db_file="sql_sessions.db"),
        tools=[SQLTools(db_url="mssql+pyodbc://...")],
        session_id=session_id,
        user_id=user_id,
        add_history_to_context=True,
        num_history_runs=10,
        add_datetime_to_context=True,
        instructions=[
            "You are an expert SQL analyst.",
            "Remember previous queries in this session.",
            "For follow-up questions, reference earlier results.",
        ],
    )
```

### Example 2: Multi-User Support

```python
def handle_user_query(user_id: str, query: str):
    agent = Agent(
        model=OpenAIChat(id="gpt-4"),
        db=SqliteDb(db_file="sessions.db"),
        user_id=user_id,
        session_id=f"{user_id}_session",
        add_history_to_context=True,
        enable_user_memories=True,
    )

    return agent.run(query)
```

### Example 3: State-Based Workflow

```python
def create_stateful_agent():
    return Agent(
        model=OpenAIChat(id="gpt-4"),
        db=SqliteDb(db_file="sessions.db"),
        add_session_state_to_context=True,
        session_state={"workflow_step": "initial"},
    )

# Update state during conversation
response = agent.run(
    "Start analysis",
    session_state={"workflow_step": "analyzing"},
)
```

---

## Database Options

### SQLite (Recommended for Development)

```python
from agno.db.sqlite import SqliteDb

db = SqliteDb(db_file="agno.db")
```

### PostgreSQL (Recommended for Production)

```python
from agno.db.postgres import PostgresDb

db = PostgresDb(
    db_url="postgresql+psycopg://user:pass@localhost:5432/dbname",
    session_table="sessions",
    memory_table="memories",
)
```

### In-Memory (Testing Only)

```python
from agno.db.inmemory import InMemoryDb

db = InMemoryDb()
```

---

## Best Practices

1. **Always use a persistent database for production**
   - SQLite for single-user/low-traffic
   - PostgreSQL for multi-user/high-traffic

2. **Set reasonable history limits**
   - Use `num_history_runs` to prevent context overflow
   - Consider session summaries for long conversations

3. **Use session_id consistently**
   - Generate unique IDs per conversation
   - Keep same ID for follow-up queries

4. **Enable datetime context for time-aware queries**
   - Useful for "today", "this week", etc.

5. **Use session state for workflow management**
   - Track conversation flow
   - Store temporary data

6. **Consider async operations for APIs**
   - Better performance
   - Non-blocking I/O

7. **Memory vs Session History**
   - Memory: Long-term user preferences/facts
   - Session History: Conversation context
   - Use both for best experience

8. **Cache sessions for frequent access**
   - Reduces database load
   - Improves response time

---

## Future Feature Ideas

### High Priority
- [ ] Add session management to CLI (unique session per CLI run)
- [ ] Add session_id support to MCP API endpoint
- [ ] Enable conversation history (last 10 exchanges)
- [ ] Add datetime context awareness

### Medium Priority
- [ ] Implement user memories for personalization
- [ ] Add session summaries for long conversations
- [ ] Multi-user session support in API
- [ ] Session state for workflow tracking

### Low Priority
- [ ] Session caching for performance
- [ ] Cross-session history search
- [ ] Advanced memory management
- [ ] Async API endpoints

---

## Quick Reference: Common Patterns

### Pattern 1: Basic Session
```python
agent = Agent(
    model=model,
    db=SqliteDb(db_file="sessions.db"),
    session_id="unique_id",
    add_history_to_context=True,
)
```

### Pattern 2: With User Memories
```python
agent = Agent(
    model=model,
    db=SqliteDb(db_file="sessions.db"),
    session_id="unique_id",
    user_id="user_123",
    add_history_to_context=True,
    enable_user_memories=True,
)
```

### Pattern 3: Stateful Agent
```python
agent = Agent(
    model=model,
    db=SqliteDb(db_file="sessions.db"),
    session_id="unique_id",
    add_session_state_to_context=True,
    session_state={"key": "value"},
)
```

### Pattern 4: Performance Optimized
```python
agent = Agent(
    model=model,
    db=SqliteDb(db_file="sessions.db"),
    session_id="unique_id",
    add_history_to_context=True,
    num_history_runs=5,
    cache_session=True,
    enable_session_summaries=True,
)
```

---

## Resources

- [Agno Documentation](https://docs.agno.com/)
- [Agno GitHub](https://github.com/agno-agi/agno)
- [Agno Examples](https://github.com/agno-agi/agno/tree/main/cookbook/examples)
