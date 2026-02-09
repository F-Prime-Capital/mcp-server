#!/usr/bin/env python3
"""
F-Prime MCP Server - Authentication Testing Script

Run this script to test your Microsoft Entra ID authentication setup.
Usage: python test_auth.py
"""

import json
import asyncio
from datetime import datetime, timedelta

import boto3
import httpx
import msal
from jose import jwt


TENANT_ID = "7c2f7d68-9e11-48ca-81bd-362a0baa5fc2"
FPRIME_GROUP_ID = None  # Optional - set if you want to restrict to a specific group
SERVER_URL = "http://localhost:8000"


def get_aws_secrets() -> dict:
    """Fetch secrets from AWS Secrets Manager."""
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name='us-east-2'
        )
        response = client.get_secret_value(SecretId='resource_logins')
        secrets = json.loads(response['SecretString'])
        print("✓ Successfully loaded secrets from AWS Secrets Manager")
        return secrets
    except Exception as e:
        print(f"✗ Failed to fetch AWS secrets: {e}")
        print("  Make sure you have AWS credentials configured")
        return {}


async def test_azure_connectivity(client_id: str):
    """Test connectivity to Azure Entra ID endpoints."""
    print("\n" + "=" * 60)
    print("TEST 1: Azure Entra ID Connectivity")
    print("=" * 60)
    
    endpoints = {
        "OpenID Configuration": f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration",
        "JWKS (Keys)": f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys",
    }
    
    async with httpx.AsyncClient() as client:
        for name, url in endpoints.items():
            try:
                resp = await client.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if "issuer" in data:
                        print(f"  ✓ {name}: OK (Issuer: {data['issuer']})")
                    else:
                        print(f"  ✓ {name}: OK (Keys found: {len(data.get('keys', []))})")
                else:
                    print(f"  ✗ {name}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"  ✗ {name}: {e}")


async def test_server_connectivity():
    """Test connectivity to the MCP server."""
    print("\n" + "=" * 60)
    print("TEST 2: MCP Server Connectivity")
    print("=" * 60)
    
    endpoints = [
        ("Health Check", f"{SERVER_URL}/health"),
        ("Root", f"{SERVER_URL}/"),
    ]
    
    async with httpx.AsyncClient() as client:
        for name, url in endpoints:
            try:
                resp = await client.get(url, timeout=10)
                print(f"  ✓ {name}: HTTP {resp.status_code}")
            except httpx.ConnectError:
                print(f"  ✗ {name}: Connection failed - Is the server running?")
            except Exception as e:
                print(f"  ✗ {name}: {e}")


def authenticate_device_code(client_id: str) -> dict | None:
    """Authenticate using device code flow."""
    print("\n" + "=" * 60)
    print("TEST 3: Device Code Authentication")
    print("=" * 60)
    
    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    )
    
    scopes = ["openid", "profile", "email", f"api://{client_id}/access"]
    
    flow = app.initiate_device_flow(scopes=scopes)
    
    if "user_code" not in flow:
        print(f"  ✗ Failed to create device flow: {flow.get('error_description', 'Unknown error')}")
        return None
    
    print(f"\n  To sign in:")
    print(f"  1. Open: {flow['verification_uri']}")
    print(f"  2. Enter code: {flow['user_code']}")
    print(f"\n  Waiting for authentication...")
    
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" in result:
        claims = result.get("id_token_claims", {})
        print(f"\n  ✓ Authentication successful!")
        print(f"    User: {claims.get('name', 'Unknown')}")
        print(f"    Email: {claims.get('preferred_username', 'Unknown')}")
        return {
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token"),
            "id_token": result.get("id_token"),
            "expires_in": result.get("expires_in", 3600),
        }
    else:
        print(f"  ✗ Authentication failed: {result.get('error_description', 'Unknown error')}")
        return None


def inspect_token(token: str):
    """Decode and inspect the JWT token."""
    print("\n" + "=" * 60)
    print("TEST 4: Token Inspection")
    print("=" * 60)
    
    try:
        claims = jwt.get_unverified_claims(token)
        
        print(f"\n  Token Claims:")
        print(f"    Subject (sub): {claims.get('sub', 'N/A')}")
        print(f"    Object ID (oid): {claims.get('oid', 'N/A')}")
        print(f"    Name: {claims.get('name', 'N/A')}")
        print(f"    Email: {claims.get('preferred_username', 'N/A')}")
        print(f"    Audience: {claims.get('aud', 'N/A')}")
        print(f"    Issuer: {claims.get('iss', 'N/A')}")
        
        # Expiration
        exp = claims.get('exp')
        if exp:
            exp_time = datetime.fromtimestamp(exp)
            print(f"    Expires: {exp_time.isoformat()}")
        
        # Groups
        groups = claims.get('groups', [])
        print(f"    Groups: {len(groups)} group(s)")
        for g in groups[:5]:
            print(f"      - {g}")
        if len(groups) > 5:
            print(f"      ... and {len(groups) - 5} more")
        
        # Roles
        roles = claims.get('roles', [])
        print(f"    Roles: {roles if roles else 'None'}")
        
        # Check F-Prime membership
        print(f"\n  Access Check:")
        
        if FPRIME_GROUP_ID:
            print(f"    Group restriction enabled: {FPRIME_GROUP_ID}")
            if FPRIME_GROUP_ID in groups:
                print(f"    ✓ User IS in the required group")
            elif "FPrime.Member" in roles:
                print(f"    ✓ User has the required role")
            else:
                print(f"    ✗ User is NOT in the required group")
        else:
            print(f"    No group restriction - all tenant users allowed")
            print(f"    ✓ User is authenticated and authorized")
        
        return claims
        
    except Exception as e:
        print(f"  ✗ Failed to decode token: {e}")
        return None


async def test_authenticated_api(access_token: str):
    """Test authenticated API calls."""
    print("\n" + "=" * 60)
    print("TEST 5: Authenticated API Calls")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    tests = [
        ("GET", "/auth/me", None),
        ("GET", "/mcp/tools", None),
        ("POST", "/mcp/tools/call", {"name": "fprime_search_projects", "arguments": {"query": "test"}}),
    ]
    
    async with httpx.AsyncClient(base_url=SERVER_URL) as client:
        for method, path, body in tests:
            try:
                if method == "GET":
                    resp = await client.get(path, headers=headers, timeout=10)
                else:
                    resp = await client.post(path, headers=headers, json=body, timeout=10)
                
                status = "✓" if resp.status_code == 200 else "✗"
                print(f"  {status} {method} {path}: HTTP {resp.status_code}")
                
                if resp.status_code == 200:
                    data = resp.json()
                    preview = json.dumps(data)[:80]
                    print(f"      Response: {preview}...")
                elif resp.status_code in [401, 403]:
                    print(f"      {resp.json().get('detail', resp.text)}")
                    
            except httpx.ConnectError:
                print(f"  ✗ {method} {path}: Server not running")
            except Exception as e:
                print(f"  ✗ {method} {path}: {e}")


async def validate_token_signature(token: str):
    """Validate token signature against Azure JWKS."""
    print("\n" + "=" * 60)
    print("TEST 6: Token Signature Validation")
    print("=" * 60)
    
    from jose import jwt as jose_jwt
    from jose.exceptions import JWTError, ExpiredSignatureError
    
    jwks_url = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
    
    async with httpx.AsyncClient() as client:
        print(f"  Fetching JWKS from Azure...")
        resp = await client.get(jwks_url)
        jwks = resp.json()
        print(f"  Found {len(jwks.get('keys', []))} keys")
        
        header = jose_jwt.get_unverified_header(token)
        kid = header.get('kid')
        print(f"  Token key ID: {kid}")
        
        rsa_key = None
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                rsa_key = key
                break
        
        if not rsa_key:
            print("  ✗ No matching key found in JWKS")
            return False
        
        print("  ✓ Found matching key")
        
        try:
            claims = jose_jwt.get_unverified_claims(token)
            audience = claims.get('aud')
            issuer = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
            
            jose_jwt.decode(
                token,
                rsa_key,
                algorithms=['RS256'],
                audience=audience,
                issuer=issuer,
                options={'verify_exp': True}
            )
            
            print("  ✓ Token signature is VALID")
            return True
            
        except ExpiredSignatureError:
            print("  ✗ Token has EXPIRED")
            return False
        except JWTError as e:
            print(f"  ✗ Token validation FAILED: {e}")
            return False


# =============================================================================
# MAIN
# =============================================================================

async def main():
    print("=" * 60)
    print("F-Prime MCP Server - Authentication Test Suite")
    print("=" * 60)
    
    # Load secrets from AWS
    secrets = get_aws_secrets()
    
    client_id = secrets.get('entra_mcp_clientid')
    client_secret = secrets.get('entra_mcp_secret')
    
    if not client_id:
        print("\n✗ Could not load client_id from AWS Secrets Manager")
        print("  Make sure 'entra_mcp_clientid' exists in the 'resource_logins' secret")
        return
    
    print(f"\n  Client ID: {client_id[:8]}...")
    print(f"  Client Secret: {'*' * 10} (loaded)")
    print(f"  Tenant ID: {TENANT_ID}")
    
    # Run tests
    await test_azure_connectivity(client_id)
    await test_server_connectivity()
    
    # Authenticate
    tokens = authenticate_device_code(client_id)
    
    if tokens:
        inspect_token(tokens["access_token"])
        await validate_token_signature(tokens["access_token"])
        await test_authenticated_api(tokens["access_token"])
        
        # Save token for later use
        with open(".fprime_token", "w") as f:
            json.dump(tokens, f, indent=2)
        print(f"\n✓ Token saved to .fprime_token")
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())