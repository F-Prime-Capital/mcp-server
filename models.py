from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class CompanySearchQuery(BaseModel):
    prompt: str | None = None
    name: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class DocumentFilterQuery(BaseModel):
    prompt: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class DocumentQueryRequest(BaseModel):
    document_id: str
    question: str
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class SimilarPeopleQuery(BaseModel):
    prompt: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class ContactInfoRequest(BaseModel):
    name: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)
