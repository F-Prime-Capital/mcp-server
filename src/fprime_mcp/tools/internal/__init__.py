"""F-Prime internal tools.

Add your internal tool implementations here.
Each tool should be registered with the tool_registry.
"""

from fprime_mcp.tools.registry import tool_registry, ToolPermission
from fprime_mcp.auth.models import UserSession


# Example: Project Search Tool
@tool_registry.register(
    name="fprime_search_projects",
    description="Search F-Prime projects by name, status, or team",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for project name or description",
            },
            "status": {
                "type": "string",
                "enum": ["active", "completed", "archived"],
                "description": "Filter by project status",
            },
            "team": {
                "type": "string",
                "description": "Filter by team name",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of results",
            },
        },
        "required": ["query"],
    },
    permission=ToolPermission.READ,
)
async def search_projects(arguments: dict, user: UserSession) -> dict:
    """Search F-Prime projects."""
    query = arguments.get("query", "")
    status = arguments.get("status")
    team = arguments.get("team")
    limit = arguments.get("limit", 10)

    # TODO: Replace with actual F-Prime API call
    # This is a placeholder implementation
    results = [
        {
            "id": "proj-001",
            "name": f"Sample Project matching '{query}'",
            "status": status or "active",
            "team": team or "Core Team",
            "description": "A sample project for demonstration",
        }
    ]

    return {
        "query": query,
        "total": len(results),
        "results": results[:limit],
    }


# Example: Document Retrieval Tool
@tool_registry.register(
    name="fprime_get_document",
    description="Retrieve an F-Prime internal document by ID",
    input_schema={
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "The unique document identifier",
            },
            "include_content": {
                "type": "boolean",
                "default": True,
                "description": "Whether to include the full document content",
            },
        },
        "required": ["document_id"],
    },
    permission=ToolPermission.READ,
)
async def get_document(arguments: dict, user: UserSession) -> dict:
    """Retrieve an F-Prime document."""
    doc_id = arguments["document_id"]
    include_content = arguments.get("include_content", True)

    # TODO: Replace with actual document retrieval
    document = {
        "id": doc_id,
        "title": f"Document {doc_id}",
        "author": "F-Prime Team",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-20T14:30:00Z",
    }

    if include_content:
        document["content"] = f"This is the content of document {doc_id}..."

    return document


# Example: Team Directory Tool
@tool_registry.register(
    name="fprime_team_directory",
    description="Look up F-Prime team members and their contact information",
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name to search for",
            },
            "department": {
                "type": "string",
                "description": "Filter by department",
            },
            "role": {
                "type": "string",
                "description": "Filter by role",
            },
        },
    },
    permission=ToolPermission.READ,
)
async def team_directory(arguments: dict, user: UserSession) -> dict:
    """Search the F-Prime team directory."""
    name = arguments.get("name", "")
    department = arguments.get("department")
    role = arguments.get("role")

    # TODO: Replace with actual directory lookup
    members = [
        {
            "name": "Jane Smith",
            "email": "jane.smith@fprime.example.com",
            "department": department or "Engineering",
            "role": role or "Senior Engineer",
        }
    ]

    return {
        "query": {"name": name, "department": department, "role": role},
        "total": len(members),
        "members": members,
    }


# Example: Admin Tool (requires special role)
@tool_registry.register(
    name="fprime_admin_stats",
    description="Get administrative statistics (admin only)",
    input_schema={
        "type": "object",
        "properties": {
            "time_range": {
                "type": "string",
                "enum": ["day", "week", "month", "year"],
                "default": "week",
            },
        },
    },
    permission=ToolPermission.ADMIN,
    required_roles=["FPrime.Admin"],
)
async def admin_stats(arguments: dict, user: UserSession) -> dict:
    """Get administrative statistics."""
    time_range = arguments.get("time_range", "week")

    # TODO: Replace with actual admin stats
    return {
        "time_range": time_range,
        "active_users": 150,
        "total_requests": 5420,
        "avg_response_time_ms": 145,
    }