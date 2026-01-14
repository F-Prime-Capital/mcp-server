from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from config import SETTINGS
from auth import require_auth_token, authorize_action
from proxy_client import LambdaProxyClient, ProxyError
from repositories import VCProxyRepository
from services import CompanyService, PeopleService, DocumentService
from models import (
    CompanySearchQuery,
    DocumentFilterQuery,
    DocumentQueryRequest,
    SimilarPeopleQuery,
    ContactInfoRequest,
)


mcp = FastMCP(SETTINGS.mcp_name)

if not SETTINGS.proxy_api_url:
    raise RuntimeError("VC_PROXY_API_URL must be set.")

proxy_client = LambdaProxyClient(base_url=SETTINGS.proxy_api_url, timeout_s=SETTINGS.http_timeout_s)
repo = VCProxyRepository(proxy=proxy_client)

company_service = CompanyService(repo=repo)
people_service = PeopleService(repo=repo)
document_service = DocumentService(repo=repo)


def _as_payload(prompt: str | None, qualifiers: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if prompt is not None:
        payload["prompt"] = prompt
    payload.update(qualifiers or {})
    if extra:
        payload.update({k: v for k, v in extra.items() if v is not None})
    return payload


@mcp.tool(name="search_companies")
def search_companies(query: CompanySearchQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "search_companies")
    payload = _as_payload(query.prompt, query.qualifiers, {"name": query.name, "domain": query.domain, "linkedin_url": query.linkedin_url})
    return company_service.search_companies(ctx.auth_token, payload)


@mcp.tool(name="filter_documents")
def filter_documents(query: DocumentFilterQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "filter_documents")
    payload = _as_payload(query.prompt, query.qualifiers)
    return document_service.filter_documents(ctx.auth_token, payload)


@mcp.tool(name="query_document")
def query_document(req: DocumentQueryRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "query_document")
    payload = {"document_id": req.document_id, "question": req.question, **(req.qualifiers or {})}
    return document_service.query_document(ctx.auth_token, payload)


@mcp.tool(name="similar_people_search")
def similar_people_search(query: SimilarPeopleQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "similar_people_search")
    payload = _as_payload(query.prompt, query.qualifiers)
    return people_service.similar_people_search(ctx.auth_token, payload)


@mcp.tool(name="get_contact_info")
def get_contact_info(req: ContactInfoRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "get_contact_info")
    return repo.get_email_address(
        auth_token=ctx.auth_token,
        name=req.name,
        domain=req.domain,
        linkedin_url=req.linkedin_url,
        qualifiers=req.qualifiers,
    )


@mcp.tool(name="health")
def health() -> dict[str, Any]:
    return {"name": SETTINGS.mcp_name, "env": SETTINGS.environment, "ok": True}


@mcp.tool(name="proxy_smoke_test")
def proxy_smoke_test(access_token: str | None = None) -> dict[str, Any]:
    ctx = require_auth_token(access_token)
    try:
        _ = repo.get_email_address(ctx.auth_token, name=None, domain=None, linkedin_url=None, qualifiers={})
        return {"ok": True}
    except ProxyError as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
