# MCP Server (F-Prime internal tools)

This repository contains an MCP server intended to expose F-Prime internal workflows as MCP tools.

## Tools exposed

Implemented / partially implemented:
- **Research Portal** (`research_portal`): company research entry-point. Currently maps `company_search` to the existing `get_similars` proxy endpoint and supports `founder_exec_info`, `theme_description`, and `map_theme` via proxy.
- **Get Contact Info** (`get_contact_info`): uses the proxy endpoint `get_email_address`. Optionally also pulls founder/exec info if `find_founders=true` and `domain` is provided.
- **Similar Companies** (`similar_companies`): uses the proxy endpoint `get_similars` (tech-only today).
- **Similar People** (`similar_people`): uses the proxy endpoint `get_similar_people`.
- **Therapeutics Landscape** (`therapeutics_landscape`): searches by target/gene, indication, and/or molecule type across:
  - Box metadata (Airtable)
  - scraped websites (Airtable)
  - GlobalData
  and can optionally export results as an Excel file (base64).

Skeleton tools (stubbed, to be wired to the real backend later):
- `subscriptions`
- `resources`
- `llm_tools`
- `memo_writer`
- `publics`
- `preprints`
- `hc_box_search`
- `hc_sourcing`
- `tech_box_search`
- `fsv_sharepoint_search`
- `healthcare_voting`
- `tech_voting`
- `publics_report`
- `accounts_receivable`

## Configuration

### Proxy-backed tools
Set these environment variables to enable the proxy-backed tools:
- `VC_PROXY_API_URL` (required)
- `VC_PROXY_AUTH_TOKEN` (optional default token for local testing)
- `HTTP_TIMEOUT_S` (optional)

### Therapeutics Landscape
Therapeutics Landscape can be configured either via direct env vars or AWS Secrets Manager fallback.

**Option A: env vars**
- `AIRTABLE_API_KEY`
- `GLOBALDATA_TOKEN`

**Option B: Secrets Manager fallback (mirrors the reference Lambda)**
- `USE_SECRETS_MANAGER=1`
- `RESOURCE_LOGINS_SECRET_NAME=resource_logins`
- `AWS_REGION=us-east-2`

Optional overrides:
- `GLOBALDATA_ENDPOINT`
- `TL_BOX_BASE_ID`, `TL_BOX_TABLE_ID`
- `TL_WEBSITE_BASE_ID`, `TL_WEBSITE_TABLE_ID`
- `TL_CACHE_TTL_S`, `TL_CACHE_MAXSIZE`

Python deps (needed for specific tools):
- Proxy-backed tools: `requests`
- Therapeutics Landscape: `requests`, `pyairtable`; for Excel downloads: `pandas`, `openpyxl`

## Running

```bash
python server.py
```

The server runs over stdio by default.
