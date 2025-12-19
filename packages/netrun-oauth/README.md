# netrun-oauth

Reusable OAuth 2.0 adapters for multi-tenant SaaS applications. Extracted from Intirkast's production OAuth integration layer.

## Features

- **Platform-Agnostic OAuth Adapters**: Unified interface for 12+ OAuth platforms
- **Token Encryption**: AES-256-GCM encryption via Fernet for secure token storage
- **Azure Integration**: Native Azure Key Vault support for production deployments
- **Adapter Factory**: Dynamic adapter creation with automatic credential injection
- **Multi-Tenant Ready**: Designed for SaaS applications with tenant isolation
- **SDLC v2.2 Compliant**: Security placeholders, comprehensive error handling, type hints

## Supported Platforms

- Microsoft (Azure AD, Office 365, Microsoft Graph)
- Google (Workspace, Gmail, Calendar, Drive)
- Salesforce
- HubSpot
- QuickBooks
- Xero
- Meta (Facebook, Instagram)
- Mailchimp
- Slack
- Zoom
- DocuSign
- Dropbox

## Installation

```bash
# Basic installation
pip install netrun-oauth

# With Azure Key Vault support
pip install netrun-oauth[azure]

# With development tools
pip install netrun-oauth[dev]

# Everything
pip install netrun-oauth[all]
```

## Quick Start

### Basic OAuth Flow

```python
from netrun_oauth import OAuthAdapterFactory

# Create adapter (auto-resolves credentials from environment)
adapter = OAuthAdapterFactory.create("microsoft")

# Generate authorization URL
auth_url = await adapter.get_authorization_url(
    state="random_state_token",
    redirect_uri="https://app.example.com/oauth/callback"
)

# Exchange authorization code for token
token_data = await adapter.exchange_code_for_token(
    code="authorization_code_from_callback",
    redirect_uri="https://app.example.com/oauth/callback"
)

print(token_data.access_token)  # Access token
print(token_data.refresh_token)  # Refresh token
print(token_data.expires_at)  # Expiration datetime
```

### Token Encryption

```python
from netrun_oauth import TokenEncryptionService

# Initialize encryption service (auto-resolves key from environment/Azure Key Vault)
encryption = TokenEncryptionService()

# Encrypt token before storing in database
encrypted_token = encryption.encrypt_token(token_data.access_token)

# Decrypt token when needed
decrypted_token = encryption.decrypt_token(encrypted_token)
```

### Explicit Credentials

```python
# Provide credentials explicitly (bypasses auto-resolution)
adapter = OAuthAdapterFactory.create(
    "google",
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)
```

## Configuration

### Environment Variables

Set platform-specific credentials:

```bash
# Microsoft
export MICROSOFT_CLIENT_ID="your_microsoft_client_id"
export MICROSOFT_CLIENT_SECRET="your_microsoft_client_secret"

# Google
export GOOGLE_CLIENT_ID="your_google_client_id"
export GOOGLE_CLIENT_SECRET="your_google_client_secret"

# Token encryption key (32-byte base64-encoded Fernet key)
export OAUTH_TOKEN_ENCRYPTION_KEY="your_fernet_key"
```

Generate encryption key:

```python
from netrun_oauth import TokenEncryptionService

key = TokenEncryptionService.generate_key()
print(f"OAUTH_TOKEN_ENCRYPTION_KEY={key}")
```

### Azure Key Vault (Production)

For production deployments, store credentials in Azure Key Vault:

```bash
# Set Key Vault URL
export AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"

# Store secrets in Key Vault (use Azure CLI or Portal)
az keyvault secret set --vault-name your-vault --name microsoft-client-id --value "..."
az keyvault secret set --vault-name your-vault --name microsoft-client-secret --value "..."
az keyvault secret set --vault-name your-vault --name oauth-token-encryption-key --value "..."
```

The adapter factory will automatically fetch credentials from Key Vault using `DefaultAzureCredential`.

## Advanced Usage

### Refresh Tokens

```python
# Refresh expired access token
new_token_data = await adapter.refresh_token(refresh_token)
```

### Revoke Tokens

```python
# Revoke access token (disconnect account)
success = await adapter.revoke_token(access_token)
```

### User Profile

```python
# Fetch user profile information
profile = await adapter.get_user_profile(access_token)
print(profile["display_name"])
print(profile["email"])
```

### Custom Adapters

```python
from netrun_oauth import BaseOAuthAdapter, OAuthAdapterFactory

class CustomAdapter(BaseOAuthAdapter):
    async def get_authorization_url(self, state, redirect_uri, scopes=None):
        # Implementation
        pass

    # ... implement other abstract methods

# Register custom adapter
OAuthAdapterFactory.register_adapter("custom_platform", CustomAdapter)

# Use custom adapter
adapter = OAuthAdapterFactory.create("custom_platform")
```

## Security Best Practices

### Production Deployment

1. **Use Azure Key Vault**: Store all credentials in Azure Key Vault, never in environment variables or code
2. **Enable Managed Identity**: Use Azure Managed Identity for Key Vault access (no credentials needed)
3. **Rotate Keys**: Implement key rotation for token encryption using `rotate_encryption()`
4. **Audit Logging**: Log all OAuth operations for compliance and security monitoring
5. **HTTPS Only**: Always use HTTPS for redirect URIs and API calls

### Placeholder Format

For development/testing, use placeholder format:

```python
client_id = "{{MICROSOFT_CLIENT_ID}}"
client_secret = "{{MICROSOFT_CLIENT_SECRET}}"
```

This prevents accidental credential leakage in version control.

## Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=netrun_oauth --cov-report=html

# Run specific test
pytest tests/test_factory.py::test_factory_create_microsoft
```

## Architecture

### Adapter Pattern

Each platform adapter inherits from `BaseOAuthAdapter` and implements:

- `get_authorization_url()` - Generate OAuth authorization URL
- `exchange_code_for_token()` - Exchange authorization code for access token
- `refresh_token()` - Refresh expired access token
- `revoke_token()` - Revoke access token
- `post_text()`, `post_image()`, `post_video()` - Platform-specific posting (optional)
- `get_user_profile()` - Fetch user profile (optional)

### Factory Pattern

`OAuthAdapterFactory` provides:

- Dynamic adapter creation by platform name
- Automatic credential injection (Key Vault → Environment → Placeholders)
- Custom adapter registration
- Platform enumeration

### Token Encryption

`TokenEncryptionService` uses:

- **Fernet**: Symmetric encryption with AES-256-GCM
- **Timestamps**: Built-in expiration for key rotation
- **Authentication**: HMAC prevents tampering
- **Key Resolution**: Auto-loads from Key Vault or environment

## API Reference

### OAuthAdapterFactory

```python
OAuthAdapterFactory.create(platform: str, client_id: str = None, client_secret: str = None, **kwargs) -> BaseOAuthAdapter
OAuthAdapterFactory.list_platforms() -> List[str]
OAuthAdapterFactory.register_adapter(platform: str, adapter_class: type) -> None
```

### BaseOAuthAdapter

```python
async get_authorization_url(state: str, redirect_uri: str, scopes: list = None) -> str
async exchange_code_for_token(code: str, redirect_uri: str, code_verifier: str = None, state: str = None) -> TokenData
async refresh_token(refresh_token: str) -> TokenData
async revoke_token(access_token: str) -> bool
async post_text(access_token: str, content: str, **kwargs) -> PostResult
async post_image(access_token: str, content: str, image_url: str, **kwargs) -> PostResult
async post_video(access_token: str, content: str, video_url: str, **kwargs) -> PostResult
async get_user_profile(access_token: str) -> Dict[str, Any]
```

### TokenEncryptionService

```python
__init__(encryption_key: str = None)
encrypt_token(token: str) -> str
decrypt_token(encrypted_token: str) -> str
rotate_encryption(old_encrypted_token: str, new_key: str) -> str
is_initialized() -> bool
@staticmethod generate_key() -> str
```

### Data Classes

```python
@dataclass
class TokenData:
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None

@dataclass
class PostResult:
    success: bool
    platform: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_after_seconds: Optional[int] = None
```

## Contributing

Contributions welcome! Please follow:

1. Fork repository
2. Create feature branch (`git checkout -b feature/new-adapter`)
3. Implement adapter following `BaseOAuthAdapter` interface
4. Add comprehensive tests (target 80%+ coverage)
5. Update README with new platform
6. Submit pull request

## License

MIT License - see LICENSE file for details

## Credits

Extracted from [Intirkast](https://github.com/netrunsystems/intirkast) production OAuth integration layer.

Developed by [Netrun Systems](https://netrunsystems.com) - Cloud Infrastructure & Multi-Tenant SaaS Solutions.

## Support

- Documentation: https://github.com/netrunsystems/netrun-service-library
- Issues: https://github.com/netrunsystems/netrun-service-library/issues
- Email: support@netrunsystems.com
