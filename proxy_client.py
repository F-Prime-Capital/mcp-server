from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import requests


class ProxyError(Exception):
    pass


@dataclass(frozen=True)
class LambdaProxyClient:
    base_url: str
    timeout_s: float = 30.0

    def _with_endpoint(self, endpoint: str) -> str:
        parsed = urlparse(self.base_url)
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        q["endpoint"] = endpoint
        new_query = urlencode(q, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    def post(self, endpoint: str, payload: dict[str, Any], auth_token: str) -> Any:
        url = self._with_endpoint(endpoint)
        headers = {"authorization": auth_token, "content-type": "application/json"}

        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.timeout_s)

        if not r.ok:
            try:
                body = r.json()
            except Exception:
                body = r.text
            raise ProxyError(f"Proxy call failed: status={r.status_code}, body={body}")

        try:
            return r.json()
        except Exception as e:
            raise ProxyError(f"Proxy returned non-JSON body: {r.text}") from e
