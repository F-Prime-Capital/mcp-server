#!/usr/bin/env python3
"""
Test script for MCP Server OIDC authentication flow.
Based on the existing F-Prime OIDC test pattern.
"""

import requests
from urllib.parse import urlparse, parse_qs
import base64
import json

BASE_URL = "http://localhost:8000"
AUTH_LOGIN = f"{BASE_URL}/auth/login"
AUTH_CALLBACK = f"{BASE_URL}/auth/callback"
AUTH_USER = f"{BASE_URL}/auth/user"
AUTH_LOGOUT = f"{BASE_URL}/auth/logout"


def extract_token_from_url(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return {
        "token": params.get("token", [None])[0],
        "all_params": {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    }


def validate_token(token):
    if not token:
        print("No token provided")
        return None
    
    parts = token.split('.')
    if len(parts) != 3:
        print(f"FAIL: Not a JWT ({len(parts)} parts)")
        return None
    
    try:
        header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
        print("PASS: Valid JWT")
        print(f"   Header: {header}")
        print(f"   Subject: {payload.get('sub', 'N/A')}")
        print(f"   Email: {payload.get('email', 'N/A')}")
        return payload
    except Exception as e:
        print(f"FAIL: Decode failed: {e}")
        return None


def test_login_redirect():
    print("=" * 50)
    print("Test 1: Login Redirect")
    print("=" * 50)
    try:
        r = requests.get(AUTH_LOGIN, allow_redirects=False, timeout=10)
        if r.status_code in [302, 303, 307]:
            url = r.headers.get("Location", "")
            params = parse_qs(urlparse(url).query)
            is_entra = "login.microsoftonline.com" in url
            print(f"{'PASS' if is_entra else 'FAIL'}: Redirect to Entra")
            print(f"   client_id: {'PASS' if 'client_id' in params else 'FAIL'}")
            print(f"   redirect_uri: {params.get('redirect_uri', ['N/A'])[0]}")
            print(f"   state: {'PASS' if 'state' in params else 'FAIL'}")
            print(f"   nonce: {'PASS' if 'nonce' in params else 'FAIL'}")
            print(f"   response_type: {params.get('response_type', ['N/A'])[0]}")
            print(f"   scope: {params.get('scope', ['N/A'])[0]}")
            return True
        else:
            print(f"FAIL: Expected redirect, got {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("FAIL: Connection failed - is the MCP server running?")
        print(f"   Try: uvicorn fprime_mcp.main:app --reload --port 8000")
        return False


def test_callback_security():
    print("\n" + "=" * 50)
    print("Test 2: Callback Security")
    print("=" * 50)
    
    # Test missing code
    r = requests.get(AUTH_CALLBACK, allow_redirects=False, timeout=10)
    missing_code_ok = r.status_code == 403
    print(f"Missing code: {r.status_code} ({'PASS - rejected' if missing_code_ok else 'FAIL - should reject'})")
    
    # Test invalid state
    r = requests.get(f"{AUTH_CALLBACK}?code=test&state=invalid", allow_redirects=False, timeout=10)
    invalid_state_ok = r.status_code == 403
    print(f"Invalid state: {r.status_code} ({'PASS - rejected' if invalid_state_ok else 'FAIL - should reject'})")
    
    return missing_code_ok and invalid_state_ok


def test_user_endpoint():
    print("\n" + "=" * 50)
    print("Test 3: User Endpoint (No Session)")
    print("=" * 50)
    r = requests.get(AUTH_USER, timeout=10)
    no_session_ok = r.status_code == 403
    print(f"No session: {r.status_code} ({'PASS - rejected' if no_session_ok else 'FAIL - should reject'})")
    return no_session_ok


def test_health_endpoint():
    print("\n" + "=" * 50)
    print("Test 4: Health Endpoint")
    print("=" * 50)
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        if r.status_code == 200:
            print(f"PASS: Health check OK")
            print(f"   Response: {r.json()}")
            return True
        else:
            print(f"FAIL: Health check returned {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("FAIL: Connection failed")
        return False


def print_summary(results):
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    print(f"\n   Tests passed: {passed}/{total}")
    print(f"""
Auth flow implementation check:
   - /auth/login redirects to Entra with proper params
   - /auth/callback validates state and rejects invalid requests  
   - /auth/user requires authentication
   - /health returns server status

To complete testing:
   1. Ensure 'Allow public client flows' is enabled in Azure
   2. Add http://localhost:8000/auth/callback to Entra app redirect URIs
   3. Start the server: uvicorn fprime_mcp.main:app --reload --port 8000
   4. Visit http://localhost:8000/auth/login in your browser
""")


def test_manual_login():
    print("\n" + "=" * 50)
    print("Test 5: Manual Login Test")
    print("=" * 50)
    
    response = input("Do you want to test manual login? (y/n): ").strip().lower()
    if response != 'y':
        print("Skipped")
        return
    
    print(f"\n1. Open in browser: {AUTH_LOGIN}")
    print("2. Complete Microsoft login")
    print("3. After redirect, check if you're logged in")
    
    input("\nPress Enter after completing login...")
    
    # Test with session cookie (user would need to provide it)
    cookie = input("Paste the 'mcp_session' cookie value (or Enter to skip): ").strip()
    
    if cookie:
        r = requests.get(AUTH_USER, cookies={"mcp_session": cookie}, timeout=10)
        if r.status_code == 200:
            user = r.json()
            print(f"\nPASS: Authenticated!")
            print(f"   Email: {user.get('email', 'N/A')}")
            print(f"   Name: {user.get('name', 'N/A')}")
        else:
            print(f"\nFAIL: {r.status_code} - {r.text}")
    else:
        print("Skipped")


if __name__ == "__main__":
    results = []
    
    results.append(test_health_endpoint())
    results.append(test_login_redirect())
    results.append(test_callback_security())
    results.append(test_user_endpoint())
    
    print_summary(results)
    
    test_manual_login()