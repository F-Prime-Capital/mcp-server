from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from config import SETTINGS
from auth import require_auth, AuthError, ForbiddenError
from models import (
    CompanySearchQuery,
    CompanyRecord,
    DocumentFilterQuery,
    DocumentRecord,
    DocumentQueryRequest,
    DocumentQueryResponse,
    SimilarPeopleQuery,
    PersonRecord,
)
from repositories import (
    StubCompanyRepository,
    StubDocumentRepository,
    StubPeopleRepository,
)
from services import DocumentQAService


mcp = FastMCP(SETTINGS.mcp_name)

companies_repo = StubCompanyRepository()
documents_repo = StubDocumentRepository()
people_repo = StubPeopleRepository()
doc_qa = DocumentQAService()


def _authorize_or_raise(ctx, action: str) -> None:
    # Fill in: map ctx.roles/ctx.groups to permissions per action and dataset.
    # Examples you’ll need to define:
    # - who can access which doc types / deal rooms
    # - who can access investment committee memos
    # - who can query Affinity relationship graphs
    raise NotImplementedError("Implement authorization policy for actions/datasets.")


@mcp.tool(name="search_companies")
def search_companies(query: CompanySearchQuery, access_token: str | None = None) -> list[CompanyRecord]:
    ctx = require_auth(access_token)
    _authorize_or_raise(ctx, action="search_companies")
    return companies_repo.search(query)


@mcp.tool(name="filter_documents")
def filter_documents(query: DocumentFilterQuery, access_token: str | None = None) -> list[DocumentRecord]:
    ctx = require_auth(access_token)
    _authorize_or_raise(ctx, action="filter_documents")
    return documents_repo.filter(query)


@mcp.tool(name="query_document")
def query_document(request: DocumentQueryRequest, access_token: str | None = None) -> DocumentQueryResponse:
    ctx = require_auth(access_token)
    _authorize_or_raise(ctx, action="query_document")
    doc_text = documents_repo.get_text(request.document_id)
    return doc_qa.answer(doc_text, request)


@mcp.tool(name="similar_people_search")
def similar_people_search(query: SimilarPeopleQuery, access_token: str | None = None) -> list[PersonRecord]:
    ctx = require_auth(access_token)
    _authorize_or_raise(ctx, action="similar_people_search")
    return people_repo.similar_people(query)


@mcp.tool(name="health")
def health() -> dict:
    return {"name": SETTINGS.mcp_name, "env": SETTINGS.environment, "ok": True}


if __name__ == "__main__":
    mcp.run(transport="stdio")
