"""Tool registry for F-Prime internal tools."""

import logging
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

from fprime_mcp.auth.models import UserSession

logger = logging.getLogger(__name__)


class ToolPermission(Enum):
    """Permission levels for tools."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


@dataclass
class ToolDefinition:
    """Definition of an F-Prime tool."""
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Awaitable[Any]]
    permission: ToolPermission = ToolPermission.READ
    required_roles: list[str] = field(default_factory=list)
    enabled: bool = True


class ToolRegistry:
    """Registry for F-Prime internal tools."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        permission: ToolPermission = ToolPermission.READ,
        required_roles: list[str] | None = None,
    ):
        """Decorator to register a tool handler."""
        def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
            self._tools[name] = ToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=func,
                permission=permission,
                required_roles=required_roles or [],
            )
            logger.info(f"Registered tool: {name}")
            return func
        return decorator

    def get_tool(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def list_tools(self, user: UserSession | None = None) -> list[ToolDefinition]:
        """List all available tools, optionally filtered by user permissions."""
        tools = [t for t in self._tools.values() if t.enabled]

        if user:
            # Filter by required roles
            tools = [
                t for t in tools
                if not t.required_roles or any(r in user.roles for r in t.required_roles)
            ]

        return tools

    def check_permission(self, tool_name: str, user: UserSession) -> bool:
        """Check if user has permission to use a tool."""
        tool = self.get_tool(tool_name)
        if not tool:
            return False

        # Check required roles
        if tool.required_roles:
            if not any(r in user.roles for r in tool.required_roles):
                return False

        return True

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        user: UserSession,
    ) -> Any:
        """Execute a tool with the given arguments."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        if not self.check_permission(name, user):
            raise PermissionError(f"User does not have permission to use tool: {name}")

        logger.info(f"Executing tool {name} for user {user.user_id}")
        return await tool.handler(arguments, user=user)


# Global registry instance
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return tool_registry