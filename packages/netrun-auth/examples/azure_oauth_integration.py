"""
Example: Azure AD and OAuth Integration Usage

Demonstrates how to use netrun-auth v1.0.0 integrations:
- Azure AD authentication (authorization code flow)
- Azure AD client credentials (service-to-service)
- Generic OAuth (Google, GitHub)
- Multi-tenant Azure AD
- FastAPI integration

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-25
"""

import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from netrun_auth.integrations import (
    # Azure AD
    AzureADConfig,
    AzureADClient,
    AzureADMultiTenantClient,
    initialize_azure_ad,
    get_current_user_azure,
    # OAuth
    OAuthProvider,
    OAuthConfig,
    OAuthManager,
    create_oauth_router,
)


# Example 1: Azure AD Authorization Code Flow (Web Application)
def example_azure_ad_web_app():
    """Example: Azure AD authentication for web application."""

    # Configure Azure AD
    config = AzureADConfig(
        tenant_id="[AZURE_TENANT_ID]",  # Replace with your tenant ID
        client_id="[AZURE_CLIENT_ID]",  # Replace with your client ID
        client_secret="[AZURE_CLIENT_SECRET]",  # Replace with your client secret
        redirect_uri="http://localhost:8000/auth/azure/callback",
        scopes=["User.Read", "offline_access"]
    )

    # Create Azure AD client
    azure_client = AzureADClient(config)

    # Generate authorization URL
    auth_url, state = azure_client.get_authorization_url(use_pkce=True)

    print(f"1. Redirect user to: {auth_url}")
    print(f"2. Store state in session: {state}")
    print("3. After user authorizes, they'll be redirected to your callback URL")

    return azure_client, state


# Example 2: Azure AD Callback Handler
async def example_azure_ad_callback(azure_client: AzureADClient, code: str, state: str):
    """Example: Handle Azure AD callback and validate token."""

    # Exchange authorization code for tokens
    tokens = await azure_client.exchange_code_for_tokens(code, state)

    print(f"Access token obtained (expires in {tokens['expires_in']}s)")

    # Validate and extract claims from access token
    azure_claims = await azure_client.validate_azure_token(tokens["access_token"])

    print(f"User ID: {azure_claims['oid']}")
    print(f"Email: {azure_claims.get('email', 'N/A')}")
    print(f"Tenant ID: {azure_claims['tid']}")

    # Get user profile from Microsoft Graph
    user_profile = await azure_client.get_user_profile(tokens["access_token"])

    print(f"User profile: {user_profile}")

    # Map Azure claims to local format
    local_claims = azure_client.map_azure_claims_to_local(azure_claims)

    print(f"Local claims: {local_claims}")

    return tokens, local_claims


# Example 3: Azure AD Client Credentials (Service-to-Service)
async def example_azure_ad_service_auth():
    """Example: Azure AD client credentials for service-to-service."""

    # Configure Azure AD for service-to-service
    config = AzureADConfig(
        tenant_id="[AZURE_TENANT_ID]",
        client_id="[AZURE_CLIENT_ID]",
        client_secret="[AZURE_CLIENT_SECRET]",
        scopes=[".default"]  # Use .default for client credentials
    )

    azure_client = AzureADClient(config)

    # Get client credentials token
    tokens = await azure_client.get_client_credentials_token()

    print(f"Service token obtained (expires in {tokens['expires_in']}s)")
    print(f"Access token: {tokens['access_token'][:50]}...")

    return tokens


# Example 4: Multi-Tenant Azure AD
async def example_azure_ad_multi_tenant():
    """Example: Multi-tenant Azure AD for SaaS applications."""

    # Configure multi-tenant Azure AD
    config = AzureADConfig(
        tenant_id="common",  # Multi-tenant
        client_id="[AZURE_CLIENT_ID]",
        client_secret="[AZURE_CLIENT_SECRET]",
        redirect_uri="http://localhost:8000/auth/azure/callback"
    )

    # Create multi-tenant client
    azure_client = AzureADMultiTenantClient(config)

    # Generate authorization URL (works for any tenant)
    auth_url, state = azure_client.get_authorization_url()

    print(f"Multi-tenant auth URL: {auth_url}")

    # Validate token from any tenant
    token = "[AZURE_ACCESS_TOKEN]"  # Replace with actual token

    # Validate with tenant allowlist
    allowed_tenants = ["tenant-1-id", "tenant-2-id"]

    try:
        claims = await azure_client.validate_azure_token(
            token,
            allowed_tenants=allowed_tenants
        )
        print(f"Token valid for tenant: {claims['tid']}")
    except Exception as e:
        print(f"Token validation failed: {e}")


# Example 5: Google OAuth
def example_google_oauth():
    """Example: Google OAuth authentication."""

    # Create OAuth manager
    oauth_manager = OAuthManager()

    # Register Google provider
    google_config = OAuthConfig.google(
        client_id="[GOOGLE_CLIENT_ID]",
        client_secret="[GOOGLE_CLIENT_SECRET]",
        redirect_uri="http://localhost:8000/auth/google/callback"
    )

    oauth_manager.register_provider(google_config)

    # Get Google client
    google_client = oauth_manager.get_client(OAuthProvider.GOOGLE)

    # Generate authorization URL
    auth_url, state = google_client.get_authorization_url()

    print(f"Google auth URL: {auth_url}")
    print(f"State: {state}")

    return oauth_manager, google_client, state


# Example 6: GitHub OAuth
async def example_github_oauth_callback(github_client, code: str, state: str):
    """Example: Handle GitHub OAuth callback."""

    # Exchange code for tokens
    tokens = await github_client.exchange_code_for_tokens(code, state)

    print(f"GitHub access token: {tokens['access_token'][:50]}...")

    # Get user info
    user_info = await github_client.get_user_info(tokens["access_token"])

    print(f"GitHub user: {user_info['login']}")
    print(f"Email: {user_info.get('email', 'N/A')}")

    # Map to local claims
    local_claims = github_client.map_provider_claims_to_local(user_info)

    print(f"Local claims: {local_claims}")

    return local_claims


# Example 7: Complete FastAPI Application
def create_fastapi_app():
    """Example: Complete FastAPI app with Azure AD and OAuth."""

    app = FastAPI(title="Netrun Auth Integration Example")

    # Initialize Azure AD
    azure_config = AzureADConfig(
        tenant_id="[AZURE_TENANT_ID]",
        client_id="[AZURE_CLIENT_ID]",
        client_secret="[AZURE_CLIENT_SECRET]",
        redirect_uri="http://localhost:8000/auth/azure/callback"
    )
    initialize_azure_ad(azure_config)

    # Initialize OAuth manager
    oauth_manager = OAuthManager()

    # Register Google
    google_config = OAuthConfig.google(
        client_id="[GOOGLE_CLIENT_ID]",
        client_secret="[GOOGLE_CLIENT_SECRET]",
        redirect_uri="http://localhost:8000/auth/google/callback"
    )
    oauth_manager.register_provider(google_config)

    # Register GitHub
    github_config = OAuthConfig.github(
        client_id="[GITHUB_CLIENT_ID]",
        client_secret="[GITHUB_CLIENT_SECRET]",
        redirect_uri="http://localhost:8000/auth/github/callback"
    )
    oauth_manager.register_provider(github_config)

    # Create OAuth router
    oauth_router = create_oauth_router(oauth_manager)
    app.include_router(oauth_router)

    # Azure AD routes
    @app.get("/auth/azure/login")
    async def azure_login(request: Request):
        """Start Azure AD login flow."""
        from netrun_auth.integrations import get_azure_ad_client

        azure_client = get_azure_ad_client()
        auth_url, state = azure_client.get_authorization_url()

        # Store state in session
        request.session["azure_state"] = state

        return RedirectResponse(url=auth_url)

    @app.get("/auth/azure/callback")
    async def azure_callback(code: str, state: str, request: Request):
        """Handle Azure AD callback."""
        from netrun_auth.integrations import get_azure_ad_client

        # Validate state
        stored_state = request.session.get("azure_state")
        if stored_state != state:
            raise HTTPException(status_code=400, detail="Invalid state")

        azure_client = get_azure_ad_client()

        # Exchange code for tokens
        tokens = await azure_client.exchange_code_for_tokens(code, state)

        # Validate token and get claims
        local_claims = await get_current_user_azure(tokens["access_token"])

        return {
            "message": "Login successful",
            "user": local_claims,
            "tokens": tokens
        }

    # Protected route example (commented out - requires proper dependency setup)
    # @app.get("/api/profile")
    # async def get_profile(user: dict = Depends(get_current_user_azure)):
    #     """Protected route requiring Azure AD authentication."""
    #     return {
    #         "user_id": user["user_id"],
    #         "email": user["email"],
    #         "organization_id": user["organization_id"]
    #     }

    return app


# Example 8: Token Refresh
async def example_token_refresh(oauth_client, refresh_token: str):
    """Example: Refresh OAuth access token."""

    # Refresh token
    new_tokens = await oauth_client.refresh_access_token(refresh_token)

    print(f"New access token: {new_tokens['access_token'][:50]}...")
    print(f"Expires in: {new_tokens['expires_in']}s")

    return new_tokens


# Main demonstration
async def main():
    """Run all examples (with placeholder credentials)."""

    print("=" * 60)
    print("Netrun Auth v1.0.0 - Azure AD & OAuth Integration Examples")
    print("=" * 60)

    print("\n--- Example 1: Azure AD Web App ---")
    # azure_client, state = example_azure_ad_web_app()

    print("\n--- Example 2: Azure AD Callback ---")
    # tokens, claims = await example_azure_ad_callback(azure_client, "CODE", state)

    print("\n--- Example 3: Azure AD Service Auth ---")
    # service_tokens = await example_azure_ad_service_auth()

    print("\n--- Example 4: Multi-Tenant Azure AD ---")
    # await example_azure_ad_multi_tenant()

    print("\n--- Example 5: Google OAuth ---")
    oauth_manager, google_client, state = example_google_oauth()

    print("\n--- Example 6: GitHub OAuth Callback ---")
    # claims = await example_github_oauth_callback(github_client, "CODE", state)

    print("\n--- Example 7: FastAPI App ---")
    app = create_fastapi_app()
    print(f"FastAPI app created with {len(app.routes)} routes")

    print("\n--- Example 8: Token Refresh ---")
    # new_tokens = await example_token_refresh(google_client, "REFRESH_TOKEN")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("Replace placeholder credentials with actual values to test.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
