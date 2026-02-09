#!/usr/bin/env python3
"""
Test script for entra_mcp credentials from webpage_token secret.
"""

import json
import asyncio
import boto3
import httpx
import msal


def get_mcp_credentials() -> dict:
    """Fetch MCP credentials from AWS Secrets Manager (webpage_token)."""
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name='us-east-2'
        )
        response = client.get_secret_value(SecretId='webpage_token')
        secrets = json.loads(response['SecretString'])
        print("✓ Successfully loaded secrets from AWS (webpage_token)")
        
        # Show available keys
        print(f"  Available keys: {list(secrets.keys())}")
        
        return {
            'client_id': secrets.get('entra_mcp_clientid'),
            'client_secret': secrets.get('entra_mcp_clientsecret'),
            'tenant_id': '7c2f7d68-9e11-48ca-81bd-362a0baa5fc2',
        }
    except Exception as e:
        print(f"✗ Failed to fetch AWS secrets: {e}")
        return {}


async def test_credentials():
    print("=" * 60)
    print("Testing Entra MCP Credentials")
    print("=" * 60)
    
    creds = get_mcp_credentials()
    
    client_id = creds.get('client_id')
    client_secret = creds.get('client_secret')
    tenant_id = creds.get('tenant_id')
    
    print(f"\n  Credentials:")
    print(f"    Tenant ID: {tenant_id}")
    print(f"    Client ID: {client_id[:12]}..." if client_id else "    Client ID: NOT FOUND")
    print(f"    Client Secret: {'*' * 10}" if client_secret else "    Client Secret: NOT FOUND")
    
    if not client_id:
        print("\n✗ 'entra_mcp_clientid' not found in webpage_token secret")
        print("  You may need to add it to AWS Secrets Manager")
        return
    
    if not client_secret:
        print("\n✗ 'entra_mcp_secret' not found in webpage_token secret")
        print("  You may need to add it to AWS Secrets Manager")
        return
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    # Test 1: OIDC Endpoints
    print(f"\n" + "-" * 60)
    print("TEST 1: Azure OIDC Endpoints")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{authority}/v2.0/.well-known/openid-configuration")
        if resp.status_code == 200:
            print(f"  ✓ OpenID Configuration: OK")
        else:
            print(f"  ✗ OpenID Configuration: HTTP {resp.status_code}")
    
    # Test 2: Device Code Flow (User Authentication)
    print(f"\n" + "-" * 60)
    print("TEST 2: Device Code Flow (Interactive User Login)")
    print("-" * 60)
    
    try:
        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
        )
        
        # Same scopes as the working config
        scopes = ["openid", "email", "profile"]
        flow = app.initiate_device_flow(scopes=scopes)
        
        if "user_code" not in flow:
            print(f"  ✗ Device flow failed: {flow.get('error')}")
            print(f"    {flow.get('error_description', '')}")
        else:
            print(f"\n  To sign in:")
            print(f"  ┌────────────────────────────────────────┐")
            print(f"  │  1. Open: {flow['verification_uri']:<28} │")
            print(f"  │  2. Enter code: {flow['user_code']:<21} │")
            print(f"  └────────────────────────────────────────┘")
            print(f"\n  Waiting for authentication...")
            
            result = app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                claims = result.get("id_token_claims", {})
                print(f"\n  ✓ Authentication SUCCESS!")
                print(f"    Name: {claims.get('name', 'N/A')}")
                print(f"    Email: {claims.get('preferred_username', 'N/A')}")
                print(f"    User ID (oid): {claims.get('oid', 'N/A')}")
                print(f"    Tenant ID (tid): {claims.get('tid', 'N/A')}")
                
                # Token info
                print(f"\n  Token Info:")
                print(f"    Access Token: {result['access_token'][:50]}...")
                print(f"    Expires In: {result.get('expires_in', 'N/A')} seconds")
                
                if result.get('refresh_token'):
                    print(f"    Refresh Token: ✓ Present")
                
                # Save for later testing
                with open(".mcp_test_token", "w") as f:
                    json.dump({
                        "access_token": result["access_token"],
                        "refresh_token": result.get("refresh_token"),
                        "id_token": result.get("id_token"),
                        "claims": claims,
                    }, f, indent=2)
                print(f"\n  ✓ Token saved to .mcp_test_token")
                
            else:
                print(f"\n  ✗ Authentication FAILED")
                print(f"    Error: {result.get('error')}")
                print(f"    Description: {result.get('error_description')}")
                
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Summary
    print(f"\n" + "=" * 60)
    print("CONFIGURATION FOR MCP SERVER")
    print("=" * 60)
    print(f"""
  Use these settings in your MCP server:
  
  AWS Secret: 'webpage_token'
  Keys:
    - entra_mcp_clientid
    - entra_mcp_secret
  
  Tenant ID: {tenant_id}
  Authority: {authority}
  Scopes: openid email profile
""")


if __name__ == "__main__":
    asyncio.run(test_credentials())