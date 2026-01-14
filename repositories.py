from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from proxy_client import LambdaProxyClient


@dataclass(frozen=True)
class VCProxyRepository:
    proxy: LambdaProxyClient

    def get_email_address(self, auth_token: str, name: str | None, domain: str | None, linkedin_url: str | None, qualifiers: dict[str, Any]) -> Any:
        payload: dict[str, Any] = {**qualifiers}
        if name is not None:
            payload["name"] = name
        if domain is not None:
            payload["domain"] = domain
        if linkedin_url is not None:
            payload["linkedin_url"] = linkedin_url

        return self.proxy.post("get_email_address", payload, auth_token)

    def pull_founder_exec_info(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.proxy.post("pull_founder_exec_info", payload, auth_token)

    def get_similars(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.proxy.post("get_similars", payload, auth_token)

    def get_similar_people(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.proxy.post("get_similar_people", payload, auth_token)

    def get_theme_description(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.proxy.post("get_theme_description", payload, auth_token)

    def map_theme(self, auth_token: str, payload: dict[str, Any]) -> Any:
        return self.proxy.post("map_theme", payload, auth_token)
