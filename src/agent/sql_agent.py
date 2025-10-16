import os
import sys
import logging
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agno.utils.log import logger
from agno.agent import Agent
from agno.tools.sql import SQLTools
from agno.models.openai import OpenAIChat
from agno.models.azure import AzureOpenAI
from agno.db.sqlite import SqliteDb
import httpx
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tiktoken_cache_dir = os.path.abspath("tiktoken_cache")
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir

def get_access_token():
    """Get Azure AD access token using client credentials flow."""
    provider = os.getenv("MODEL_PROVIDER", "openai").lower()

    if provider != "azure":
        return "dummy_token_for_compatibility"

    auth = "https://api.uhg.com/oauth2/token"
    scope = "https://api.uhg.com/.default"
    grant_type = "client_credentials"
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    with httpx.Client() as client:
        body = {
            "grant_type": grant_type,
            "scope": scope,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = client.post(auth, headers=headers, data=body, timeout=60)
        response.raise_for_status()
        return response.json()["access_token"]


class AutoRefreshAzureOpenAI(AzureOpenAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_expiry = datetime.now() + timedelta(hours=1)
        logger.info(f"Azure model created, token expires at {self.token_expiry.strftime('%H:%M:%S')}")

    def _refresh_token_if_needed(self):
        now = datetime.now()
        if now >= self.token_expiry - timedelta(minutes=5):
            logger.info("Token expiring soon, refreshing...")
            self.azure_ad_token = get_access_token()
            self.token_expiry = now + timedelta(hours=1)
            logger.info(f"Token refreshed, expires at {self.token_expiry.strftime('%H:%M:%S')}")

    def invoke(self, *args, **kwargs):
        self._refresh_token_if_needed()
        return super().invoke(*args, **kwargs)


def get_model():
    """
    Get the AI model based on MODEL_PROVIDER environment variable.
    Switch between providers by changing MODEL_PROVIDER in .env
    """
    provider = os.getenv("MODEL_PROVIDER", "openai").lower()

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when MODEL_PROVIDER=openai")

        return OpenAIChat(
            id=os.getenv("OPENAI_MODEL_ID", "gpt-4"),
            api_key=api_key
        )

    elif provider == "azure":
        project_id = os.getenv("AZURE_PROJECT_ID")
        if not project_id:
            raise ValueError("AZURE_PROJECT_ID is required when MODEL_PROVIDER=azure")

        return AutoRefreshAzureOpenAI(
            id=os.getenv("AZURE_MODEL_ID", "gpt-4.1"),
            azure_deployment=os.getenv("AZURE_DEPLOYMENT", "gpt-4.1_2025-04-14"),
            api_version=os.getenv("AZURE_API_VERSION", "2025-01-01-preview"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT", "https://api.uhg.com/api/cloud/api-management/ai-gateway/1.0"),
            azure_ad_token=get_access_token(),
            default_headers={"projectId": project_id}
        )

    else:
        raise ValueError(f"Unsupported MODEL_PROVIDER: {provider}. Supported: openai, azure")


def _build_db_url(db_url=None):
    """Build SQL Server connection string from environment variables."""
    if db_url is not None:
        return db_url

    host = os.getenv("SQLSERVER_HOST")
    database = os.getenv("SQLSERVER_DATABASE")
    trusted = os.getenv("SQLSERVER_TRUSTED_CONNECTION", "yes")

    if trusted.lower() == "yes":
        return f"mssql+pyodbc://{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    else:
        username = os.getenv("SQLSERVER_USERNAME")
        password = os.getenv("SQLSERVER_PASSWORD")
        return f"mssql+pyodbc://{username}:{password}@{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server"


def create_sql_agent(db_url=None):
    """
    Create SQL Server Analysis Agent for AgentOS.

    This agent is created once at server startup and serves multiple users.
    User ID and session ID are provided per request by AgentOS.

    Note: For Azure deployments, the server should be restarted every ~55 minutes
    to refresh expired tokens, or use OpenAI which has no token expiry.

    Args:
        db_url: Optional SQL Server database URL

    Returns:
        Configured Agent instance for AgentOS
    """
    db_url = _build_db_url(db_url)
    sql_tools = SQLTools(db_url=db_url)
    model = get_model()
    session_db_file = os.getenv("SESSION_DB_FILE", "agno_sessions.db")
    session_db = SqliteDb(db_file=session_db_file)

    agent = Agent(
        name="SQL Assistant",
        model=model,
        db=session_db,
        add_history_to_context=True,
        num_history_runs=10,
        add_datetime_to_context=True,
        tools=[sql_tools],
        instructions=[
            "You are an expert SQL Server database analyst.",
            "Always explain your SQL queries before executing them.",
            "For large datasets, use LIMIT or TOP clause to restrict results.",
            "Provide clear insights and actionable recommendations.",
            "Focus on read-only analysis – never suggest UPDATE, DELETE, or INSERT operations.",
        ],
        markdown=True,
    )

    logger.info(f"SQL Server Agent created for AgentOS with {os.getenv('MODEL_PROVIDER', 'openai')} provider")
    return agent


if __name__ == "__main__":
    agent = create_sql_agent()
    agent.print_response("Show me all available tables in the database", markdown=True)
