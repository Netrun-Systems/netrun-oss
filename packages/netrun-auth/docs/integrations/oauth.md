# OAuth 2.0 Integration Guide

Complete integration guide for OAuth 2.0 providers.

## Supported Providers

netrun-auth provides pre-configured OAuth clients for:

- **Google**: Identity and access for Google accounts
- **GitHub**: Developer authentication and organization access
- **Okta**: Enterprise identity management
- **Auth0**: Identity platform
- Custom OAuth 2.0 providers

## Configuration

### Google OAuth

#### Setup in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project
3. Go to **APIs & Services** > **OAuth consent screen**
4. Configure consent screen (required)
5. Go to **Credentials** > **Create Credential** > **OAuth 2.0 Client ID**
6. Select **Web application**
7. Add authorized redirect URIs:
   - `http://localhost:8000/auth/google/callback`
   - `https://your-domain.com/auth/google/callback`
8. Copy **Client ID** and **Client Secret**

#### Environment Variables

```env
NETRUN_AUTH_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
NETRUN_AUTH_GOOGLE_CLIENT_SECRET=your-secret
NETRUN_AUTH_GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
NETRUN_AUTH_GOOGLE_SCOPES=openid,profile,email
```

### GitHub OAuth

#### Setup in GitHub Settings

1. Go to **GitHub Settings** > **Developer settings** > **OAuth Apps**
2. Click **New OAuth App**
3. Fill in application details:
   - **Application name**: netrun-auth-app
   - **Homepage URL**: https://your-domain.com
   - **Authorization callback URL**: http://localhost:8000/auth/github/callback
4. Copy **Client ID** and generate **Client Secret**

#### Environment Variables

```env
NETRUN_AUTH_GITHUB_CLIENT_ID=your-client-id
NETRUN_AUTH_GITHUB_CLIENT_SECRET=your-secret
NETRUN_AUTH_GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback
NETRUN_AUTH_GITHUB_SCOPES=read:user,user:email
```

### Okta OAuth

#### Setup in Okta Admin Console

1. Go to [Okta Admin Console](https://developer.okta.com/)
2. Go to **Applications** > **Create App Integration**
3. Select **OAuth 2.0**
4. Select **Web** application
5. Configure:
   - **App name**: netrun-auth-app
   - **Base URIs**: https://your-domain.com
   - **Redirect URIs**: http://localhost:8000/auth/okta/callback
6. Copy **Client ID** and **Client Secret**

#### Environment Variables

```env
NETRUN_AUTH_OKTA_DOMAIN=your-domain.okta.com
NETRUN_AUTH_OKTA_CLIENT_ID=your-client-id
NETRUN_AUTH_OKTA_CLIENT_SECRET=your-secret
NETRUN_AUTH_OKTA_REDIRECT_URI=http://localhost:8000/auth/okta/callback
```

### Auth0 OAuth

#### Setup in Auth0 Dashboard

1. Go to [Auth0 Dashboard](https://manage.auth0.com/)
2. Go to **Applications** > **Create Application**
3. Select **Regular Web Applications**
4. Configure:
   - **Name**: netrun-auth-app
   - **Application type**: Regular Web Application
5. Go to **Settings** tab
6. Set **Allowed Callback URLs**: http://localhost:8000/auth/auth0/callback
7. Copy **Client ID** and **Client Secret**

#### Environment Variables

```env
NETRUN_AUTH_AUTH0_DOMAIN=your-domain.auth0.com
NETRUN_AUTH_AUTH0_CLIENT_ID=your-client-id
NETRUN_AUTH_AUTH0_CLIENT_SECRET=your-secret
NETRUN_AUTH_AUTH0_REDIRECT_URI=http://localhost:8000/auth/auth0/callback
```

## Authorization Code Flow

Standard OAuth 2.0 flow for web applications.

### Implementation

```python
from fastapi import FastAPI
from netrun_auth.integrations.oauth import OAuth2Config, OAuth2Client

app = FastAPI()

# Initialize Google OAuth
google_config = OAuth2Config(
    client_id="your-client-id",
    client_secret="your-secret",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    user_info_url="https://openidconnect.googleapis.com/v1/userinfo",
    scopes=["openid", "profile", "email"]
)

google_client = OAuth2Client(google_config)

# Step 1: Generate authorization URL
@app.get("/auth/google")
async def google_login():
    """Redirect to Google login."""
    auth_url, state = google_client.get_authorization_url()

    # Store state in session for verification
    # response.set_cookie("oauth_state", state)

    return {"redirect_url": auth_url}

# Step 2: Handle OAuth callback
@app.get("/auth/google/callback")
async def google_callback(code: str, state: str):
    """Handle Google OAuth callback."""

    # Verify state
    # stored_state = request.cookies.get("oauth_state")
    # if state != stored_state:
    #     raise HTTPException(status_code=400, detail="Invalid state")

    # Exchange code for token
    token = await google_client.get_token(code)

    # Get user info
    user_info = await google_client.get_user_info(token["access_token"])

    # Generate netrun-auth tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=user_info["sub"],
        email=user_info.get("email"),
        display_name=user_info.get("name")
    )

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": "Bearer"
    }
```

## Multi-Provider Setup

Handle multiple OAuth providers.

### Provider Manager

```python
from netrun_auth.integrations.oauth import OAuthManager

oauth_manager = OAuthManager()

# Add Google
oauth_manager.add_provider(
    "google",
    OAuth2Config(
        client_id="google-client-id",
        client_secret="google-secret",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        user_info_url="https://openidconnect.googleapis.com/v1/userinfo"
    )
)

# Add GitHub
oauth_manager.add_provider(
    "github",
    OAuth2Config(
        client_id="github-client-id",
        client_secret="github-secret",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        user_info_url="https://api.github.com/user"
    )
)

# Get provider
google = oauth_manager.get_provider("google")
github = oauth_manager.get_provider("github")
```

### Multi-Provider Routes

```python
@app.get("/auth/{provider}")
async def oauth_login(provider: str):
    """Login with specified OAuth provider."""
    oauth_client = oauth_manager.get_provider(provider)

    if not oauth_client:
        raise HTTPException(status_code=404, detail="Provider not found")

    auth_url, state = oauth_client.get_authorization_url()
    return {"redirect_url": auth_url}

@app.get("/auth/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str):
    """Handle OAuth callback for any provider."""
    oauth_client = oauth_manager.get_provider(provider)

    if not oauth_client:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Exchange code for token
    token = await oauth_client.get_token(code)

    # Get user info
    user_info = await oauth_client.get_user_info(token["access_token"])

    # Map provider user info to netrun-auth format
    mapped_user = map_oauth_user(provider, user_info)

    # Generate tokens
    token_pair = await jwt_manager.generate_token_pair(**mapped_user)

    return token_pair.model_dump()

def map_oauth_user(provider: str, user_info: dict) -> dict:
    """Map OAuth user info to netrun-auth format."""
    if provider == "google":
        return {
            "user_id": user_info["sub"],
            "email": user_info.get("email"),
            "display_name": user_info.get("name")
        }
    elif provider == "github":
        return {
            "user_id": str(user_info["id"]),
            "email": user_info.get("email"),
            "display_name": user_info.get("name")
        }
    # ... other providers
```

## PKCE for Public Clients

Use PKCE (Proof Key for Code Exchange) for enhanced security.

```python
class OAuthClientPKCE(OAuth2Client):
    """OAuth2 client with PKCE support."""

    async def get_authorization_url_with_pkce(self):
        """Generate authorization URL with PKCE."""
        code_verifier = self.generate_code_verifier()
        code_challenge = self.generate_code_challenge(code_verifier)

        # Store for callback verification
        state = self.generate_state()

        auth_url = self.config.authorize_url + "?" + urlencode({
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"  # SHA256
        })

        return auth_url, state, code_verifier

    async def get_token_with_pkce(self, code: str, code_verifier: str):
        """Exchange code for token using PKCE."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "code_verifier": code_verifier
        }

        # For public clients, don't include client_secret
        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret

        return await self.post_token(data)
```

## OpenID Connect

OIDC extends OAuth 2.0 for authentication.

```python
class OIDCClient(OAuth2Client):
    """OpenID Connect client."""

    async def get_user_claims(self, id_token: str) -> dict:
        """Decode and validate ID token claims."""
        claims = jwt.decode(
            id_token,
            options={"verify_signature": False}  # Validate separately
        )

        # Validate claims
        if claims.get("aud") != self.config.client_id:
            raise ValueError("Invalid audience")

        if claims.get("iss") != self.config.issuer:
            raise ValueError("Invalid issuer")

        # Check expiration
        from datetime import datetime, timezone
        if claims.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            raise ValueError("Token expired")

        return claims

@app.get("/auth/oidc/callback")
async def oidc_callback(code: str, id_token: str):
    """Handle OIDC callback."""
    oidc_client = OIDCClient(config)

    # Get claims from ID token
    claims = await oidc_client.get_user_claims(id_token)

    # Generate netrun-auth tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=claims["sub"],
        email=claims.get("email"),
        display_name=claims.get("name")
    )

    return token_pair.model_dump()
```

## Refresh Token Handling

Refresh OAuth tokens when expired.

```python
class OAuthTokenManager:
    """Manage OAuth token refresh and storage."""

    async def refresh_token(self, refresh_token: str, provider: str):
        """Refresh OAuth token."""
        client = self.oauth_manager.get_provider(provider)

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client.config.client_id,
            "client_secret": client.config.client_secret
        }

        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                client.config.token_url,
                data=data
            )

        return response.json()

    async def is_token_expired(self, token: dict) -> bool:
        """Check if token is expired."""
        from datetime import datetime, timezone

        expires_at = token.get("expires_at")
        if not expires_at:
            return False

        return expires_at < datetime.now(timezone.utc).timestamp()

    async def maybe_refresh_token(self, oauth_token: dict, provider: str):
        """Refresh token if expired."""
        if await self.is_token_expired(oauth_token):
            return await self.refresh_token(oauth_token["refresh_token"], provider)

        return oauth_token
```

## Custom OAuth Provider

Add custom OAuth 2.0 provider not in presets.

```python
custom_config = OAuth2Config(
    client_id="your-client-id",
    client_secret="your-secret",
    authorize_url="https://your-oauth-provider.com/oauth/authorize",
    token_url="https://your-oauth-provider.com/oauth/token",
    user_info_url="https://your-oauth-provider.com/api/user",
    scopes=["openid", "profile", "email"],
    name="Custom Provider"
)

client = OAuth2Client(custom_config)

# Use like any other provider
auth_url, state = client.get_authorization_url()
token = await client.get_token(code)
user_info = await client.get_user_info(token["access_token"])
```

## Security Best Practices

1. **Validate State Parameter**: Prevent CSRF attacks
   ```python
   stored_state = session.get("oauth_state")
   if state != stored_state:
       raise HTTPException(status_code=400, detail="Invalid state")
   ```

2. **Use PKCE**: For public clients
   ```python
   auth_url, state, pkce = client.get_authorization_url_with_pkce()
   ```

3. **Validate Token Signature**: Ensure token integrity
   ```python
   claims = jwt.decode(id_token, public_key, algorithms=["RS256"])
   ```

4. **Check Token Expiry**: Prevent using expired tokens
   ```python
   if claims["exp"] < time.time():
       raise ValueError("Token expired")
   ```

5. **Secure Token Storage**: Never expose tokens
   ```python
   # Store in httponly cookie
   response.set_cookie("oauth_token", token, httponly=True)

   # Not in localStorage (vulnerable to XSS)
   ```

6. **Use HTTPS**: Always use HTTPS in production
   ```
   Redirect URIs: https://your-domain.com/auth/callback
   Not: http://your-domain.com/auth/callback
   ```

## Complete Multi-Provider Example

```python
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from netrun_auth import JWTManager, AuthConfig
from netrun_auth.integrations.oauth import OAuthManager, OAuth2Config

app = FastAPI()

# Initialize managers
auth_config = AuthConfig()
jwt_manager = JWTManager(auth_config)
oauth_manager = OAuthManager()

# Configure providers
providers = {
    "google": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://openidconnect.googleapis.com/v1/userinfo"
    },
    "github": {
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user"
    }
}

for provider_name, config in providers.items():
    oauth_manager.add_provider(
        provider_name,
        OAuth2Config(**config)
    )

# OAuth routes
@app.get("/auth/{provider}")
async def oauth_login(provider: str):
    client = oauth_manager.get_provider(provider)
    if not client:
        raise HTTPException(status_code=404, detail="Provider not found")

    auth_url, state = client.get_authorization_url()
    # Store state in session
    return RedirectResponse(url=auth_url)

@app.get("/auth/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str):
    client = oauth_manager.get_provider(provider)

    # Verify state
    # ...

    # Get token
    token = await client.get_token(code)

    # Get user info
    user_info = await client.get_user_info(token["access_token"])

    # Map user info
    if provider == "google":
        user_id = user_info["sub"]
    elif provider == "github":
        user_id = str(user_info["id"])
    else:
        user_id = user_info.get("id")

    # Generate netrun-auth tokens
    token_pair = await jwt_manager.generate_token_pair(
        user_id=user_id,
        roles=["user"]
    )

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": "Bearer"
    }
```

## Troubleshooting

### Invalid Redirect URI

```
Error: redirect_uri_mismatch
```

**Solution**: Ensure redirect URI matches exactly

### Invalid State Token

```
Error: Invalid state parameter
```

**Solution**: Verify state in session before exchanging code

### Token Invalid/Expired

```
Error: invalid_grant
```

**Solution**: Code is single-use and expires in ~10 minutes

---

**Last Updated**: November 25, 2025
**Version**: 1.0.0
