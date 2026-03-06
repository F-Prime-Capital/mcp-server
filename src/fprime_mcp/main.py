"""Remote MCP server entrypoint for F-Prime tools."""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from fprime_mcp.tools.network_search import search_network_by_natural_language as run_network_search
from fprime_mcp.tools.therapeutics import query_therapeutics_landscape

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "8000"))
MCP_PATH = os.getenv("MCP_PATH", "/mcp")
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")

mcp = FastMCP(
    name="F-Prime MCP Server",
    instructions=(
        "Use these tools for therapeutics intelligence and network discovery. "
        "Prefer specific filters for better quality and lower latency."
    ),
    host=HOST,
    port=PORT,
    streamable_http_path=MCP_PATH,
)


@mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def healthz(_request: Request) -> JSONResponse:
    """Simple health endpoint for Docker/liveness checks."""
    return JSONResponse(
        {
            "status": "ok",
            "service": "fprime-mcp-server",
            "transport": MCP_TRANSPORT,
            "mcp_path": MCP_PATH,
        }
    )


@mcp.tool()
def therapeutics_landscape(
    target: str = "",
    indication: str = "",
    molecule_type: str = "",
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Query therapeutics landscape data across Box, websites, and GlobalData."""
    return query_therapeutics_landscape(
        target=target,
        indication=indication,
        molecule_type=molecule_type,
        sources=sources,
    )


@mcp.tool()
def search_network_by_natural_language(
    text_queries: list[str] | None = None,
    linkedins: list[str] | None = None,
    linkedin_experience_type: list[str] | None = None,
    num_results: int = 100,
    limit_response: int | None = None,
    response_format: str = "csv",
    location: list[str] | None = None,
    title_filter_out: list[str] | None = None,
    title_filter_in: list[str] | None = None,
    founding_date: str | None = None,
    funding_total: str | None = None,
    headcount: str | None = None,
    recency_category: list[str] | None = None,
    function: list[str] | None = None,
    seniority: list[str] | None = None,
    company_type: list[str] | None = None,
    years_of_experience: str | None = None,
    num_relevant_years: str | None = None,
    years_of_experience_at_company: str | None = None,
    harmonic_ids: list[str] | None = None,
    company_ids: list[str] | None = None,
    company_list_id: str | None = None,
    retrieve_affinity_profile_urls: bool = False,
) -> dict[str, Any]:
    """Search people in the network using natural language and optional structured filters."""
    return run_network_search(
        text_queries=text_queries,
        linkedins=linkedins,
        linkedin_experience_type=linkedin_experience_type,
        num_results=num_results,
        limit_response=limit_response,
        response_format=response_format,
        location=location,
        title_filter_out=title_filter_out,
        title_filter_in=title_filter_in,
        founding_date=founding_date,
        funding_total=funding_total,
        headcount=headcount,
        recency_category=recency_category,
        years_of_experience=years_of_experience,
        function=function,
        seniority=seniority,
        company_type=company_type,
        num_relevant_years=num_relevant_years,
        years_of_experience_at_company=years_of_experience_at_company,
        harmonic_ids=harmonic_ids,
        company_ids=company_ids,
        company_list_id=company_list_id,
        retrieve_affinity_profile_urls=retrieve_affinity_profile_urls,
    )


def main() -> None:
    """Run the MCP server with the configured transport."""
    valid_transports = {"streamable-http", "stdio", "sse"}
    if MCP_TRANSPORT not in valid_transports:
        raise ValueError(
            f"Invalid MCP_TRANSPORT '{MCP_TRANSPORT}'. "
            "Valid values: streamable-http, stdio, sse"
        )
    logger.info("Starting MCP server on %s:%s (transport=%s)", HOST, PORT, MCP_TRANSPORT)
    mcp.run(transport=MCP_TRANSPORT)


if __name__ == "__main__":
    main()
