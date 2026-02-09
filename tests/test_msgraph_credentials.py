#!/usr/bin/env python3
"""
Test script to verify Microsoft Graph API credentials from AWS Secrets Manager.
"""

import json
import asyncio
import boto3
import httpx
import msal


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
        print("✓ Successfully loaded secrets from AWS")
        return secrets
    except Exception as e:
        print(f"✗ Failed to fetch AWS secrets: {e}")
        return {}


async def test_credentials():
    print("=" * 60)
    print("Testing Microsoft Graph API Credentials")
    print("=" * 60)
    
    # Load secrets
    secrets = get_aws_secrets()
    
    client_id = secrets.get('ms_graphapi_client_id')
    client_secret = secrets.get('ms_graphapi_client_secret')
    tenant_id = secrets.get('ms_graphapi_tenant_id')
    
    print(f"\n  Credentials found:")
    print(f"    Tenant ID: {tenant_id}")
    print(f"    Client ID: {client_id[:8]}..." if client_id else "    Client ID: NOT FOUND")
    print(f"    Client Secret: {'*' * 10}" if client_secret else "    Client Secret: NOT FOUND")
    
    if not all([client_id, client_secret, tenant_id]):
        print("\n✗ Missing required credentials")
        return
    
    # Test 1: Check Azure OIDC endpoints
    print(f"\n" + "-" * 60)
    print("TEST 1: Azure OIDC Endpoint Connectivity")
    print("-" * 60)
    
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    async with httpx.AsyncClient() as client:
        # OpenID Configuration
        try:
            resp = await client.get(f"{authority}/v2.0/.well-known/openid-configuration")
            if resp.status_code == 200:
                config = resp.json()
                print(f"  ✓ OpenID Config: OK")
                print(f"    Issuer: {config.get('issuer')}")
            else:
                print(f"  ✗ OpenID Config: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  ✗ OpenID Config: {e}")
    
    # Test 2: Client Credentials Flow (app-only authentication)
    print(f"\n" + "-" * 60)
    print("TEST 2: Client Credentials Flow (App-Only Auth)")
    print("-" * 60)
    
    try:
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )
        
        # Request token for Microsoft Graph
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            print(f"  ✓ Client credentials flow: SUCCESS")
            print(f"    Token type: {result.get('token_type')}")
            print(f"    Expires in: {result.get('expires_in')} seconds")
            
            # Try to call Microsoft Graph API
            print(f"\n  Testing Graph API call...")
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {result['access_token']}"}
                resp = await client.get(
                    "https://graph.microsoft.com/v1.0/organization",
                    headers=headers
                )
                if resp.status_code == 200:
                    org = resp.json().get('value', [{}])[0]
                    print(f"  ✓ Graph API call: SUCCESS")
                    print(f"    Organization: {org.get('displayName', 'N/A')}")
                else:
                    print(f"  ✗ Graph API call: HTTP {resp.status_code}")
                    print(f"    {resp.text[:200]}")
        else:
            print(f"  ✗ Client credentials flow: FAILED")
            print(f"    Error: {result.get('error')}")
            print(f"    Description: {result.get('error_description')}")
    except Exception as e:
        print(f"  ✗ Client credentials flow: {e}")
    
    # Test 3: Device Code Flow (interactive user authentication)
    print(f"\n" + "-" * 60)
    print("TEST 3: Device Code Flow (User Auth) - OPTIONAL")
    print("-" * 60)
    
    response = input("  Do you want to test interactive login? (y/n): ").strip().lower()
    
    if response == 'y':
        try:
            # For user auth, we need a public client app
            public_app = msal.PublicClientApplication(
                client_id=client_id,
                authority=authority,
            )
            
            scopes = ["openid", "profile", "email", "User.Read"]
            flow = public_app.initiate_device_flow(scopes=scopes)
            
            if "user_code" not in flow:
                print(f"  ✗ Device flow failed: {flow.get('error_description')}")
            else:
                print(f"\n  To sign in:")
                print(f"  1. Open: {flow['verification_uri']}")
                print(f"  2. Enter code: {flow['user_code']}")
                print(f"\n  Waiting for authentication...")
                
                result = public_app.acquire_token_by_device_flow(flow)
                
                if "access_token" in result:
                    claims = result.get("id_token_claims", {})
                    print(f"\n  ✓ User authentication: SUCCESS")
                    print(f"    Name: {claims.get('name', 'N/A')}")
                    print(f"    Email: {claims.get('preferred_username', 'N/A')}")
                    print(f"    Object ID: {claims.get('oid', 'N/A')}")
                    
                    # Check groups if present
                    groups = claims.get('groups', [])
                    if groups:
                        print(f"    Groups: {len(groups)} group(s)")
                    else:
                        print(f"    Groups: None in token (may need to configure groups claim)")
                else:
                    print(f"  ✗ User authentication: FAILED")
                    print(f"    Error: {result.get('error_description')}")
        except Exception as e:
            print(f"  ✗ Device flow error: {e}")
    else:
        print("  Skipped.")
    
    # Summary
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"""
  Credentials Location: AWS Secrets Manager ('resource_logins')
  
  Keys to use in MCP server config:
    - ms_graphapi_tenant_id: {tenant_id}
    - ms_graphapi_client_id: {client_id[:20]}...
    - ms_graphapi_client_secret: (hidden)
  
  If all tests passed, these credentials can be used for the MCP server!
""")


if __name__ == "__main__":
    asyncio.run(test_credentials())