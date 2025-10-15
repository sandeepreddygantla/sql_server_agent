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

        return AzureOpenAI(
            id=os.getenv("AZURE_MODEL_ID", "gpt-4.1"),
            azure_deployment=os.getenv("AZURE_DEPLOYMENT", "gpt-4.1_2025-04-14"),
            api_version=os.getenv("AZURE_API_VERSION", "2025-01-01-preview"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT", "https://api.uhg.com/api/cloud/api-management/ai-gateway/1.0"),
            azure_ad_token=get_access_token(),
            default_headers={"projectId": project_id}
        )

    else:
        raise ValueError(f"Unsupported MODEL_PROVIDER: {provider}. Supported: openai, azure")


class SQLAgentManager:
    """Manages SQL agent with automatic token refresh for Azure."""

    def __init__(self, db_url: str = None):
        self.db_url = db_url
        self.provider = os.getenv("MODEL_PROVIDER", "openai").lower()
        self.token_expiry = None
        self.agent = None
        self._create_agent()

    def _create_agent(self):
        """Create or recreate the agent."""
        if self.db_url is None:
            host = os.getenv("SQLSERVER_HOST")
            database = os.getenv("SQLSERVER_DATABASE")
            trusted = os.getenv("SQLSERVER_TRUSTED_CONNECTION", "yes")

            if trusted.lower() == "yes":
                db_url = f"mssql+pyodbc://{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
            else:
                username = os.getenv("SQLSERVER_USERNAME")
                password = os.getenv("SQLSERVER_PASSWORD")
                db_url = f"mssql+pyodbc://{username}:{password}@{host}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        else:
            db_url = self.db_url

        sql_tools = SQLTools(db_url=db_url)
        model = get_model()

        self.agent = Agent(
            name="Assistant",
            model=model,
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

        if self.provider == "azure":
            self.token_expiry = datetime.now() + timedelta(hours=1)

        logger.info(f"SQL Server Agent created with {self.provider} provider")

    def _refresh_if_needed(self):
        """Check token expiry and refresh if needed."""
        if self.provider != "azure" or self.token_expiry is None:
            return

        if datetime.now() >= self.token_expiry - timedelta(minutes=5):
            logger.info("Refreshing Azure access token...")
            self._create_agent()
            logger.info("Token refreshed successfully")

    @property
    def name(self):
        """Get agent name."""
        return self.agent.name

    def print_response(self, message: str, **kwargs):
        """Print agent response with automatic token refresh."""
        self._refresh_if_needed()
        return self.agent.print_response(message, **kwargs)

    def run(self, message: str, **kwargs):
        """Run agent with automatic token refresh."""
        self._refresh_if_needed()
        return self.agent.run(message, **kwargs)


def sql_agent(db_url: str = None):
    """
    Create SQL Server Analysis Agent with automatic token refresh.

    Returns SQLAgentManager that handles token refresh automatically.
    """
    return SQLAgentManager(db_url=db_url)


if __name__ == "__main__":
    agent = sql_agent()
    agent.print_response("Show me all available tables in the database", markdown=True)
