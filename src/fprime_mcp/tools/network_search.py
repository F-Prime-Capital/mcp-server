"""Network search MCP tool backed by the internal network search API."""

from __future__ import annotations

import csv
import io
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

DEFAULT_NETWORK_SEARCHER_API_URL = (
    "http://ec2-18-220-218-243.us-east-2.compute.amazonaws.com:8000/search-network-by-company-list"
)


class NetworkSearchRequest(BaseModel):
    """Request model for network search with basic validation."""

    text_queries: list[str] | None = Field(default=None)
    linkedins: list[str] | None = Field(default=None)
    linkedin_experience_type: list[str] | None = Field(default=None)
    num_results: int = Field(default=100, ge=1, le=1000)
    limit_response: int | None = Field(default=None, ge=1)
    response_format: str = Field(default="csv")
    retrieve_affinity_profile_urls: bool = Field(default=False)

    location: list[str] | None = None
    title_filter_out: list[str] | None = None
    title_filter_in: list[str] | None = None
    founding_date: str | None = None
    funding_total: str | None = None
    headcount: str | None = None
    company_type: list[str] | None = None
    company_ids: list[str] | None = None
    company_list_id: str | None = None
    recency_category: list[str] | None = None
    years_of_experience: str | None = None
    function: list[str] | None = None
    seniority: list[str] | None = None
    num_relevant_years: str | None = None
    years_of_experience_at_company: str | None = None
    harmonic_ids: list[str] | None = None

    @field_validator("linkedin_experience_type")
    @classmethod
    def validate_linkedin_experience_type(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        valid = {"current_company", "past_companies", "all"}
        invalid = set(value) - valid
        if invalid:
            raise ValueError(f"Invalid linkedin_experience_type values: {invalid}")
        return value

    @field_validator("response_format")
    @classmethod
    def validate_response_format(cls, value: str) -> str:
        valid = {"json", "csv"}
        normalized = value.lower()
        if normalized not in valid:
            raise ValueError(f"Invalid response_format: {value}. Valid values: {valid}")
        return normalized

    def to_filters_dict(self) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        filter_fields = [
            "location",
            "title_filter_out",
            "title_filter_in",
            "founding_date",
            "funding_total",
            "headcount",
            "recency_category",
            "years_of_experience",
            "function",
            "seniority",
            "company_type",
            "num_relevant_years",
            "years_of_experience_at_company",
            "harmonic_ids",
            "company_ids",
            "company_list_id",
        ]

        for field in filter_fields:
            value = getattr(self, field)
            if value is not None:
                filters[field] = value

        return filters

    def has_search_criteria(self) -> bool:
        return bool(self.linkedins) or bool(self.text_queries) or bool(self.to_filters_dict())


def convert_results_to_csv(results: list[dict[str, Any]]) -> str:
    """Convert person records to CSV for token-efficient MCP responses."""
    if not results:
        return ""

    headers = [
        "person_name",
        "linkedin_url",
        "title",
        "company_name",
        "location",
        "seniority",
        "function",
        "engagement",
        "relevance_score",
        "best_similarity",
        "recency_weighted_similarity",
        "top_k_similarity",
        "relationships",
        "relationship_emails",
        "strongest_connection_email",
        "harmonic_profile_url",
        "affinity_profile_url",
        "HaveContactedInLastYear",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()

    for person in results:
        writer.writerow(
            {
                "person_name": person.get("person_name", ""),
                "linkedin_url": person.get("linkedin_url", ""),
                "title": person.get("title", ""),
                "company_name": person.get("company_name", ""),
                "location": person.get("location", ""),
                "seniority": person.get("seniority", ""),
                "function": "; ".join(person.get("function", [])) if person.get("function") else "",
                "engagement": person.get("engagement", ""),
                "relevance_score": person.get("relevance_score", ""),
                "best_similarity": person.get("best_similarity", ""),
                "recency_weighted_similarity": person.get("recency_weighted_similarity", ""),
                "top_k_similarity": person.get("top_k_similarity", ""),
                "relationships": "; ".join(person.get("relationships", []))
                if person.get("relationships")
                else "",
                "relationship_emails": "; ".join(person.get("relationship_emails", []))
                if person.get("relationship_emails")
                else "",
                "strongest_connection_email": person.get("strongest_connection_email", ""),
                "harmonic_profile_url": person.get("harmonic_profile_url", ""),
                "affinity_profile_url": person.get("affinity_profile_url", ""),
                "HaveContactedInLastYear": person.get("HaveContactedInLastYear", False),
            }
        )

    return output.getvalue()


def search_network_by_natural_language(**kwargs: Any) -> dict[str, Any]:
    """Search the network by natural language, LinkedIn similarity, and structured filters."""
    try:
        request = NetworkSearchRequest(**kwargs)
    except ValidationError as exc:
        return {"success": False, "error": f"Validation error: {exc}", "results": [], "count": 0}

    if not request.has_search_criteria():
        return {
            "success": False,
            "error": "At least one of linkedins, text_queries, or filters is required",
            "results": [],
            "count": 0,
        }

    payload: dict[str, Any] = {
        "linkedin_urls": request.linkedins or [],
        "linkedin_experience_type": request.linkedin_experience_type or [],
        "text_queries": request.text_queries or [],
        "filters": request.to_filters_dict(),
        "num_results": request.num_results,
        "retrieve_affinity_profile_urls": request.retrieve_affinity_profile_urls,
    }
    if request.limit_response is not None:
        payload["limit_response"] = request.limit_response

    api_key = os.getenv("INTERNAL_API_KEY")
    api_url = os.getenv("NETWORK_SEARCHER_API_URL", DEFAULT_NETWORK_SEARCHER_API_URL)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    timeout = httpx.Timeout(2400.0, connect=10.0)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            api_response = response.json()
    except httpx.TimeoutException as exc:
        return {"success": False, "error": f"Request timed out: {exc}", "results": [], "count": 0}
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "error": f"API returned {exc.response.status_code}: {exc.response.text}",
            "results": [],
            "count": 0,
        }
    except httpx.RequestError as exc:
        return {"success": False, "error": f"Request failed: {exc}", "results": [], "count": 0}

    if isinstance(api_response, dict) and "data" in api_response:
        people_data = api_response["data"]
    elif isinstance(api_response, list):
        people_data = api_response
    elif isinstance(api_response, dict):
        people_data = api_response.get("results", {}).get("data", [])
    else:
        people_data = []

    count = len(people_data) if isinstance(people_data, list) else 0
    if request.response_format == "csv":
        return {
            "success": True,
            "format": "csv",
            "csv_data": convert_results_to_csv(people_data),
            "count": count,
        }

    return {"success": True, "format": "json", "results": api_response, "count": count}
