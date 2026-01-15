from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import base64
import io
import time

from repositories import VCProxyRepository, TherapeuticsLandscapeRepository
from models import TherapeuticsLandscapeQuery, ResearchPortalRequest


def not_implemented(tool_name: str, message: str, **kwargs: Any) -> dict[str, Any]:
    return {
        "status": "not_implemented",
        "tool": tool_name,
        "message": message,
        **kwargs,
    }


@dataclass(frozen=True)
class SimilarityService:
    repo: VCProxyRepository

    def similar_companies(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.repo.get_similars(auth_token, payload)

    def similar_people(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.repo.get_similar_people(auth_token, payload)


@dataclass(frozen=True)
class ContactInfoService:
    repo: VCProxyRepository

    def get_contact_info(self, auth_token: str, *, name: str | None, domain: str | None, linkedin_url: str | None, qualifiers: dict[str, Any]) -> Any:
        return self.repo.get_email_address(auth_token, name=name, domain=domain, linkedin_url=linkedin_url, qualifiers=qualifiers)

    def get_founder_exec_info(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.repo.pull_founder_exec_info(auth_token, payload)


@dataclass(frozen=True)
class ResearchPortalService:
    """Company / people research entry point.

    This is partially backed by existing proxy endpoints:
      - get_similars
      - pull_founder_exec_info
      - get_theme_description
      - map_theme

    Other actions can be wired later.
    """

    repo: VCProxyRepository

    def handle(self, auth_token: str, req: ResearchPortalRequest) -> Any:
        payload: dict[str, Any] = {**(req.qualifiers or {})}
        if req.prompt is not None:
            payload["prompt"] = req.prompt
        if req.name is not None:
            payload["name"] = req.name
        if req.domain is not None:
            payload["domain"] = req.domain
        if req.linkedin_url is not None:
            payload["linkedin_url"] = req.linkedin_url

        if req.action == "company_search":
            # Today, company search is mapped to the existing similarity endpoint.
            return self.repo.get_similars(auth_token, payload)
        if req.action == "company_connections":
            return not_implemented(
                "research_portal",
                "Company connection search is not wired yet (no backend endpoint configured).",
                payload=payload,
            )
        if req.action == "founder_exec_info":
            return self.repo.pull_founder_exec_info(auth_token, payload)
        if req.action == "theme_description":
            return self.repo.get_theme_description(auth_token, payload)
        if req.action == "map_theme":
            return self.repo.map_theme(auth_token, payload)

        return not_implemented("research_portal", f"Unknown action: {req.action}")


@dataclass
class TherapeuticsLandscapeService:
    repo: TherapeuticsLandscapeRepository

    def search(self, query: TherapeuticsLandscapeQuery) -> dict[str, Any]:
        target = (query.target or "").strip()
        indication = (query.indication or "").strip()
        molecule_type = (query.molecule_type or "").strip()

        if not (target or indication or molecule_type):
            return {"status": "error", "message": "Provide at least one of target, indication, molecule_type."}

        sources = set(query.sources or ["box", "websites", "globaldata"])

        box_results = None
        website_results = None
        globaldata_results = None

        if "box" in sources:
            box_results = self.repo.query_box(target, indication, molecule_type)
        if "websites" in sources:
            website_results = self.repo.query_websites(target, indication, molecule_type)
        if "globaldata" in sources:
            globaldata_results = self.repo.query_globaldata(target, indication, molecule_type)

        out: dict[str, Any] = {
            "status": "ok",
            "box_results": box_results,
            "website_results": website_results,
            "globaldata_results": globaldata_results,
        }

        if query.download:
            try:
                import pandas as pd
            except Exception as e:
                return {
                    **out,
                    "download": {
                        "status": "error",
                        "message": "Download requires pandas + openpyxl (pip install pandas openpyxl).",
                        "error": str(e),
                    },
                }

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                if box_results is not None:
                    box_df = pd.DataFrame(box_results)
                    box_df.drop(columns=["box_id", "bot_file", "affinity_id"], inplace=True, errors="ignore")
                    box_df.to_excel(writer, sheet_name="Box", index=False)
                if website_results is not None:
                    website_df = pd.DataFrame(website_results)
                    website_df.drop(columns=["harmonic_id", "Last Modified"], inplace=True, errors="ignore")
                    website_df.to_excel(writer, sheet_name="Websites", index=False)
                if globaldata_results is not None:
                    gd_rows = self.repo.parse_globaldata_download(globaldata_results)
                    gd_df = pd.DataFrame(gd_rows)
                    gd_df.to_excel(writer, sheet_name="GlobalData", index=False)

            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode("ascii")
            out["download"] = {
                "status": "ok",
                "filename": f"therapeutics_landscape_{int(time.time())}.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "base64": b64,
            }

        return out


# ---------------------------
# Skeleton services (to be wired later)
# ---------------------------


@dataclass(frozen=True)
class SkeletonService:
    tool_name: str

    def run(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return not_implemented(
            self.tool_name,
            "This tool is stubbed in the MCP server but not wired to a backend yet.",
        )
