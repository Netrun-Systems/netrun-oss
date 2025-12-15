# Azure Key Vault Advanced Integration Patterns Research Report

**Version**: 1.0
**Date**: 2025-12-03
**Agent**: Technical Research Specialist
**Correlation ID**: research_keyvault_2025-12-03_001

---

## Executive Summary

This research report analyzes advanced Azure Key Vault integration patterns for Python configuration management, comparing netrun-config's current implementation against industry best practices and competing libraries. The findings identify 15+ non-trivial features that could differentiate netrun-config in the market.

**Current netrun-config Implementation Analysis**:
- Basic KeyVaultMixin with lazy initialization
- Instance-level secret caching (no TTL/expiration)
- DefaultAzureCredential/ManagedIdentityCredential support
- Environment variable fallback
- Single vault support only

**Key Gaps Identified**:
1. No secret rotation detection or auto-refresh
2. No TTL-based cache expiration
3. Single vault only (no multi-vault support)
4. No certificate or key management
5. No batch fetching optimization
6. No audit logging of secret access
7. No pydantic-settings integration (uses mixin pattern)

---

## 1. Azure Key Vault Current Best Practices

### 1.1 Authentication: azure-identity Credential Chains

**Source**: [Microsoft Learn - Azure Key Vault Python Quickstart](https://learn.microsoft.com/en-us/azure/key-vault/secrets/quick-create-python)

**Best Practice**: Use `DefaultAzureCredential` as primary credential chain.

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# DefaultAzureCredential chains through multiple auth methods:
# 1. EnvironmentCredential (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
# 2. WorkloadIdentityCredential (for AKS workload identity)
# 3. ManagedIdentityCredential (for Azure-hosted resources)
# 4. SharedTokenCacheCredential (for Azure CLI cached tokens)
# 5. VisualStudioCodeCredential
# 6. AzureCliCredential
# 7. AzurePowerShellCredential

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://my-vault.vault.azure.net/", credential=credential)
```

**netrun-config Gap**: Current implementation manually selects between `DefaultAzureCredential` and `ManagedIdentityCredential` based on environment. Should use `DefaultAzureCredential` exclusively and let Azure SDK handle the chain.

**Recommendation**:
```python
# IMPROVED: Let DefaultAzureCredential handle all scenarios
def _get_azure_credential(self):
    """Get Azure credential using DefaultAzureCredential chain."""
    # Optional: Exclude specific credential types for faster local dev
    return DefaultAzureCredential(
        exclude_shared_token_cache_credential=True,
        exclude_visual_studio_code_credential=True,
    )
```

### 1.2 Secret Caching Strategies

**Source**: [Azure Key Vault Best Practices](https://learn.microsoft.com/en-us/azure/key-vault/secrets/secrets-best-practices)

**Key Recommendations**:
- Cache secrets in memory for at least **8 hours** to reduce API calls
- Implement **exponential back-off retry** logic for transient failures
- Refresh cached values when secrets are rotated
- Use **Event Grid** notifications for rotation detection

**netrun-config Gap**: Current caching is indefinite (no TTL). No rotation detection mechanism.

**Recommended Implementation**:
```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

@dataclass
class CachedSecret:
    """Secret with TTL-based cache expiration."""
    value: str
    fetched_at: datetime
    ttl_seconds: int = 28800  # 8 hours default
    version: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.fetched_at + timedelta(seconds=self.ttl_seconds)
```

### 1.3 Secret Rotation Strategy

**Source**: [Azure Key Vault Rotation Tutorial](https://learn.microsoft.com/en-us/azure/key-vault/secrets/tutorial-rotation)

**Best Practice**: Rotate secrets at least every **60 days**.

**Dual-Credentials Pattern** (Zero-Downtime Rotation):
1. Use two sets of credentials (primary/secondary)
2. Rotate one while the other remains active
3. Switch primary/secondary designation
4. Rotate the now-secondary credential

**Event Grid Integration**:
- `SecretNearExpiry` event: 30 days before expiration
- `SecretNewVersionCreated` event: New version available

---

## 2. Competing Libraries Analysis

### 2.1 dynaconf

**Source**: [Dynaconf Secrets Documentation](https://www.dynaconf.com/secrets/)

| Feature | dynaconf | netrun-config |
|---------|----------|---------------|
| Azure Key Vault | Not native (custom loader) | Mixin pattern |
| HashiCorp Vault | Native support | Not supported |
| Redis secrets | Native support | Not supported |
| Environment layering | Yes (settings_envs) | Partial |
| Custom loaders | Yes (plugin system) | No |

**Key Insight**: dynaconf has a robust loader plugin system. Azure Key Vault support requires a custom loader but the architecture is extensible.

**GitHub Issue**: [#1192 - Loading secrets from Azure Key Vault](https://github.com/dynaconf/dynaconf/issues/1192) - Community request since October 2024.

**Opportunity**: netrun-config can be THE definitive Azure Key Vault configuration library for Python.

### 2.2 AWS Secrets Manager Caching Library

**Source**: [AWS Secrets Manager Python Caching](https://github.com/aws/aws-secretsmanager-caching-python)

**Excellent patterns to adopt**:

```python
# AWS SecretCacheConfig - Configuration options
cache_config = SecretCacheConfig(
    max_cache_size=1024,                   # Maximum cached secrets
    exception_retry_delay_base=1,          # Initial retry delay (seconds)
    exception_retry_growth_factor=2,       # Exponential backoff multiplier
    exception_retry_delay_max=3600,        # Maximum retry delay (seconds)
    default_version_stage='AWSCURRENT',    # Version stage to request
    secret_refresh_interval=3600.0,        # TTL in seconds (1 hour)
    secret_cache_hook=None,                # Custom hook implementation
)

# Usage
cache = SecretCache(config=cache_config, client=client)
secret_value = cache.get_secret_string("my-secret")
```

**Key Features to Adopt**:
1. **Configurable TTL**: `secret_refresh_interval` parameter
2. **Max cache size**: Prevent memory exhaustion
3. **Exponential backoff**: `exception_retry_delay_*` parameters
4. **Secret hooks**: Custom transformation pipeline
5. **Decorator-based injection**: `@InjectSecretString` pattern

### 2.3 HashiCorp Vault (hvac library)

**Source**: [hvac Python Client](https://python-hvac.org/)

**Notable Patterns**:

```python
import hvac

client = hvac.Client(
    url='https://vault.example.com',
    token=os.environ['VAULT_TOKEN'],
    namespace='admin',  # HCP Vault namespace requirement
    cert=(client_cert_path, client_key_path),
    verify=server_cert_path,
)

# KV v2 secret access
secret = client.secrets.kv.v2.read_secret_version(
    path='my-secret',
    mount_point='secret',
)
```

**Key Features**:
- Multiple auth methods (Token, AppRole, Kubernetes, JWT/OIDC)
- KV v1/v2 engine support
- Namespace support (for HCP Vault)
- TLS certificate configuration

### 2.4 pydantic-settings Native Azure Key Vault

**Source**: [pydantic-settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

**CRITICAL FINDING**: pydantic-settings 2.x has **BUILT-IN** `AzureKeyVaultSettingsSource`!

```python
from azure.identity import DefaultAzureCredential
from pydantic_settings import (
    AzureKeyVaultSettingsSource,
    BaseSettings,
    PydanticBaseSettingsSource,
)

class Settings(BaseSettings):
    my_secret: str  # Loaded from Key Vault automatically

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            AzureKeyVaultSettingsSource(
                settings_cls,
                os.environ['AZURE_KEY_VAULT_URL'],
                DefaultAzureCredential(),
                snake_case_conversion=True,  # my-secret -> my_secret
            ),
            file_secret_settings,
        )
```

**netrun-config Opportunity**: Wrap `AzureKeyVaultSettingsSource` with enhanced features:
- Multi-vault support
- TTL-based caching layer
- Rotation detection
- Audit logging

### 2.5 pydantic-settings-vault (HashiCorp)

**Source**: [pydantic-settings-vault on PyPI](https://pypi.org/project/pydantic-settings-vault/)

**Configuration Pattern**:
```python
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings_vault import VaultSettingsSource

class Settings(BaseSettings):
    my_secret: str = Field(
        json_schema_extra={
            'vault_secret_path': 'secret/data/my-app',
            'vault_secret_key': 'password',
        }
    )

    model_config = {
        'vault_url': 'https://vault.example.com',
        'vault_namespace': 'admin',
    }
```

**Notable Features**:
- Per-field vault path configuration
- Namespace support
- Multiple auth methods (AppRole, Kubernetes, Token, JWT)
- Logger for debugging (`"pydantic-vault"`)

---

## 3. Non-Trivial Features for netrun-config

### 3.1 Priority 1: Critical (High Value, Medium Effort)

#### Feature 1: TTL-Based Secret Caching

**Why**: Microsoft recommends 8-hour cache minimum. Current implementation has no TTL.

```python
class SecretCacheConfig:
    """Configuration for secret caching behavior."""
    default_ttl_seconds: int = 28800  # 8 hours
    max_cache_size: int = 500
    retry_delay_base: float = 1.0
    retry_delay_max: float = 300.0
    retry_growth_factor: float = 2.0
```

#### Feature 2: Secret Rotation Detection

**Why**: Zero-downtime rotation is enterprise-critical.

**Implementation Options**:
1. **Poll-based**: Check version on each access if past soft-TTL
2. **Event-driven**: Azure Event Grid webhook for `SecretNewVersionCreated`

```python
class KeyVaultClient:
    async def get_secret_with_rotation_check(
        self,
        secret_name: str,
        force_refresh: bool = False,
    ) -> CachedSecret:
        cached = self._cache.get(secret_name)

        if cached and not force_refresh:
            # Soft TTL check - async version refresh
            if cached.is_soft_expired:
                asyncio.create_task(self._refresh_if_new_version(secret_name))
            if not cached.is_hard_expired:
                return cached

        return await self._fetch_and_cache(secret_name)
```

#### Feature 3: Multi-Vault Support

**Why**: Different environments (dev/staging/prod) often use different vaults.

```python
class MultiVaultConfig:
    """Support for multiple Key Vaults."""
    vaults: dict[str, VaultConfig] = {
        'default': VaultConfig(url='https://prod.vault.azure.net/'),
        'dev': VaultConfig(url='https://dev.vault.azure.net/'),
        'certificates': VaultConfig(url='https://certs.vault.azure.net/'),
    }

# Usage
secret = config.get_secret('api-key', vault='dev')
cert = config.get_certificate('ssl-cert', vault='certificates')
```

#### Feature 4: Pydantic Settings Source Integration

**Why**: Replace mixin pattern with proper `settings_customise_sources()` integration.

```python
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

class NetrunKeyVaultSettingsSource(PydanticBaseSettingsSource):
    """Enhanced Azure Key Vault settings source with caching and rotation."""

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        vault_url: str,
        credential: TokenCredential,
        *,
        cache_ttl_seconds: int = 28800,
        snake_case_conversion: bool = True,
        fallback_to_env: bool = True,
    ):
        super().__init__(settings_cls)
        self._vault_url = vault_url
        self._credential = credential
        self._cache_ttl = cache_ttl_seconds
        self._snake_case = snake_case_conversion
        self._fallback = fallback_to_env
```

### 3.2 Priority 2: Important (Medium Value, Medium Effort)

#### Feature 5: Batch Secret Fetching

**Why**: Reduce API calls during application startup.

```python
async def prefetch_secrets(
    self,
    secret_names: list[str],
    concurrency: int = 10,
) -> dict[str, str]:
    """Batch fetch secrets with controlled concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(name: str) -> tuple[str, str]:
        async with semaphore:
            secret = await self._fetch_secret(name)
            return (name, secret)

    results = await asyncio.gather(
        *[fetch_one(name) for name in secret_names]
    )
    return dict(results)
```

#### Feature 6: Lazy Loading with Descriptors

**Why**: Only fetch secrets when actually accessed.

```python
class LazySecret:
    """Descriptor for lazy-loaded Key Vault secrets."""

    def __init__(self, secret_name: str, vault: str = 'default'):
        self.secret_name = secret_name
        self.vault = vault

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        cache_key = f"{self.vault}:{self.secret_name}"
        if cache_key not in obj._secret_cache:
            obj._secret_cache[cache_key] = obj._kv_client.get_secret(
                self.secret_name
            ).value
        return obj._secret_cache[cache_key]

# Usage
class MySettings(BaseConfig):
    database_password = LazySecret('database-password')
    api_key = LazySecret('api-key', vault='external')
```

#### Feature 7: Secret Versioning and Rollback

**Why**: Ability to access previous secret versions for debugging/recovery.

```python
async def get_secret_version(
    self,
    secret_name: str,
    version: Optional[str] = None,
) -> SecretVersion:
    """Get specific version of a secret."""
    secret = await self._client.get_secret(secret_name, version=version)
    return SecretVersion(
        value=secret.value,
        version=secret.properties.version,
        created_on=secret.properties.created_on,
        enabled=secret.properties.enabled,
    )

async def list_secret_versions(
    self,
    secret_name: str,
    include_disabled: bool = False,
) -> list[SecretVersionInfo]:
    """List all versions of a secret."""
    versions = []
    async for props in self._client.list_properties_of_secret_versions(secret_name):
        if include_disabled or props.enabled:
            versions.append(SecretVersionInfo(
                version=props.version,
                created_on=props.created_on,
                enabled=props.enabled,
            ))
    return sorted(versions, key=lambda v: v.created_on, reverse=True)
```

#### Feature 8: Certificate Management

**Why**: Full Key Vault integration should support certificates, not just secrets.

```python
from azure.keyvault.certificates import CertificateClient, CertificatePolicy

class KeyVaultCertificateManager:
    """Certificate management for Key Vault."""

    async def get_certificate(
        self,
        certificate_name: str,
        include_private_key: bool = False,
    ) -> CertificateBundle:
        """Get certificate with optional private key."""
        cert = await self._cert_client.get_certificate(certificate_name)

        if include_private_key:
            # Private key is stored as a secret with same name
            secret = await self._secret_client.get_secret(certificate_name)
            return CertificateBundle(
                certificate=cert.cer,
                private_key=secret.value,
                thumbprint=cert.properties.x509_thumbprint,
            )

        return CertificateBundle(
            certificate=cert.cer,
            thumbprint=cert.properties.x509_thumbprint,
        )
```

#### Feature 9: Key Management (Encryption Keys)

**Why**: Azure Key Vault keys enable application-level encryption.

```python
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm

class KeyVaultCryptoManager:
    """Cryptographic operations using Key Vault keys."""

    async def encrypt(
        self,
        key_name: str,
        plaintext: bytes,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.rsa_oaep,
    ) -> bytes:
        """Encrypt data using Key Vault key."""
        crypto_client = CryptographyClient(
            key=f"{self._vault_url}/keys/{key_name}",
            credential=self._credential,
        )
        result = await crypto_client.encrypt(algorithm, plaintext)
        return result.ciphertext

    async def wrap_key(
        self,
        key_name: str,
        key_to_wrap: bytes,
        algorithm: KeyWrapAlgorithm = KeyWrapAlgorithm.rsa_oaep,
    ) -> bytes:
        """Wrap (encrypt) a symmetric key with Key Vault key."""
        crypto_client = CryptographyClient(
            key=f"{self._vault_url}/keys/{key_name}",
            credential=self._credential,
        )
        result = await crypto_client.wrap_key(algorithm, key_to_wrap)
        return result.encrypted_key
```

### 3.3 Priority 3: Advanced (High Value, High Effort)

#### Feature 10: Audit Logging of Secret Access

**Why**: Compliance (SOC2, ISO27001) requires tracking who accessed what secrets.

```python
import structlog
from typing import Callable, Optional

class AuditedSecretClient:
    """Key Vault client with audit logging."""

    def __init__(
        self,
        client: SecretClient,
        audit_logger: Optional[structlog.BoundLogger] = None,
        on_access: Optional[Callable[[str, str], None]] = None,
    ):
        self._client = client
        self._logger = audit_logger or structlog.get_logger()
        self._on_access = on_access

    async def get_secret(self, secret_name: str) -> KeyVaultSecret:
        """Get secret with audit logging."""
        self._logger.info(
            "secret_accessed",
            secret_name=secret_name,
            vault_url=self._client.vault_url,
            timestamp=datetime.utcnow().isoformat(),
        )

        if self._on_access:
            self._on_access(secret_name, "read")

        return await self._client.get_secret(secret_name)
```

**Integration with Azure Monitor**:
```python
# Enable Key Vault diagnostic logs
# Category: AuditEvent captures all secret operations
# Query:
# AzureDiagnostics
# | where Category == "AuditEvent"
# | where OperationName == "SecretGet"
```

#### Feature 11: Local Development Secret Caching

**Why**: Reduce Key Vault calls during development, enable offline mode.

```python
import json
from pathlib import Path

class LocalSecretCache:
    """Persistent local cache for development mode."""

    CACHE_FILE = Path.home() / ".netrun" / "secret_cache.json"

    def __init__(self, encryption_key: Optional[bytes] = None):
        self._encryption_key = encryption_key
        self._cache: dict[str, CachedSecret] = {}
        self._load_cache()

    def _load_cache(self):
        if self.CACHE_FILE.exists():
            data = self.CACHE_FILE.read_text()
            if self._encryption_key:
                data = self._decrypt(data)
            self._cache = json.loads(data)

    def _save_cache(self):
        data = json.dumps(self._cache, default=str)
        if self._encryption_key:
            data = self._encrypt(data)
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.CACHE_FILE.write_text(data)
```

#### Feature 12: Cross-Tenant Key Vault Access

**Why**: Azure Lighthouse scenarios for MSP clients.

**Important Limitation**: Azure Lighthouse does NOT support direct Key Vault secrets access.

**Alternative**: Multi-tenant application registration pattern.

```python
from azure.identity import ClientSecretCredential

class CrossTenantVaultClient:
    """Access Key Vault in different Azure AD tenant."""

    def __init__(
        self,
        vault_url: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
    ):
        # Multi-tenant app must be consented in target tenant
        self._credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self._client = SecretClient(
            vault_url=vault_url,
            credential=self._credential,
        )
```

#### Feature 13: Private Endpoint Support

**Why**: Enterprise security requires no public endpoint exposure.

**Configuration Pattern**:
```python
class PrivateEndpointConfig:
    """Configuration for private endpoint access."""
    vault_url: str
    use_private_endpoint: bool = False
    private_dns_zone: Optional[str] = None
    vnet_subnet_id: Optional[str] = None

# Note: Private endpoint access requires:
# 1. Application running inside VNet with private endpoint
# 2. Private DNS zone linked to VNet
# 3. Key Vault firewall allowing private endpoint
```

#### Feature 14: Event Grid Integration for Rotation

**Why**: Real-time rotation notification instead of polling.

```python
from azure.eventgrid import EventGridPublisherClient

class RotationEventHandler:
    """Handle Key Vault rotation events from Event Grid."""

    async def handle_secret_near_expiry(self, event: dict):
        """Handle SecretNearExpiry event (30 days before expiry)."""
        secret_name = event['data']['objectName']
        vault_uri = event['data']['vaultName']
        expiry_date = event['data']['exp']

        # Trigger rotation workflow
        await self._trigger_rotation(secret_name, vault_uri)

    async def handle_secret_new_version(self, event: dict):
        """Handle SecretNewVersionCreated event."""
        secret_name = event['data']['objectName']
        new_version = event['data']['version']

        # Invalidate cache for this secret
        self._cache.invalidate(secret_name)

        # Notify dependent services
        await self._notify_rotation_complete(secret_name, new_version)
```

#### Feature 15: Secret Decorator Injection

**Why**: Clean, declarative secret injection like AWS's `@InjectSecretString`.

```python
from functools import wraps
from typing import Callable, TypeVar

F = TypeVar('F', bound=Callable)

def inject_secret(
    secret_name: str,
    parameter_name: str,
    vault: str = 'default',
    cache_ttl: int = 3600,
) -> Callable[[F], F]:
    """Decorator to inject Key Vault secret into function parameter."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if parameter_name not in kwargs:
                secret_value = await get_secret_async(
                    secret_name, vault=vault
                )
                kwargs[parameter_name] = secret_value
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@inject_secret('database-password', 'db_password')
async def connect_database(db_host: str, db_password: str):
    return await create_connection(db_host, db_password)
```

---

## 4. Unique Value Proposition Opportunities

### 4.1 Netrun-Specific Differentiators

| Feature | pydantic-settings | dynaconf | netrun-config (proposed) |
|---------|-------------------|----------|--------------------------|
| Azure KV TTL Cache | No | No | Yes (configurable) |
| Multi-Vault | No | No | Yes |
| Rotation Detection | No | No | Yes (poll + Event Grid) |
| Audit Logging | No | No | Yes (structlog integration) |
| Certificate Mgmt | No | No | Yes |
| Lazy Loading | No | Yes | Yes (descriptor pattern) |
| Cross-Tenant | No | No | Partial (app registration) |
| Local Dev Cache | No | No | Yes (encrypted file) |
| Batch Prefetch | No | No | Yes (async gather) |

### 4.2 Target Market Positioning

**Primary**: Azure-first Python shops needing enterprise configuration management.

**Secondary**: Multi-cloud organizations using Azure Key Vault alongside other providers.

**Message**: "The only Python configuration library with enterprise-grade Azure Key Vault integration - caching, rotation, certificates, and audit logging built-in."

### 4.3 Integration with Netrun Service Catalog

Relevant services from the 44+ catalog:
- **Service 03 (AI-Assisted IT Automation)**: Secret management for AI agents
- **Service 12 (Compliance Automation)**: Audit logging for SOC2/ISO27001
- **Service 28 (Azure Management)**: Native Azure Key Vault integration
- **Service 36 (Security Operations)**: Secret rotation and monitoring

---

## 5. Implementation Priority Recommendations

### Phase 1: Foundation (2-3 weeks)
1. **TTL-Based Caching** - Replace infinite cache with configurable TTL
2. **Pydantic Settings Source** - Migrate from mixin to proper settings source
3. **Improved Credential Chain** - Use DefaultAzureCredential exclusively

### Phase 2: Enterprise Features (3-4 weeks)
4. **Multi-Vault Support** - Environment-specific vault configuration
5. **Batch Prefetching** - Async batch loading at startup
6. **Lazy Loading Descriptors** - On-demand secret resolution

### Phase 3: Advanced (4-6 weeks)
7. **Secret Rotation Detection** - Poll-based version checking
8. **Audit Logging** - Structured logging with correlation IDs
9. **Certificate Management** - Full certificate lifecycle support

### Phase 4: Premium (6-8 weeks)
10. **Key Management/Crypto** - Encryption key operations
11. **Event Grid Integration** - Real-time rotation notifications
12. **Local Development Cache** - Encrypted persistent cache
13. **Cross-Tenant Support** - Multi-tenant app patterns

---

## 6. Code Patterns Reference

### 6.1 Complete Enhanced KeyVaultClient

```python
"""
Enhanced Azure Key Vault client for netrun-config v2.0.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Protocol, TypeVar
import asyncio
import logging

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.keyvault.certificates import CertificateClient
from azure.keyvault.keys import KeyClient

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for secret caching."""
    default_ttl_seconds: int = 28800  # 8 hours per Microsoft guidance
    soft_ttl_seconds: int = 3600      # 1 hour soft expiry triggers refresh
    max_cache_size: int = 500
    retry_delay_base: float = 1.0
    retry_delay_max: float = 300.0
    retry_growth_factor: float = 2.0


@dataclass
class CachedSecret:
    """Cached secret with TTL metadata."""
    value: str
    version: str
    fetched_at: datetime
    ttl_seconds: int = 28800

    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.fetched_at).total_seconds()

    @property
    def is_soft_expired(self) -> bool:
        """Soft expiry - trigger background refresh."""
        return self.age_seconds > (self.ttl_seconds * 0.75)

    @property
    def is_hard_expired(self) -> bool:
        """Hard expiry - must refresh before returning."""
        return self.age_seconds > self.ttl_seconds


@dataclass
class VaultConfig:
    """Configuration for a single Key Vault."""
    url: str
    credential: Optional[Any] = None
    cache_config: CacheConfig = field(default_factory=CacheConfig)


class EnhancedKeyVaultClient:
    """
    Enhanced Key Vault client with:
    - TTL-based caching
    - Multi-vault support
    - Rotation detection
    - Batch fetching
    - Audit logging
    """

    def __init__(
        self,
        vaults: Dict[str, VaultConfig],
        default_vault: str = 'default',
        audit_logger: Optional[logging.Logger] = None,
    ):
        self._vaults = vaults
        self._default_vault = default_vault
        self._audit_logger = audit_logger or logger
        self._secret_clients: Dict[str, SecretClient] = {}
        self._cache: Dict[str, CachedSecret] = {}
        self._background_tasks: set = set()

        # Initialize clients
        for name, config in vaults.items():
            credential = config.credential or DefaultAzureCredential(
                exclude_shared_token_cache_credential=True,
            )
            self._secret_clients[name] = SecretClient(
                vault_url=config.url,
                credential=credential,
            )

    def get_secret(
        self,
        secret_name: str,
        vault: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Optional[str]:
        """
        Get secret with TTL-based caching.

        Args:
            secret_name: Name of the secret in Key Vault
            vault: Vault name (uses default if not specified)
            force_refresh: Force fetch from Key Vault

        Returns:
            Secret value or None if not found
        """
        vault = vault or self._default_vault
        cache_key = f"{vault}:{secret_name}"

        # Check cache
        if not force_refresh and cache_key in self._cache:
            cached = self._cache[cache_key]

            if cached.is_soft_expired and not cached.is_hard_expired:
                # Trigger background refresh
                self._schedule_background_refresh(secret_name, vault)

            if not cached.is_hard_expired:
                return cached.value

        # Fetch from Key Vault
        return self._fetch_and_cache(secret_name, vault)

    def _fetch_and_cache(
        self,
        secret_name: str,
        vault: str,
    ) -> Optional[str]:
        """Fetch secret from Key Vault and cache it."""
        client = self._secret_clients.get(vault)
        if not client:
            raise ValueError(f"Unknown vault: {vault}")

        cache_key = f"{vault}:{secret_name}"
        config = self._vaults[vault]

        try:
            secret = client.get_secret(secret_name)

            # Audit log
            self._audit_logger.info(
                "secret_accessed",
                extra={
                    'secret_name': secret_name,
                    'vault': vault,
                    'version': secret.properties.version,
                    'action': 'fetch',
                }
            )

            # Cache
            self._cache[cache_key] = CachedSecret(
                value=secret.value,
                version=secret.properties.version,
                fetched_at=datetime.now(),
                ttl_seconds=config.cache_config.default_ttl_seconds,
            )

            return secret.value

        except ResourceNotFoundError:
            self._audit_logger.warning(
                "secret_not_found",
                extra={'secret_name': secret_name, 'vault': vault}
            )
            return None

    def _schedule_background_refresh(self, secret_name: str, vault: str):
        """Schedule background refresh for near-expiry secret."""
        # Implementation depends on async context
        pass

    async def prefetch_secrets(
        self,
        secrets: Dict[str, list[str]],  # {vault: [secret_names]}
        concurrency: int = 10,
    ) -> Dict[str, str]:
        """
        Batch prefetch secrets from multiple vaults.

        Args:
            secrets: Dict mapping vault names to secret name lists
            concurrency: Maximum concurrent requests

        Returns:
            Dict mapping "vault:secret_name" to values
        """
        semaphore = asyncio.Semaphore(concurrency)
        results = {}

        async def fetch_one(vault: str, secret_name: str):
            async with semaphore:
                value = self.get_secret(secret_name, vault=vault)
                return (f"{vault}:{secret_name}", value)

        tasks = [
            fetch_one(vault, secret_name)
            for vault, secret_names in secrets.items()
            for secret_name in secret_names
        ]

        for cache_key, value in await asyncio.gather(*tasks):
            if value is not None:
                results[cache_key] = value

        return results

    def check_for_new_version(
        self,
        secret_name: str,
        vault: Optional[str] = None,
    ) -> bool:
        """
        Check if secret has a newer version than cached.

        Returns:
            True if new version available
        """
        vault = vault or self._default_vault
        cache_key = f"{vault}:{secret_name}"

        cached = self._cache.get(cache_key)
        if not cached:
            return True

        client = self._secret_clients[vault]
        current_props = client.get_secret(secret_name).properties

        return current_props.version != cached.version

    def invalidate(
        self,
        secret_name: Optional[str] = None,
        vault: Optional[str] = None,
    ):
        """
        Invalidate cached secret(s).

        Args:
            secret_name: Specific secret to invalidate (all if None)
            vault: Specific vault (all if None)
        """
        if secret_name and vault:
            self._cache.pop(f"{vault}:{secret_name}", None)
        elif vault:
            self._cache = {
                k: v for k, v in self._cache.items()
                if not k.startswith(f"{vault}:")
            }
        elif secret_name:
            self._cache = {
                k: v for k, v in self._cache.items()
                if not k.endswith(f":{secret_name}")
            }
        else:
            self._cache.clear()
```

---

## 7. Sources

### Official Documentation
- [Azure Key Vault Python Quickstart](https://learn.microsoft.com/en-us/azure/key-vault/secrets/quick-create-python)
- [Azure Key Vault Best Practices](https://learn.microsoft.com/en-us/azure/key-vault/secrets/secrets-best-practices)
- [Azure Key Vault Rotation Tutorial](https://learn.microsoft.com/en-us/azure/key-vault/secrets/tutorial-rotation)
- [Azure Key Vault Event Grid Integration](https://learn.microsoft.com/en-us/azure/key-vault/general/event-grid-overview)
- [Azure Key Vault Private Link](https://learn.microsoft.com/en-us/azure/key-vault/general/private-link-service)
- [Azure Key Vault Certificates Client](https://learn.microsoft.com/en-us/python/api/overview/azure/keyvault-certificates-readme)
- [Azure Key Vault Keys Client](https://learn.microsoft.com/en-us/python/api/overview/azure/keyvault-keys-readme)
- [pydantic-settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

### Third-Party Libraries
- [AWS Secrets Manager Python Caching](https://github.com/aws/aws-secretsmanager-caching-python)
- [hvac - HashiCorp Vault Python Client](https://python-hvac.org/)
- [dynaconf Documentation](https://www.dynaconf.com/)
- [pydantic-settings-vault](https://pypi.org/project/pydantic-settings-vault/)
- [pydantic-azure-secrets](https://github.com/kewtree1408/pydantic-azure-secrets)

### Community Resources
- [dynaconf Azure Key Vault Issue #1192](https://github.com/dynaconf/dynaconf/issues/1192)
- [Azure SDK Lazy Loading Issue #36205](https://github.com/Azure/azure-sdk-for-python/issues/36205)

---

## Micro-Retrospective

### What Went Well
1. Comprehensive discovery of pydantic-settings native `AzureKeyVaultSettingsSource` - this fundamentally changes the architecture recommendation
2. AWS Secrets Manager caching library provided excellent patterns for TTL configuration
3. Clear gap analysis between netrun-config current state and industry best practices

### What Needs Improvement
1. Initial search for python-dotenv-vault was a dead end (different product than expected)
2. Cross-tenant Key Vault research could have been faster by identifying Lighthouse limitations earlier

### Action Items
1. **Update netrun-config roadmap** with phased implementation plan by 2025-12-10
2. **Create proof-of-concept** for pydantic settings source pattern by 2025-12-15

### Patterns Discovered
- **Pattern**: AWS-style `SecretCacheConfig` dataclass for configurable caching
- **Anti-Pattern**: Indefinite caching without TTL (current netrun-config implementation)

---

*Generated by Technical Research Specialist Agent*
*Netrun Systems - SDLC v2.1 Compliant*
