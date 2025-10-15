import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agno.utils.log import logger
from agno.agent import Agent
from agno.tools.sql import SQLTools
from agno.models.openai import OpenAIChat
# from agno.models.azure import AzureOpenAI  # Uncomment for Azure deployment
import httpx
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("Please set OPENAI_API_KEY environment variable")

project_id = "openai-meeting-processor"  # Simple project ID for personal use
tiktoken_cache_dir = os.path.abspath("tiktoken_cache")
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir

# --- Dummy Auth Function (for compatibility) ---
def get_access_token():
    """
    Dummy function to maintain compatibility with existing code.
    OpenAI API uses API key authentication, not tokens.
    """
    return "dummy_token_for_compatibility"

access_token = get_access_token()


def sql_agent(db_url: str = None) -> Agent:
    """
    Create SQL Server Analysis Agent (No Memory)

    Args:
        db_url: SQLAlchemy database URL (e.g., "mssql+pyodbc://...")

    Returns:
        Configured Agno Agent with SQL Server tools
    """
    if db_url is None:
        from dotenv import load_dotenv
        load_dotenv()

        host = os.getenv("SQLSERVER_HOST", "localhost,1433")
        database = os.getenv("SQLSERVER_DATABASE")
        trusted = os.getenv("SQLSERVER_TRUSTED_CONNECTION", "yes")

        if trusted.lower() == "yes":
            db_url = f"mssql+pyodbc://{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        else:
            username = os.getenv("SQLSERVER_USERNAME")
            password = os.getenv("SQLSERVER_PASSWORD")
            db_url = f"mssql+pyodbc://{username}:{password}@{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server"

    # Create SQL Tools using Agno's built-in SQLTools
    sql_tools = SQLTools(db_url=db_url)

    # Create the Agent with OpenAI model and SQL tools (for local testing)
    # When deploying to organization, comment out OpenAI section and uncomment Azure section
    
    # === OpenAI Configuration (Local Testing) ===
    agent = Agent(
        name="Assistant",
        model=OpenAIChat(
            id="gpt-4",
            api_key=openai_api_key
        ),
        tools=[sql_tools],
        instructions=[
            "You are an expert SQL Server database analyst.",
            "Always explain your SQL queries before executing them.",
            "For large datasets, use LIMIT or TOP clause to restrict results.",
            "Provide clear insights and actionable recommendations.",
            "Focus on read-only analysis – never suggest UPDATE, DELETE, or INSERT operations.",
        ],
        markdown=True,
        stream=True
    )
    
    # === Azure Configuration (Organization Deployment) ===
    # Uncomment this section and comment out OpenAI section above when deploying
    # agent = Agent(
    #     name="Assistant",
    #     model=AzureOpenAI(
    #         id="gpt-4.1",
    #         azure_deployment="gpt-4.1_2025-04-14",
    #         api_version="2025-01-01-preview",
    #         azure_endpoint="https://api.uhg.com/api/cloud/api-management/ai-gateway/1.0",
    #         azure_ad_token=access_token,
    #         default_headers={
    #             "projectId": os.getenv("AZURE_PROJECT_ID")
    #         }
    #     ),
    #     tools=[sql_tools],
    #     instructions=[
    #         "You are an expert SQL Server database analyst.",
    #         "Always explain your SQL queries before executing them.",
    #         "For large datasets, use LIMIT or TOP clause to restrict results.",
    #         "Provide clear insights and actionable recommendations.",
    #         "Focus on read-only analysis – never suggest UPDATE, DELETE, or INSERT operations.",
    #     ],
    #     markdown=True,
    #     stream=True
    # )

    logger.info("SQL Server Agent created")
    return agent


if __name__ == "__main__":
    agent = sql_agent()
    agent.print_response("Show me all available tables in the database", markdown=True)
