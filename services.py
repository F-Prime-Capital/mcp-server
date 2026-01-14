from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from repositories import VCProxyRepository


@dataclass(frozen=True)
class CompanyService:
    repo: VCProxyRepository

    def search_companies(self, auth_token: str, payload: dict[str, Any]) -> Any:
        # Fill in: exact payload schema expected by get_similars (ex name/domain/filters/etc).
        return self.repo.get_similars(auth_token, payload)


@dataclass(frozen=True)
class PeopleService:
    repo: VCProxyRepository

    def similar_people_search(self, auth_token: str, payload: dict[str, Any]) -> Any:
        # Fill in: exact payload schema expected by get_similar_people (ex natural language).
        return self.repo.get_similar_people(auth_token, payload)


@dataclass(frozen=True)
class DocumentService:
    repo: VCProxyRepository

    def filter_documents(self, _auth_token: str, _payload: dict[str, Any]) -> Any:
        # Fill in: a real document index/search endpoint (not present in allowed_endpoints list).
        raise NotImplementedError("No document filter endpoint wired yet.")

    def query_document(self, _auth_token: str, _payload: dict[str, Any]) -> Any:
        # Fill in: (1) a doc retrieval endpoint, and (2) a QA/search-in-doc endpoint.
        raise NotImplementedError("No document query endpoint wired yet.")
