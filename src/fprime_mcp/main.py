"""Main FastAPI application for F-Prime MCP Server."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fprime_mcp.auth.routes import router as auth_router
from fprime_mcp.auth.oidc_config import get_oidc_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting F-Prime MCP Server...")
    
    # Validate OIDC config on startup
    try:
        config = get_oidc_config()
        logger.info(f"OIDC configured for tenant: {config.tenant_id}")
        logger.info(f"Redirect URI: {config.redirect_uri}")
    except Exception as e:
        logger.error(f"Failed to load OIDC config: {e}")
        raise
    
    yield
    
    logger.info("Shutting down F-Prime MCP Server...")


# Create FastAPI application
app = FastAPI(
    title="F-Prime MCP Server",
    description="MCP Server for F-Prime internal tools with Microsoft Entra ID authentication",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "https://claude.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)


# =============================================================================
# Health and Status Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fprime-mcp-server"}


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "F-Prime MCP Server",
        "version": "0.1.0",
        "auth_required": True,
        "login_url": "/auth/login",
        "docs_url": "/docs",
    }


# =============================================================================
# Protected MCP Endpoints (require authentication)
# =============================================================================

async def get_current_user(request: Request) -> dict:
    """Get current user from session cookie."""
    import httpx
    from fprime_mcp.auth.oidc_config import get_oidc_config
    
    token = request.cookies.get("mcp_session")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    config = get_oidc_config()
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            config.userinfo_endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
            )
        
        return resp.json()


@app.get("/mcp/tools")
async def list_mcp_tools(request: Request):
    """List available MCP tools (requires authentication)."""
    user = await get_current_user(request)
    
    # Example tools - replace with your actual tool definitions
    tools = [
        {
            "name": "fprime_search_projects",
            "description": "Search F-Prime projects by name, status, or team",
        },
        {
            "name": "fprime_get_document", 
            "description": "Retrieve an F-Prime internal document by ID",
        },
        {
            "name": "fprime_team_directory",
            "description": "Look up F-Prime team members and contact info",
        },
    ]
    
    return {
        "user": user.get("email"),
        "tools": tools,
    }


@app.post("/mcp/tools/call")
async def call_mcp_tool(request: Request):
    """Call an MCP tool (requires authentication)."""
    user = await get_current_user(request)
    body = await request.json()
    
    tool_name = body.get("name")
    arguments = body.get("arguments", {})
    
    logger.info(f"User {user.get('email')} calling tool: {tool_name}")
    
    # Example tool implementation - replace with your actual tools
    if tool_name == "fprime_search_projects":
        result = {
            "query": arguments.get("query", ""),
            "results": [{"id": "proj-001", "name": "Sample Project"}],
        }
    elif tool_name == "fprime_get_document":
        result = {
            "id": arguments.get("document_id", "unknown"),
            "title": "Sample Document",
            "content": "Document content here...",
        }
    elif tool_name == "fprime_team_directory":
        result = {
            "members": [{"name": "Jane Smith", "email": "jane@fprime.com"}],
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tool: {tool_name}",
        )
    
    return {
        "content": [{"type": "text", "text": str(result)}],
        "is_error": False,
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


# =============================================================================
# Run with Uvicorn
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fprime_mcp.main:app", host="0.0.0.0", port=8000, reload=True)