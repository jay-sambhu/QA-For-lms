#!/usr/bin/env python3
"""
JASUSS Authentication & Domain Configuration Verifier
=====================================================
Validates Supabase authentication provider status, Google OAuth configuration,
and production redirect targets against live service endpoints.

Run standalone or as a pre-deploy / CI health check:
    python3 scripts/verify_auth_config.py
"""

import os
import sys
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import load_dotenv

# Load root .env
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

DEFAULT_PRODUCTION_DOMAINS = [
    "https://www.jasuss.tech",
    "https://jasuss.tech",
    "https://web-two-flame-39.vercel.app",
]

def verify_auth_configuration(target_domains=None):
    if target_domains is None:
        target_domains = DEFAULT_PRODUCTION_DOMAINS

    print("=======================================================================")
    print("           JASUSS AUTHENTICATION & DOMAIN HEALTH VERIFIER             ")
    print("=======================================================================\n")

    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    expected_google_client_id = os.getenv("NEXT_PUBLIC_GOOGLE_CLIENT_ID")

    errors = []
    warnings = []

    # 1. Environment Variable Checks
    print("[1/3] Validating Environment Credentials...")
    if not supabase_url:
        errors.append("Missing NEXT_PUBLIC_SUPABASE_URL in environment.")
    else:
        print(f"  ✓ Supabase URL: {supabase_url}")

    if not supabase_service_key:
        errors.append("Missing SUPABASE_SERVICE_ROLE_KEY / ANON_KEY in environment.")
    else:
        print("  ✓ Supabase API Key: Present")

    if not expected_google_client_id:
        warnings.append("NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set in backend environment.")
    else:
        print(f"  ✓ Expected Google Client ID: {expected_google_client_id[:20]}...")

    if errors:
        for err in errors:
            print(f"  ✕ ERROR: {err}")
        return False

    # 2. Query Supabase Settings (/auth/v1/settings)
    print("\n[2/3] Querying Supabase Auth Engine Settings...")
    try:
        settings_resp = requests.get(
            f"{supabase_url.rstrip('/')}/auth/v1/settings",
            headers={"apikey": supabase_service_key, "Authorization": f"Bearer {supabase_service_key}"},
            timeout=10,
        )
        if settings_resp.status_code != 200:
            errors.append(f"Failed to fetch /auth/v1/settings (HTTP {settings_resp.status_code}): {settings_resp.text}")
        else:
            settings_data = settings_resp.json()
            external_providers = settings_data.get("external", {})
            google_enabled = external_providers.get("google")

            if google_enabled is True:
                print("  ✓ Google OAuth Provider: ENABLED in Supabase")
            else:
                errors.append("Google OAuth provider is DISABLED in Supabase (external.google is false).")

            # Note API limitation per Supabase GoTrue security design:
            print("  ℹ Note on Supabase API limitation: GoTrue's public /auth/v1/settings endpoint")
            print("    intentionally does NOT expose 'site_url' or 'uri_allow_list' to project keys.")
            print("    Allowlist entries must be verified via authorization redirects and Dashboard.")
    except Exception as exc:
        errors.append(f"Network error querying Supabase settings: {exc}")

    # 3. Simulate OAuth Authorize Redirects for Production Domains
    print("\n[3/3] Testing OAuth Authorize Redirect Handlers...")
    for domain in target_domains:
        callback_url = f"{domain.rstrip('/')}/auth/callback"
        auth_endpoint = f"{supabase_url.rstrip('/')}/auth/v1/authorize?provider=google&redirect_to={callback_url}"

        try:
            resp = requests.get(auth_endpoint, allow_redirects=False, timeout=10)
            if resp.status_code != 302:
                errors.append(f"Domain {domain}: expected HTTP 302 redirect from /auth/v1/authorize, got HTTP {resp.status_code}")
                continue

            location = resp.headers.get("Location", "")
            if not location:
                errors.append(f"Domain {domain}: missing Location header in authorize response")
                continue

            parsed = urlparse(location)
            params = parse_qs(parsed.query)

            # Check destination host
            if "accounts.google.com" not in parsed.netloc:
                # If Supabase immediately bounced to localhost or site_url
                errors.append(
                    f"Domain {domain}: Redirect did not target Google. Destination: {location}. "
                    f"This indicates the domain was rejected by Supabase and fell back to Site URL."
                )
                continue

            # Verify redirect_to parameter preserved
            forwarded_redirect_to = params.get("redirect_to", [""])[0]
            if forwarded_redirect_to != callback_url:
                errors.append(
                    f"Domain {domain}: forwarded redirect_to mismatch. Expected '{callback_url}', got '{forwarded_redirect_to}'"
                )
                continue

            # Verify Google Client ID
            google_client_in_redirect = params.get("client_id", [""])[0]
            if expected_google_client_id and google_client_in_redirect != expected_google_client_id:
                warnings.append(
                    f"Domain {domain}: Google Client ID mismatch. Supabase sends '{google_client_in_redirect}', "
                    f"local env expects '{expected_google_client_id}'"
                )

            print(f"  ✓ {domain} ➔ Google OAuth Authorize Redirect: VALID")

        except Exception as exc:
            errors.append(f"Domain {domain}: Exception during OAuth authorization check: {exc}")

    # Final summary
    print("\n=======================================================================")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  ! {w}")
    if errors:
        print("FAILURE DETECTED:")
        for err in errors:
            print(f"  ✕ {err}")
        print("\nAction Required:")
        print("  1. Check Supabase Dashboard ➔ Authentication ➔ URL Configuration")
        print("     Ensure Site URL is https://www.jasuss.tech and Redirect URLs include all production domains.")
        print("  2. Check Google Cloud Console ➔ Credentials ➔ OAuth Client ID")
        print("     Ensure Authorized JavaScript origins and redirect URIs are configured.")
        print("=======================================================================")
        return False

    print("ALL AUTHENTICATION CHECKS PASSED (Ready for Production)")
    print("=======================================================================")
    return True

if __name__ == "__main__":
    success = verify_auth_configuration()
    sys.exit(0 if success else 1)
