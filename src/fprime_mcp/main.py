"""Main FastAPI application with MCP server integration."""

import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from fprime_mcp.config import Settings, get_settings
from fprime_mcp.auth import auth_router, FPrimeMember
from fprime_mcp.auth.session import get_session_manager
from fprime_mcp.auth.oidc import get_oidc_provider
from fprime_mcp.tools import get_tool_registry
from fprime_mcp.mcp_server import get_mcp_server

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

    # Initialize components
    settings = get_settings()
    tool_registry = get_tool_registry()
    mcp = get_mcp_server()

    logger.info(f"Registered {len(tool_registry.list_tools())} tools")
    logger.info(f"Server environment: {settings.server_env}")

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
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#