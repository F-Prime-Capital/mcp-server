# F-Prime MCP Server

A secure MCP (Model Context Protocol) server for F-Prime internal tools, protected by Microsoft Entra ID authentication using OIDC.

## Features

- 🔐 Microsoft Entra ID OIDC authentication
- 🛠️ Extensible tool framework
- 🚀 FastAPI-based server
- ☁️ AWS Secrets Manager integration

## Quick Start

### 1. Azure Setup

Ensure your Azure app registration has:
- Redirect URI: `http://localhost:8000/auth/callback`
- "Allow public client flows" enabled

### 2. AWS Setup

Credentials are loaded from AWS Secrets Manager (`webpage_token` secret):
- `entra_mcp_clientid`
- `entra_mcp_clientsecret`

### 3. Installation

```bash
git clone https://github.com/fprime/fprime-mcp-server.git
cd fprime-mcp-server
pip install -e .
```

### 4. Run the Server

```bash
uvicorn fprime_mcp.main:app --reload --port 8000
```

### 5. Test Authentication

```bash
python tests/test_oidc_flow.py
```

Or visit `http://localhost:8000/auth/login` in your browser.

## Project Structure

```
fprime-mcp-server/
├── src/fprime_mcp/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   └── auth/
│       ├── __init__.py
│       ├── oidc_config.py   # OIDC configuration
│       └── routes.py        # Auth endpoints
├── tests/
│   └── test_oidc_flow.py    # Auth flow tests
├── pyproject.toml
└── README.md
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /auth/login` | Start OIDC login flow |
| `GET /auth/callback` | OIDC callback handler |
| `GET /auth/user` | Get current user info |
| `GET /auth/logout` | Log out |
| `GET /mcp/tools` | List available tools (auth required) |
| `POST /mcp/tools/call` | Call a tool (auth required) |

## License

MIT License