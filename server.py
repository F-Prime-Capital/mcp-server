from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from config import SETTINGS
from auth import require_auth_token, authorize_action
from proxy_client import LambdaProxyClient, ProxyError
from repositories import VCProxyRepository, TherapeuticsLandscapeRepository
from services import (
    SimilarityService,
    ContactInfoService,
    ResearchPortalService,
    TherapeuticsLandscapeService,
    SkeletonService,
)
from models import (
    GenericToolQuery,
    ResearchPortalRequest,
    ContactInfoRequest,
    SimilarCompaniesQuery,
    SimilarPeopleQuery,
    FolderSearchQuery,
    TherapeuticsLandscapeQuery,
    MemoWriterRequest,
    VotingRequest,
    AccountsReceivableRequest,
)


mcp = FastMCP(SETTINGS.mcp_name)


# ---------------------------
# Wiring
# ---------------------------


proxy_client: LambdaProxyClient | None = None
proxy_repo: VCProxyRepository | None = None

if SETTINGS.proxy_api_url:
    proxy_client = LambdaProxyClient(base_url=SETTINGS.proxy_api_url, timeout_s=SETTINGS.http_timeout_s)
    proxy_repo = VCProxyRepository(proxy=proxy_client)


therapeutics_repo = TherapeuticsLandscapeRepository(
    airtable_api_key=SETTINGS.airtable_api_key,
    globaldata_token=SETTINGS.globaldata_token,
    use_secrets_manager=SETTINGS.use_secrets_manager,
    secret_name=SETTINGS.resource_logins_secret_name,
    aws_region=SETTINGS.aws_region,
    box_base_id=SETTINGS.tl_box_base_id,
    box_table_id=SETTINGS.tl_box_table_id,
    website_base_id=SETTINGS.tl_website_base_id,
    website_table_id=SETTINGS.tl_website_table_id,
    globaldata_endpoint=SETTINGS.globaldata_endpoint,
    cache_ttl_s=SETTINGS.tl_cache_ttl_s,
    cache_maxsize=SETTINGS.tl_cache_maxsize,
)

therapeutics_service = TherapeuticsLandscapeService(repo=therapeutics_repo)


# Proxy-backed services (optional)
if proxy_repo is not None:
    similarity_service = SimilarityService(repo=proxy_repo)
    contact_service = ContactInfoService(repo=proxy_repo)
    research_portal_service = ResearchPortalService(repo=proxy_repo)
else:
    similarity_service = None
    contact_service = None
    research_portal_service = None


# Skeleton tools to be wired later
subscriptions_service = SkeletonService(tool_name="subscriptions")
resources_service = SkeletonService(tool_name="resources")
llm_tools_service = SkeletonService(tool_name="llm_tools")
memo_writer_service = SkeletonService(tool_name="memo_writer")
publics_service = SkeletonService(tool_name="publics")
preprints_service = SkeletonService(tool_name="preprints")
hc_box_search_service = SkeletonService(tool_name="hc_box_search")
hc_sourcing_service = SkeletonService(tool_name="hc_sourcing")
tech_box_search_service = SkeletonService(tool_name="tech_box_search")
fsv_sharepoint_search_service = SkeletonService(tool_name="fsv_sharepoint_search")
healthcare_voting_service = SkeletonService(tool_name="healthcare_voting")
tech_voting_service = SkeletonService(tool_name="tech_voting")
publics_report_service = SkeletonService(tool_name="publics_report")
accounts_receivable_service = SkeletonService(tool_name="accounts_receivable")


def _require_proxy() -> VCProxyRepository:
    if proxy_repo is None:
        raise RuntimeError("VC_PROXY_API_URL is not set, so proxy-backed tools are unavailable.")
    return proxy_repo


def _as_payload(prompt: str | None, qualifiers: dict[str, Any] | None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if prompt is not None:
        payload["prompt"] = prompt
    payload.update(qualifiers or {})
    if extra:
        payload.update({k: v for k, v in extra.items() if v is not None})
    return payload


# ---------------------------
# Tools
# ---------------------------


@mcp.tool(name="subscriptions")
def subscriptions(query: GenericToolQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "subscriptions")
    return subscriptions_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="resources")
def resources(query: GenericToolQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "resources")
    return resources_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="research_portal")
def research_portal(req: ResearchPortalRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "research_portal")

    if research_portal_service is None:
        _require_proxy()

    return research_portal_service.handle(ctx.auth_token, req)  # type: ignore[union-attr]


@mcp.tool(name="get_contact_info")
def get_contact_info(req: ContactInfoRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "get_contact_info")

    if contact_service is None:
        _require_proxy()

    contact = contact_service.get_contact_info(
        ctx.auth_token,
        name=req.name,
        domain=req.domain,
        linkedin_url=req.linkedin_url,
        qualifiers=req.qualifiers,
    )  # type: ignore[union-attr]

    if req.find_founders and req.domain:
        founders = contact_service.get_founder_exec_info(
            ctx.auth_token,
            {"domain": req.domain, **(req.qualifiers or {})},
        )  # type: ignore[union-attr]
        return {"contact_info": contact, "founders": founders}

    return contact


@mcp.tool(name="llm_tools")
def llm_tools(query: GenericToolQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "llm_tools")
    return llm_tools_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="memo_writer")
def memo_writer(req: MemoWriterRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "memo_writer")
    return memo_writer_service.run(ctx.auth_token, req.dict())


@mcp.tool(name="publics")
def publics(query: GenericToolQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "publics")
    return publics_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="preprints")
def preprints(query: GenericToolQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "preprints")
    return preprints_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="hc_box_search")
def hc_box_search(query: FolderSearchQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "hc_box_search")
    return hc_box_search_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="therapeutics_landscape")
def therapeutics_landscape(query: TherapeuticsLandscapeQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "therapeutics_landscape")
    return therapeutics_service.search(query)


@mcp.tool(name="hc_sourcing")
def hc_sourcing(query: GenericToolQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "hc_sourcing")
    return hc_sourcing_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="tech_box_search")
def tech_box_search(query: FolderSearchQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "tech_box_search")
    return tech_box_search_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="similar_companies")
def similar_companies(query: SimilarCompaniesQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "similar_companies")

    if similarity_service is None:
        _require_proxy()

    payload = _as_payload(query.prompt, query.qualifiers, {"companies": query.companies})
    return similarity_service.similar_companies(ctx.auth_token, payload)  # type: ignore[union-attr]


@mcp.tool(name="similar_people")
def similar_people(query: SimilarPeopleQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "similar_people")

    if similarity_service is None:
        _require_proxy()

    payload = _as_payload(query.prompt, query.qualifiers, {"people": query.people})
    return similarity_service.similar_people(ctx.auth_token, payload)  # type: ignore[union-attr]


@mcp.tool(name="fsv_sharepoint_search")
def fsv_sharepoint_search(query: FolderSearchQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "fsv_sharepoint_search")
    return fsv_sharepoint_search_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="healthcare_voting")
def healthcare_voting(req: VotingRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "healthcare_voting")
    return healthcare_voting_service.run(ctx.auth_token, req.dict())


@mcp.tool(name="tech_voting")
def tech_voting(req: VotingRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "tech_voting")
    return tech_voting_service.run(ctx.auth_token, req.dict())


@mcp.tool(name="publics_report")
def publics_report(query: GenericToolQuery, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "publics_report")
    return publics_report_service.run(ctx.auth_token, query.dict())


@mcp.tool(name="accounts_receivable")
def accounts_receivable(req: AccountsReceivableRequest, access_token: str | None = None) -> Any:
    ctx = require_auth_token(access_token)
    authorize_action(ctx, "accounts_receivable")
    return accounts_receivable_service.run(ctx.auth_token, req.dict())


@mcp.tool(name="health")
def health() -> dict[str, Any]:
    return {
        "name": SETTINGS.mcp_name,
        "env": SETTINGS.environment,
        "ok": True,
        "proxy_configured": bool(SETTINGS.proxy_api_url),
        "therapeutics_landscape_configured": bool(SETTINGS.airtable_api_key or SETTINGS.use_secrets_manager),
    }


@mcp.tool(name="proxy_smoke_test")
def proxy_smoke_test(access_token: str | None = None) -> dict[str, Any]:
    if proxy_repo is None:
        return {"ok": False, "error": "VC_PROXY_API_URL not set"}

    ctx = require_auth_token(access_token)
    try:
        _ = proxy_repo.get_email_address(ctx.auth_token, name=None, domain=None, linkedin_url=None, qualifiers={})
        return {"ok": True}
    except ProxyError as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
