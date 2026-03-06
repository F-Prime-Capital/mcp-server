# F-Prime Remote MCP Server

This repository now runs as a **true remote MCP server** using `FastMCP` with `streamable-http`.

## Teachable Moment: Local vs Remote MCP

- `stdio` transport: your MCP server runs as a local process launched by the client.
- `streamable-http` transport: clients connect over network to an MCP URL (`/mcp`).
- This project defaults to remote mode so multiple clients can connect to one hosted server.

## Available Tools

- `therapeutics_landscape`: query therapeutics data from Box/Websites/GlobalData.
- `search_network_by_natural_language`: call internal network-search backend with semantic and structured filters.

## Quick Start

1. Install:
```bash
pip install -e .
```

2. Configure environment:
```bash
cp .env.example .env
```

3. Run server:
```bash
export $(grep -v '^#' .env | xargs)
python -m fprime_mcp.main
```

4. Verify:
```bash
curl http://localhost:8000/healthz
```

Remote MCP endpoint:
- `http://localhost:8000/mcp`

## Docker

```bash
docker compose up --build
```

## Useful Runtime Variables

- `MCP_TRANSPORT`: `streamable-http` (default), `stdio`, or `sse`
- `MCP_PATH`: HTTP path for MCP transport (default `/mcp`)
- `NETWORK_SEARCHER_API_URL`: backend endpoint for network search requests
- `INTERNAL_API_KEY`: bearer token passed to the network-search backend

## Security Note

This repo exposes MCP over HTTP. For production, place it behind HTTPS and an auth gateway
(for example Caddy/Nginx/Cloudflare Access) so only authorized clients can connect.
