import os
from dotenv import load_dotenv
from agno.os import AgentOS
from src.agent.sql_agent import create_sql_agent

load_dotenv()

sql_assistant = create_sql_agent()

agent_os = AgentOS(
    id="sql-server-agent-os",
    description="SQL Server analysis agent with natural language queries",
    agents=[sql_assistant],
)

app = agent_os.get_app()

if __name__ == "__main__":
    port = int(os.getenv("AGNO_OS_PORT", 7777))
    agent_os.serve(app="agent_os:app", host="0.0.0.0", port=port, reload=True)
