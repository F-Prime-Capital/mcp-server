from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------
# Shared / generic request models
# ---------------------------


class GenericToolQuery(BaseModel):
    """Generic free-form query wrapper for tools that are not fully wired yet."""

    prompt: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


# ---------------------------
# Research Portal / Similarity / Contact info
# ---------------------------


class CompanySearchQuery(BaseModel):
    """(Legacy) Company search / similarity request."""

    prompt: str | None = None
    name: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class SimilarCompaniesQuery(BaseModel):
    """Find companies similar to a provided list (tech-only today)."""

    companies: list[str] = Field(default_factory=list)
    prompt: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class SimilarPeopleQuery(BaseModel):
    prompt: str | None = None
    people: list[str] = Field(default_factory=list)
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class ContactInfoRequest(BaseModel):
    """Get emails/LinkedIns from name+company/domain or LinkedIn URL.

    If find_founders=True and a domain is provided, we will also attempt to return
    founder/exec info (if the backend endpoint exists).
    """

    name: str | None = None
    company: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    find_founders: bool = False
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class ResearchPortalRequest(BaseModel):
    """Single entry-point tool for company/person research.

    This is intentionally broad; the backend wiring may vary.
    """

    action: Literal[
        "company_search",
        "company_connections",
        "founder_exec_info",
        "theme_description",
        "map_theme",
    ] = "company_search"

    prompt: str | None = None

    # Common company identifiers
    name: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None

    qualifiers: dict[str, Any] = Field(default_factory=dict)


# ---------------------------
# Docs / LLM tools
# ---------------------------


class DocumentFilterQuery(BaseModel):
    prompt: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class DocumentQueryRequest(BaseModel):
    document_id: str
    question: str
    qualifiers: dict[str, Any] = Field(default_factory=dict)


# ---------------------------
# Box / SharePoint search (skeleton)
# ---------------------------


class FolderSearchQuery(BaseModel):
    """Search for folders and optionally query within them.

    Used as a skeleton for HC Box Search, Tech Box Search, and SharePoint Search.
    """

    prompt: str | None = None

    # common filters
    name: str | None = None
    summary: str | None = None

    # healthcare-ish
    genes: str | None = None
    indications: str | None = None
    technology: str | None = None

    # tech-ish
    product: str | None = None
    sector: str | None = None
    customer_type: str | None = None

    qualifiers: dict[str, Any] = Field(default_factory=dict)


# ---------------------------
# Therapeutics Landscape (implemented)
# ---------------------------


class TherapeuticsLandscapeQuery(BaseModel):
    """Search pipeline drugs/companies by target/gene, indication, and molecule type.

    Mirrors the reference Lambda: searches Box (Airtable), websites (Airtable), and GlobalData.
    """

    target: str | None = None
    indication: str | None = None
    molecule_type: str | None = None

    sources: list[Literal["box", "websites", "globaldata"]] = Field(
        default_factory=lambda: ["box", "websites", "globaldata"]
    )
    download: bool = False

    qualifiers: dict[str, Any] = Field(default_factory=dict)


# ---------------------------
# Memo writer / Voting / AR (skeleton)
# ---------------------------


class MemoWriterRequest(BaseModel):
    company: str | None = None
    prompt: str | None = None
    box_folder_id: str | None = None
    sections: list[str] = Field(default_factory=list)
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class VotingRequest(BaseModel):
    company: str
    action: Literal["view", "set_vote"] = "view"
    vote: Literal["yes", "no", "abstain"] | None = None
    notes: str | None = None
    qualifiers: dict[str, Any] = Field(default_factory=dict)


class AccountsReceivableRequest(BaseModel):
    action: Literal["list", "get", "create", "update", "send"] = "list"
    invoice_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    qualifiers: dict[str, Any] = Field(default_factory=dict)
