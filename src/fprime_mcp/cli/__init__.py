"""CLI for F-Prime MCP Server authentication and testing."""

import argparse
import asyncio
import json
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading

import httpx
import msal

from fprime_mcp.config import get_settings


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback in local server."""

    auth_code = None
    state = None

    def do_GET(self):
        """Handle GET request with OAuth callback."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            OAuthCallbackHandler.state = params.get("state", [None])[0]

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            """)
        else:
            error = params.get("error", ["Unknown error"])[0]
            error_desc = params.get("error_description", [""])[0]

            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>Authentication Failed</h1>
                    <p>{error}: {error_desc}</p>
                </body>
                </html>
            """.encode())

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def login_interactive():
    """Perform interactive login using device code or browser flow."""
    settings = get_settings()

    # Use MSAL for authentication
    app = msal.PublicClientApplication(
        client_id=settings.azure_client_id,
        authority=settings.oidc_authority,
    )

    # Try browser-based login first
    print("Starting authentication...")
    print("A browser window will open for you to sign in.\n")

    # Start local callback server
    callback_port = 8400
    redirect_uri = f"http://localhost:{callback_port}/callback"

    server = HTTPServer(("localhost", callback_port), OAuthCallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()

    # Build auth URL and open browser
    scopes = [f"api://{settings.azure_client_id}/access"]

    flow = app.initiate_auth_code_flow(
        scopes=scopes,
        redirect_uri=redirect_uri,
    )

    auth_url = flow["auth_uri"]
    print(f"Opening browser to: {auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    server_thread.join(timeout=120)

    if OAuthCallbackHandler.auth_code:
        # Exchange code for tokens
        result = app.acquire_token_by_auth_code_flow(
            flow,
            {"code": OAuthCallbackHandler.auth_code},
        )

        if "access_token" in result:
            print("✓ Authentication successful!")
            print(f"  User: {result.get('id_token_claims', {}).get('preferred_username', 'Unknown')}")

            # Save token to config file
            token_file = ".fprime_token"
            with open(token_file, "w") as f:
                json.dump({
                    "access_token": result["access_token"],
                    "refresh_token": result.get("refresh_token"),
                    "expires_in": result.get("expires_in", 3600),
                }, f)

            print(f"\n  Token saved to {token_file}")
            print("  You can now use the MCP server.")
            return True
        else:
            print(f"✗ Authentication failed: {result.get('error_description', 'Unknown error')}")
            return False
    else:
        print("✗ Authentication timed out or was cancelled.")
        return False


def login_device_code():
    """Perform login using device code flow (for headless environments)."""
    settings = get_settings()

    app = msal.PublicClientApplication(
        client_id=settings.azure_client_id,
        authority=settings.oidc_authority,
    )

    scopes = [f"api://{settings.azure_client_id}/access"]
    flow = app.initiate_device_flow(scopes=scopes)

    if "user_code" not in flow:
        print(f"✗ Failed to initiate device flow: {flow.get('error_description', 'Unknown error')}")
        return False

    print(flow["message"])
    print("\nWaiting for authentication...")

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        print("\n✓ Authentication successful!")

        token_file = ".fprime_token"
        with open(token_file, "w") as f:
            json.dump({
                "access_token": result["access_token"],
                "refresh_token": result.get("refresh_token"),
                "expires_in": result.get("expires_in", 3600),
            }, f)

        print(f"  Token saved to {token_file}")
        return True
    else:
        print(f"\n✗ Authentication failed: {result.get('error_description', 'Unknown error')}")
        return False


async def test_connection(server_url: str = "http://localhost:8000"):
    """Test connection to the MCP server."""
    try:
        # Load token
        try:
            with open(".fprime_token") as f:
                token_data = json.load(f)
                access_token = token_data["access_token"]
        except FileNotFoundError:
            print("✗ No token found. Run 'fprime-mcp login' first.")
            return False

        async with httpx.AsyncClient() as client:
            # Test authentication
            resp = await client.get(
                f"{server_url}/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if resp.status_code == 200:
                user = resp.json()
                print("✓ Connection successful!")
                print(f"  User: {user['display_name']}")
                print(f"  Email: {user['email']}")
                print(f"  F-Prime Member: {user['is_fprime_member']}")

                # List available tools
                tools_resp = await client.get(
                    f"{server_url}/mcp/tools",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if tools_resp.status_code == 200:
                    tools = tools_resp.json()["tools"]
                    print(f"\n  Available tools ({len(tools)}):")
                    for tool in tools:
                        print(f"    - {tool['name']}: {tool['description'][:50]}...")

                return True
            elif resp.status_code == 401:
                print("✗ Authentication failed. Token may be expired.")
                print("  Run 'fprime-mcp login' to re-authenticate.")
                return False
            elif resp.status_code == 403:
                print("✗ Access denied. You may not be an F-Prime member.")
                return False
            else:
                print(f"✗ Server error: {resp.status_code}")
                return False

    except httpx.ConnectError:
        print(f"✗ Cannot connect to server at {server_url}")
        print("  Is the server running?")
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="F-Prime MCP Server CLI",
        prog="fprime-mcp",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Login command
    login_parser = subparsers.add_parser("login", help="Authenticate with Microsoft Entra ID")
    login_parser.add_argument(
        "--device-code",
        action="store_true",
        help="Use device code flow (for headless environments)",
    )

    # Test connection command
    test_parser = subparsers.add_parser("test-connection", help="Test connection to MCP server")
    test_parser.add_argument(
        "--server",
        default="http://localhost:8000",
        help="Server URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    if args.command == "login":
        if args.device_code:
            success = login_device_code()
        else:
            success = login_interactive()
        sys.exit(0 if success else 1)

    elif args.command == "test-connection":
        success = asyncio.run(test_connection(args.server))
        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()