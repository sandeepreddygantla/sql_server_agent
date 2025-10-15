import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from agno.utils.log import logger
from src.agent.sql_agent import sql_agent


# Request/Response models
class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    response: str


# Initialize the SQL Server Agent
sql_agent = sql_agent()

# Create FastAPI app
app = FastAPI(
    title="SQL Server MCP",
    description="SQL Server analysis agent with natural language queries",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "SQL Server Analysis MCP",
        "version": "1.0.0",
        "description": "Simple SQL Server analysis agent",
        "endpoints": {
            "query": "POST /query – Execute natural language query",
            "health": "GET /health – Health check",
            "docs": "GET /docs – API documentation"
        }
    }


@app.post("/query", response_model=QueryResponse)
async def execute_query(request: QueryRequest):
    """
    Execute natural language query on SQL Server

    Args:
        request: QueryRequest with natural language query

    Returns:
        Agent response with analysis results
    """
    try:
        response = sql_agent.run(request.query, stream=False)

        return QueryResponse(
            response=response.content if hasattr(response, 'content') else str(response)
        )

    except Exception as e:
        logger.error(f"Error in query endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": sql_agent.name
    }


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🚀 SQL Server MCP Server starting...")
    logger.info(f"Agent: {sql_agent.name}")
    logger.info("API docs available at: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down SQL Server MCP Server...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.mcp.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
