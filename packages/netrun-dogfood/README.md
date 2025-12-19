# Netrun Dogfood MCP Server

MCP (Model Context Protocol) server providing unified API access to all Netrun Systems products deployed in Azure. Enables Claude Code agents to leverage our own production services.

## Overview

The Netrun Dogfood server exposes **53 MCP tools** with full CRUD operations across 5 Netrun Systems products:

| Product | Tools | Description |
|---------|-------|-------------|
| **Intirkon** | 13 | Azure multi-tenant management platform |
| **Charlotte** | 12 | AI orchestration and LLM mesh network |
| **Meridian** | 10 | Document publishing and flipbook generation |
| **NetrunSite** | 8 | Company website and blog API |
| **SecureVault** | 10 | Password and credential management |

## Installation

```bash
# Install from local packages
pip install -e packages/netrun-dogfood

# Or with all dependencies
pip install -e "packages/netrun-dogfood[dev]"
```

## Configuration

### Option 1: Azure Key Vault (Recommended)

Use Azure Key Vault for centralized credential management. This is the recommended approach for production.

**Prerequisites:**
1. Azure Key Vault with these secrets:
   - `AZURE-AD-TENANT-ID` - Netrun Systems Azure AD tenant
   - `AZURE-AD-CLIENT-ID` - Service principal client ID
   - `AZURE-AD-CLIENT-SECRET` - Service principal client secret

2. Azure CLI authenticated (`az login`) or Managed Identity configured

**Claude Code Integration** (`.mcp.json`):

```json
{
  "mcpServers": {
    "netrun-dogfood": {
      "command": "python",
      "args": ["run_mcp.py"],
      "env": {
        "AZURE_KEYVAULT_URL": "https://netrun-keyvault.vault.azure.net",
        "USE_KEYVAULT_AUTH": "true",
        "PROJECT_DIR": "/path/to/your/project"
      },
      "cwd": "/path/to/netrun-dogfood"
    }
  }
}
```

The `run_mcp.py` wrapper automatically loads environment variables from:
1. `$PROJECT_DIR/.env.mcp` (project-specific secrets)
2. `$PROJECT_DIR/.env` (fallback)
3. `~/.meridian.env` (user-level config)

This allows secure storage of API keys without committing them to git.

**Example `.env.mcp`**:
```bash
# Meridian API key for M2M authentication
MERIDIAN_API_KEY=mk_your_api_key_here
```

### Option 2: Environment Variables

For local development without Key Vault access:

```bash
# Azure AD / MSAL (Required)
AZURE_TENANT_ID=<netrun-systems-tenant>
AZURE_CLIENT_ID=<dogfood-service-principal>
AZURE_CLIENT_SECRET=<client-secret>

# Product API URLs (Optional - defaults shown)
INTIRKON_API_URL=https://intirkon-api.azurewebsites.net/api/v2
CHARLOTTE_API_URL=https://charlotte.netrunsystems.com/api/v1
MERIDIAN_API_URL=https://meridian-backend-prod.blackrock-7921664c.eastus2.azurecontainerapps.io/api
NETRUNSITE_API_URL=https://netrunsystems.com/api
SECUREVAULT_API_URL=http://127.0.0.1:8437/api/v1

# Meridian API Key (Recommended - bypasses Azure AD for M2M auth)
MERIDIAN_API_KEY=mk_your_api_key_here  # Get from /api/users/me/api-keys

# Feature Toggles (Optional)
INTIRKON_ENABLED=true
CHARLOTTE_ENABLED=true
MERIDIAN_ENABLED=true
NETRUNSITE_ENABLED=true
SECUREVAULT_ENABLED=true
```

**Claude Code Integration** (`.mcp.json`):

```json
{
  "mcpServers": {
    "netrun-dogfood": {
      "command": "python",
      "args": ["-m", "netrun_dogfood.server"],
      "env": {
        "AZURE_TENANT_ID": "your-tenant-id",
        "AZURE_CLIENT_ID": "your-client-id",
        "AZURE_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Creating the Service Principal

To create the dogfood service principal in Azure AD:

```bash
# Create service principal with required permissions
az ad sp create-for-rbac --name "netrun-dogfood-mcp" \
  --role Contributor \
  --scopes /subscriptions/<subscription-id>

# Update Key Vault secrets with the new credentials
az keyvault secret set --vault-name netrun-keyvault \
  --name AZURE-AD-CLIENT-ID --value "<new-client-id>"
az keyvault secret set --vault-name netrun-keyvault \
  --name AZURE-AD-CLIENT-SECRET --value "<new-client-secret>"
```

## Tool Reference

### Intirkon Tools (Cloud Management)

| Tool | Operation | Description |
|------|-----------|-------------|
| `intirkon_list_tenants` | READ | List managed Azure tenants |
| `intirkon_get_tenant` | READ | Get tenant details |
| `intirkon_get_costs` | READ | Query Azure cost data |
| `intirkon_get_resources` | READ | Inventory Azure resources |
| `intirkon_get_health` | READ | Check resource health status |
| `intirkon_get_alerts` | READ | Get cost/security alerts |
| `intirkon_create_alert` | CREATE | Create new alert rule |
| `intirkon_update_alert` | UPDATE | Modify alert threshold/config |
| `intirkon_delete_alert` | DELETE | Remove alert rule |
| `intirkon_get_advisor` | READ | Azure Advisor recommendations |
| `intirkon_get_compliance` | READ | Policy compliance status |
| `intirkon_run_action` | CREATE | Execute Azure action |
| `intirkon_health` | READ | API health check |

### Charlotte Tools (AI Orchestration)

| Tool | Operation | Description |
|------|-----------|-------------|
| `charlotte_chat` | CREATE | Send message to AI models |
| `charlotte_reason` | CREATE | Advanced reasoning request |
| `charlotte_list_models` | READ | Available LLM models |
| `charlotte_get_model` | READ | Model details and pricing |
| `charlotte_tts` | CREATE | Text-to-speech generation |
| `charlotte_stt` | CREATE | Speech-to-text transcription |
| `charlotte_list_conversations` | READ | List chat history |
| `charlotte_get_conversation` | READ | Get conversation details |
| `charlotte_delete_conversation` | DELETE | Remove conversation |
| `charlotte_mesh_status` | READ | Check mesh network health |
| `charlotte_list_nodes` | READ | List mesh nodes |
| `charlotte_health` | READ | API health check |

### Meridian Tools (Document Publishing)

| Tool | Operation | Description |
|------|-----------|-------------|
| `meridian_list_publications` | READ | List user publications |
| `meridian_get_publication` | READ | Get publication details |
| `meridian_upload_document` | CREATE | Upload PDF/document |
| `meridian_create_flipbook` | CREATE | Convert to flipbook |
| `meridian_update_publication` | UPDATE | Update metadata |
| `meridian_delete_publication` | DELETE | Remove publication |
| `meridian_get_analytics` | READ | View statistics |
| `meridian_list_templates` | READ | Available templates |
| `meridian_share_publication` | CREATE | Generate share link |
| `meridian_health` | READ | API health check |

### NetrunSite Tools (Website/Blog)

| Tool | Operation | Description |
|------|-----------|-------------|
| `netrunsite_list_posts` | READ | List blog posts |
| `netrunsite_get_post` | READ | Get post details |
| `netrunsite_create_post` | CREATE | Create blog post |
| `netrunsite_update_post` | UPDATE | Update blog post |
| `netrunsite_delete_post` | DELETE | Remove blog post |
| `netrunsite_submit_contact` | CREATE | Submit contact form |
| `netrunsite_get_analytics` | READ | Site analytics |
| `netrunsite_health` | READ | Health check |

### SecureVault Tools (Password Management)

| Tool | Operation | Description |
|------|-----------|-------------|
| `securevault_list_credentials` | READ | List stored credentials |
| `securevault_get_credential` | READ | Retrieve credential |
| `securevault_create_credential` | CREATE | Store new credential |
| `securevault_update_credential` | UPDATE | Modify credential |
| `securevault_delete_credential` | DELETE | Remove credential |
| `securevault_search` | READ | Search credentials |
| `securevault_list_folders` | READ | List folders |
| `securevault_create_folder` | CREATE | Create folder |
| `securevault_generate_password` | CREATE | Generate secure password |
| `securevault_health` | READ | Vault health check |

## Usage Examples

### Check System Health

```python
# Use dogfood_health to check all products
result = await dogfood_health()
```

### Query Azure Costs

```python
# Get costs for all tenants this month
result = await intirkon_get_costs(period="month", group_by="service")

# Get costs for specific tenant
result = await intirkon_get_costs(
    tenant_id="abc123",
    period="quarter",
    group_by="resource_group"
)
```

### Chat with AI Models

```python
# Simple chat
result = await charlotte_chat(
    message="Explain Azure cost optimization strategies",
    model="gpt-4"
)

# Advanced reasoning
result = await charlotte_reason(
    query="Analyze the security implications of multi-tenant Azure deployments",
    reasoning_type="analytical",
    depth="deep"
)
```

### Manage Credentials

```python
# Generate secure password
result = await securevault_generate_password(
    length=32,
    symbols=True,
    exclude_ambiguous=True
)

# Store credential
result = await securevault_create_credential(
    name="Production Database",
    username="admin",
    password=generated_password,
    url="https://db.example.com",
    folder="infrastructure"
)
```

## Authentication

The server supports two authentication methods:

### Method 1: Azure AD Client Credentials (Default)

Uses Azure AD Client Credentials flow for service-to-service authentication:

1. MCP server initializes with service principal credentials
2. Uses Client Credentials flow to get access tokens
3. Tokens are cached and auto-refreshed before expiry
4. Each product API validates token against shared Azure AD app

### Method 2: API Key Authentication (Meridian)

Meridian supports simpler API key authentication for M2M scenarios:

1. Create an API key via `POST /api/users/me/api-keys`
2. Set `MERIDIAN_API_KEY` environment variable
3. Server automatically uses API key instead of Azure AD for Meridian calls

**Advantages:**
- No Azure AD setup required for Meridian access
- Simpler configuration for single-product integrations
- Individual keys can be revoked without affecting other services

**Example Configuration:**
```json
{
  "mcpServers": {
    "netrun-dogfood": {
      "command": "python",
      "args": ["-m", "netrun_dogfood.server"],
      "env": {
        "MERIDIAN_API_KEY": "mk_your_api_key_here"
      }
    }
  }
}
```

### Security Notes

- Never commit credentials to version control
- Use environment variables or Azure Key Vault
- SecureVault runs as local daemon by default (localhost:8437)
- API keys start with `mk_` prefix (64 characters total)
- Revoke compromised keys via `DELETE /api/users/me/api-keys/{id}`

## Development

```bash
# Install dev dependencies
pip install -e "packages/netrun-dogfood[dev]"

# Run tests
pytest packages/netrun-dogfood/tests/

# Format code
black packages/netrun-dogfood/
ruff check packages/netrun-dogfood/
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Claude Code Agent                    │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │         netrun-dogfood MCP Server           │   │
│  │  ┌─────────────────────────────────────┐    │   │
│  │  │   AzureADClient (from netrun-auth)  │    │   │
│  │  │   - Client Credentials Flow         │    │   │
│  │  │   - Token caching                   │    │   │
│  │  │   - JWKS validation                 │    │   │
│  │  └─────────────────────────────────────┘    │   │
│  └──────────────────┬──────────────────────────┘   │
└─────────────────────┼───────────────────────────────┘
                      │ Bearer Token
                      ▼
    ┌─────────────────────────────────────────────────┐
    │              Azure AD / Entra ID                │
    │         (Netrun Systems Tenant)                 │
    └─────────────────────────────────────────────────┘
                      │
         ┌────────────┼────────────┬───────────┐
         ▼            ▼            ▼           ▼
    ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
    │Intirkon │ │Charlotte │ │Meridian │ │SecureVault│
    │   API   │ │   API    │ │   API   │ │   API    │
    └─────────┘ └──────────┘ └─────────┘ └──────────┘
```

## License

MIT License - Netrun Systems

## Testing & Verification

See [CHARLOTTE_MCP_VERIFICATION_REPORT.md](CHARLOTTE_MCP_VERIFICATION_REPORT.md) for Charlotte MCP tool testing results and deployment status.

**Current Status** (2025-12-01):
- ✅ Authentication: Fully functional with Azure Key Vault
- ✅ Tool Implementation: All 53 tools correctly implemented
- ✅ Meridian API: Production deployment with API key auth working
- ⚠️ Charlotte API: Backend deployment required (frontend only currently deployed)
- ⚠️ Other APIs: Pending end-to-end verification

## Version

1.0.1 (2025-12-01)
- Added Meridian API key authentication support
- Updated Meridian default URL to production

*Last tested: 2025-12-01*
