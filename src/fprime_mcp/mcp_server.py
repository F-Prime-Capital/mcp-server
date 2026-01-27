"""FastMCP server implementation for F-Prime."""

import logging
from typing import Any
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from pydantic import BaseModel

from fprime_mcp.tools.registry import get_tool_registry
from fprime_mcp.auth.models import UserSession

logger = logging.getLogger(__name__)


class MCPContext(BaseModel):
    """Context passed to MCP tool handlers."""
    user: UserSession | None = None


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server."""

    mcp = FastMCP(
        name="fprime-mcp-server",
        instructions="""
        F-Prime Internal MCP Server
        
        This server provides access to F-Prime internal tools and resources.
        All requests must be authenticated with a valid F-Prime member session.
        
        Available tool categories:
        - Project management: Search and manage F-Prime projects
        - Documentation: Access internal documents and knowledge base
        - Team directory: Look up team members and contact information
        - Admin tools: Administrative functions (requires admin role)
        """,
    )

    # Get the tool registry
    registry = get_tool_registry()

    # Dynamically register tools from the registry
    for tool_def in registry.list_tools():
        # Create a closure to capture the tool definition
        def make_handler(tool_name: str):
            async def handler(**kwargs: Any) -> Any:
                # Get user context - this will be injected by the transport layer
                user = kwargs.pop("_user_context", None)
                
                if user is None:
                    return {"error": "Authentication required"}
                
                if not user.is_fprime_member:
                    return {"error": "F-Prime membership required"}

                try:
                    result = await registry.execute_tool(tool_name, kwargs, user)
                    return result
                except PermissionError as e:
                    return {"error": str(e)}
                except Exception as e:
                    logger.exception(f"Tool execution error: {e}")
                    return {"error": f"Tool execution failed: {e}"}

            return handler

        # Register the tool with FastMCP
        handler = make_handler(tool_def.name)
        handler.__name__ = tool_def.name
        handler.__doc__ = tool_def.description

        # Use FastMCP's tool decorator pattern
        mcp.tool(
            name=tool_def.name,
            description=tool_def.description,
        )(handler)

    return mcp


# Create the MCP server instance
mcp_server = create_mcp_server()


def get_mcp_server() -> FastMCP:
    """Get the MCP server instance."""
    return mcp_server