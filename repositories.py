from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any
import json
import time

from proxy_client import LambdaProxyClient


@dataclass(frozen=True)
class VCProxyRepository:
    """Repository that talks to the existing "Lambda proxy" API.

    This remains the main integration point for tools that are already implemented
    behind the API gateway.
    """

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


# ---------------------------
# Therapeutics Landscape (Box + scraped websites + GlobalData)
# ---------------------------


class SimpleTTLCache:
    """Tiny TTL cache (no external deps).

    Keys are any hashable. Values expire after ttl_s.
    Eviction is "best-effort" FIFO when maxsize is reached.
    """

    def __init__(self, ttl_s: int, maxsize: int):
        self.ttl_s = int(ttl_s)
        self.maxsize = int(maxsize)
        self._lock = Lock()
        # key -> (expires_at, inserted_at, value)
        self._store: dict[Any, tuple[float, float, Any]] = {}

    def get(self, key: Any) -> Any | None:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, _inserted_at, value = item
            if expires_at < now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        now = time.time()
        expires_at = now + self.ttl_s
        with self._lock:
            if key not in self._store and len(self._store) >= self.maxsize:
                # Evict oldest insertion
                oldest_key = min(self._store.items(), key=lambda kv: kv[1][1])[0]
                self._store.pop(oldest_key, None)
            self._store[key] = (expires_at, now, value)


@lru_cache(maxsize=4)
def _load_resource_logins_from_secrets_manager(secret_name: str, region_name: str) -> dict[str, Any]:
    """Load a JSON secret (mirrors the Lambda reference code).

    Expected keys:
      - globaldata_token
      - airtable_api

    This is cached process-wide.
    """

    import boto3  # lazy import

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    secret_val = client.get_secret_value(SecretId=secret_name)["SecretString"]
    return json.loads(secret_val)


def _normalize_target(target: str) -> str:
    return target.lower().replace("-", "")


def _normalize_indication(indication: str) -> str:
    return indication.lower()


def _normalize_molecule_type(molecule_type: str) -> str:
    m = molecule_type.lower()
    if m.endswith("y"):
        m = m[:-1]
    return m


@dataclass
class TherapeuticsLandscapeRepository:
    """Implements reference Lambda behavior directly in the MCP server.

    Searches:
    - Box metadata table (Airtable)
    - Scraped websites table (Airtable)
    - GlobalData pipeline endpoint

    Tokens can be provided via env vars or via AWS Secrets Manager.
    """

    airtable_api_key: str | None
    globaldata_token: str | None

    # optional fallback to Secrets Manager
    use_secrets_manager: bool
    secret_name: str
    aws_region: str

    # Airtable IDs
    box_base_id: str
    box_table_id: str
    website_base_id: str
    website_table_id: str

    # GlobalData endpoint
    globaldata_endpoint: str

    # caching
    cache_ttl_s: int = 600
    cache_maxsize: int = 8

    def __post_init__(self) -> None:
        self._box_cache = SimpleTTLCache(ttl_s=self.cache_ttl_s, maxsize=self.cache_maxsize)
        self._web_cache = SimpleTTLCache(ttl_s=self.cache_ttl_s, maxsize=self.cache_maxsize)
        self._gd_cache = SimpleTTLCache(ttl_s=self.cache_ttl_s, maxsize=self.cache_maxsize)

    def _resolve_tokens(self) -> tuple[str, str]:
        airtable_key = self.airtable_api_key
        gd_token = self.globaldata_token

        if (not airtable_key or not gd_token) and self.use_secrets_manager:
            try:
                secret = _load_resource_logins_from_secrets_manager(self.secret_name, self.aws_region)
                airtable_key = airtable_key or secret.get("airtable_api")
                gd_token = gd_token or secret.get("globaldata_token")
            except Exception:
                # fall through to error below
                pass

        if not airtable_key:
            raise RuntimeError(
                "Missing Airtable API key. Set AIRTABLE_API_KEY or enable Secrets Manager fallback (USE_SECRETS_MANAGER=1)."
            )
        if not gd_token:
            raise RuntimeError(
                "Missing GlobalData token. Set GLOBALDATA_TOKEN or enable Secrets Manager fallback (USE_SECRETS_MANAGER=1)."
            )
        return airtable_key, gd_token

    def query_box(self, target: str, indication: str, molecule_type: str) -> list[dict[str, Any]]:
        cache_key = ("box", target, indication, molecule_type)
        cached = self._box_cache.get(cache_key)
        if cached is not None:
            return cached

        airtable_key, _gd_token = self._resolve_tokens()

        try:
            from pyairtable import Api
        except Exception as e:
            raise RuntimeError("pyairtable is required for Box/website searches (pip install pyairtable)") from e

        t = _normalize_target(target)
        ind = _normalize_indication(indication)
        mol = _normalize_molecule_type(molecule_type)

        # Mirrors Lambda formula:
        # AND(FIND(target, SUBSTITUTE(LOWER({genes}),"-",""))>0, FIND(indication, LOWER({indications}))>0,
        #     OR(FIND(mol, LOWER({summary}))>0, FIND(mol, LOWER({technology}))>0))
        formula = (
            f'AND(FIND("{t}",SUBSTITUTE(LOWER({{genes}}),"-",""))>0,'
            f'FIND("{ind}",LOWER({{indications}}))>0,'
            f'OR(FIND("{mol}",LOWER({{summary}}))>0,FIND("{mol}",LOWER({{technology}}))>0))'
        )

        table = Api(airtable_key).table(self.box_base_id, self.box_table_id)
        results = table.all(formula=formula)
        out = [r.get("fields", {}) for r in results]
        self._box_cache.set(cache_key, out)
        return out

    def query_websites(self, target: str, indication: str, molecule_type: str) -> list[dict[str, Any]]:
        cache_key = ("websites", target, indication, molecule_type)
        cached = self._web_cache.get(cache_key)
        if cached is not None:
            return cached

        airtable_key, _gd_token = self._resolve_tokens()

        try:
            from pyairtable import Api
        except Exception as e:
            raise RuntimeError("pyairtable is required for Box/website searches (pip install pyairtable)") from e

        t = _normalize_target(target)
        ind = _normalize_indication(indication)
        mol = _normalize_molecule_type(molecule_type)

        # Mirrors Lambda formula:
        # AND(FIND(target, SUBSTITUTE(LOWER({pipeline}),"-",""))>0, FIND(indication, LOWER({pipeline}))>0,
        #     FIND(molecule_type, LOWER({pipeline}))>0)
        formula = (
            f'AND(FIND("{t}",SUBSTITUTE(LOWER({{pipeline}}),"-",""))>0,'
            f'FIND("{ind}",LOWER({{pipeline}}))>0,'
            f'FIND("{mol}",LOWER({{pipeline}}))>0)'
        )

        table = Api(airtable_key).table(self.website_base_id, self.website_table_id)
        results = table.all(formula=formula)
        out = [r.get("fields", {}) for r in results]
        self._web_cache.set(cache_key, out)
        return out

    def query_globaldata(self, target: str, indication: str, molecule_type: str) -> list[dict[str, Any]]:
        cache_key = ("globaldata", target, indication, molecule_type)
        cached = self._gd_cache.get(cache_key)
        if cached is not None:
            return cached

        _airtable_key, gd_token = self._resolve_tokens()

        import requests

        params: dict[str, Any] = {"TokenId": gd_token}
        if target:
            params["Target"] = target.lower()
        if indication:
            params["Indication"] = indication.lower()
        if molecule_type:
            params["MoleculeType"] = molecule_type.lower()

        r = requests.get(self.globaldata_endpoint, params=params, timeout=30)
        if r.status_code == 200:
            results = (r.json() or {}).get("PipelineDrugs") or []
        else:
            results = []

        # Group by CompanyID like the reference Lambda
        companies: dict[str, dict[str, Any]] = {}
        for d in results:
            co_id = d.get("CompanyID")
            co_name = d.get("Company_Name")
            if co_id in companies:
                companies[co_id]["Drugs"].append(d)
            else:
                companies[co_id] = {"Drugs": [d], "Company_Name": co_name, "CompanyID": co_id}

        out = list(companies.values())
        self._gd_cache.set(cache_key, out)
        return out

    @staticmethod
    def parse_globaldata_download(globaldata: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Flatten GlobalData response into rows for Excel export (mirrors the Lambda)."""

        rows: list[dict[str, Any]] = []
        for co in globaldata:
            drugs = co.get("Drugs") or []
            co_name = co.get("Company_Name")
            for d in drugs:
                name = d.get("Drug_Name")
                alias = d.get("Alias")
                description = d.get("Product_Description")
                route = d.get("Route_of_Administration")
                target = d.get("Target")
                molecule_type = d.get("Molecule_Type")
                atc = d.get("ATC_Classification")
                mechanism = d.get("Mechanism_of_Action")
                mono = d.get("MonoCombinationDrug")
                pipeline = d.get("PipelineDetails") or []

                for p in pipeline:
                    rows.append(
                        {
                            "name": co_name,
                            "drug_name": name,
                            "alias": alias,
                            "description": description,
                            "route_of_administration": route,
                            "target": target,
                            "molecule_type": molecule_type,
                            "ATC_classification": atc,
                            "mechanism_of_action": mechanism,
                            "mono_combination": mono,
                            "stage": p.get("Development_Stage"),
                            "indication": p.get("Indication"),
                            "therapy_area": p.get("Therapy_Area"),
                            "geography": p.get("Product_Geography"),
                            "line_of_therapy": p.get("Line_of_Therapy"),
                            "last_development_stage": p.get("Last_Development_Stage"),
                            "reason_for_discontinuation": p.get("Reason_for_Discontinuation"),
                            "date_of_discontinuation": p.get("Inactive_Discontinued_Date"),
                        }
                    )

        return rows
