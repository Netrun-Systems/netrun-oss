# netrun-cors

Enterprise CORS middleware presets for FastAPI applications.

## Overview

`netrun-cors` provides standardized, production-ready CORS configurations for FastAPI applications. Instead of manually configuring CORS middleware for each project, use battle-tested presets that follow OWASP security best practices.

**Key Features:**
- 4 preset configurations: `development`, `staging`, `production`, `oauth`
- OWASP compliance validation (prevents wildcard + credentials vulnerability)
- OAuth platform support (Google, Twitter, LinkedIn, Facebook, TikTok, Instagram, Pinterest, Threads)
- Azure Container Apps integration
- Type-safe configuration with Pydantic
- Comprehensive test coverage (90%+)

## Installation

```bash
pip install netrun-cors
```

Or with Poetry:
```bash
poetry add netrun-cors
```

## Quick Start

### Development (Local Development)

Permissive CORS for rapid iteration on localhost:

```python
from fastapi import FastAPI
from netrun_cors import CORSPreset

app = FastAPI()
app.add_middleware(CORSPreset.development())
```

**Configuration:**
- Origins: `localhost:3000`, `localhost:5173`, `127.0.0.1:3000` (HTTP)
- Credentials: Enabled
- Methods: All (`*`)
- Headers: All (`*`)
- Max Age: 600s (10 minutes)

---

### Production (Explicit Whitelist)

Strict origin whitelisting for production deployments:

```python
from fastapi import FastAPI
from netrun_cors import CORSPreset

app = FastAPI()
app.add_middleware(
    CORSPreset.production(
        origins=[
            "https://app.example.com",
            "https://www.example.com"
        ]
    )
)
```

**Configuration:**
- Origins: Explicit whitelist (HTTPS recommended)
- Credentials: Enabled
- Methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `PATCH`
- Headers: `Authorization`, `Content-Type`, `Accept`, `X-Request-ID`
- Expose Headers: `X-Request-ID`
- Max Age: 3600s (1 hour)

---

### Staging (Azure Container Apps)

Support for Azure Container Apps with wildcard environment hashes:

```python
from fastapi import FastAPI
from netrun_cors import CORSPreset

app = FastAPI()
app.add_middleware(
    CORSPreset.staging(
        container_apps=["intirkast-frontend", "meridian-frontend"],
        region="eastus2"
    )
)
```

**Configuration:**
- Origins: `https://localhost:3000`, `5173` + Azure Container Apps wildcards
- Credentials: Enabled
- Methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `PATCH`
- Headers: `Authorization`, `Content-Type`, `Accept`, `X-Requested-With`, `X-Request-ID`
- Max Age: 1800s (30 minutes)

**Optional Additional Origins:**
```python
app.add_middleware(
    CORSPreset.staging(
        container_apps=["test-app"],
        additional_origins=["https://staging.example.com"]
    )
)
```

---

### OAuth (Social Platform Integration)

Whitelist OAuth callback domains for social login flows:

```python
from fastapi import FastAPI
from netrun_cors import CORSPreset

app = FastAPI()
app.add_middleware(
    CORSPreset.oauth(
        app_origins=["https://app.intirkast.com"],
        platforms=["google", "twitter", "linkedin", "facebook"]
    )
)
```

**Configuration:**
- Origins: App origins + OAuth platform domains
- Credentials: Enabled
- Methods: All (`*`)
- Headers: All (`*`)
- Expose Headers: All (`*`)
- Max Age: 3600s (1 hour)

**Supported Platforms:**
| Platform | Domain |
|----------|--------|
| `google` | `https://accounts.google.com` |
| `twitter` | `https://twitter.com` |
| `linkedin` | `https://www.linkedin.com` |
| `facebook` | `https://www.facebook.com` |
| `tiktok` | `https://www.tiktok.com` |
| `instagram` | `https://www.instagram.com` |
| `pinterest` | `https://www.pinterest.com` |
| `threads` | `https://www.threads.net` |

---

## Advanced Usage

### Custom Configuration

If presets don't match your requirements, use `CORSPreset.custom()`:

```python
from netrun_cors import CORSPreset

app.add_middleware(
    CORSPreset.custom(
        allow_origins=["https://app.example.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
        max_age=1200
    )
)
```

**OWASP Compliance Validation:**

The custom preset validates against OWASP security guidelines:

```python
# ❌ This will raise ValueError
app.add_middleware(
    CORSPreset.custom(
        allow_origins=["*"],  # Wildcard
        allow_credentials=True  # Credentials enabled
    )
)
# ValueError: OWASP Violation: Cannot use wildcard origins with credentials
```

---

### Environment Variable Configuration

Use `CORSConfig` for environment-based configuration:

```python
from netrun_cors import CORSConfig

config = CORSConfig()
# Reads from environment variables:
# CORS_ORIGINS=https://app.example.com,https://www.example.com
# CORS_ALLOW_CREDENTIALS=true
# CORS_MAX_AGE=3600

app.add_middleware(
    CORSPreset.production(origins=config.CORS_ORIGINS)
)
```

**.env file example:**
```bash
CORS_ORIGINS=https://app.example.com,https://www.example.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE
CORS_ALLOW_HEADERS=Authorization,Content-Type
CORS_EXPOSE_HEADERS=X-Request-ID,X-Process-Time
CORS_MAX_AGE=3600
```

---

## Migration Guide

### Before: Manual CORS Configuration

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://app.intirkast.com",
        "https://intirkast-frontend.orangesmoke-f0fb748a.eastus2.azurecontainerapps.io",
        "https://accounts.google.com",  # Google OAuth
        "https://twitter.com",  # Twitter OAuth
        "https://www.linkedin.com",  # LinkedIn OAuth
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
    max_age=3600,
)
```

**LOC: 18 lines**

---

### After: netrun-cors

```python
from fastapi import FastAPI
from netrun_cors import CORSPreset

app = FastAPI()
app.add_middleware(
    CORSPreset.oauth(
        app_origins=["https://app.intirkast.com"],
        platforms=["google", "twitter", "linkedin"]
    )
)
```

**LOC: 2 lines (89% reduction)**

---

## Security Best Practices

### 1. Production Origin Whitelisting

Always use explicit origin lists in production:

```python
# ✅ Secure (explicit origins)
app.add_middleware(
    CORSPreset.production(origins=["https://app.example.com"])
)

# ❌ Insecure (wildcard in production)
app.add_middleware(
    CORSPreset.custom(allow_origins=["*"], allow_credentials=False)
)
```

---

### 2. HTTPS Only in Production

Use HTTPS origins for production deployments:

```python
# ✅ Secure (HTTPS)
origins = [
    "https://app.example.com",
    "https://www.example.com"
]

# ❌ Insecure (HTTP in production)
origins = [
    "http://app.example.com",  # Vulnerable to MITM attacks
]
```

---

### 3. Minimize Exposed Headers

Only expose headers your frontend needs:

```python
# ✅ Minimal (production)
expose_headers = ["X-Request-ID"]

# ⚠️ Permissive (development only)
expose_headers = ["*"]
```

---

### 4. Preflight Caching

Use appropriate `max_age` for preflight caching:

```python
# Production: 1 hour (reduces preflight overhead)
app.add_middleware(CORSPreset.production(origins=[...]))  # max_age=3600

# Development: 10 minutes (faster iteration)
app.add_middleware(CORSPreset.development())  # max_age=600
```

---

## Testing

Run the test suite with pytest:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=netrun_cors --cov-report=term-missing

# Run tests with verbose output
pytest -v
```

---

## API Reference

### CORSPreset

Factory class for standardized CORS middleware configurations.

#### Methods

##### `development()`

Permissive CORS for local development (localhost origins).

**Returns:** `CORSMiddleware`

**Example:**
```python
app.add_middleware(CORSPreset.development())
```

---

##### `staging(container_apps, region, additional_origins)`

Azure Container Apps staging environment with wildcard support.

**Parameters:**
- `container_apps` (List[str]): Azure Container App names
- `region` (str): Azure region (default: `"eastus2"`)
- `additional_origins` (Optional[List[str]]): Additional origins to whitelist

**Returns:** `CORSMiddleware`

**Example:**
```python
app.add_middleware(
    CORSPreset.staging(
        container_apps=["test-app"],
        region="westus2"
    )
)
```

---

##### `production(origins)`

Production deployment with explicit origin whitelisting.

**Parameters:**
- `origins` (List[str]): List of allowed production origins

**Returns:** `CORSMiddleware`

**Example:**
```python
app.add_middleware(
    CORSPreset.production(origins=["https://app.example.com"])
)
```

---

##### `oauth(app_origins, platforms)`

OAuth-enabled applications with social platform callback domains.

**Parameters:**
- `app_origins` (List[str]): Application origins
- `platforms` (List[str]): OAuth platform identifiers

**Returns:** `CORSMiddleware`

**Raises:**
- `ValueError`: If invalid platform identifier provided

**Example:**
```python
app.add_middleware(
    CORSPreset.oauth(
        app_origins=["https://app.example.com"],
        platforms=["google", "twitter"]
    )
)
```

---

##### `custom(**kwargs)`

Custom CORS configuration with full control.

**Parameters:**
- `allow_origins` (List[str]): List of allowed origins
- `allow_credentials` (bool): Allow credentials (default: `True`)
- `allow_methods` (Optional[List[str]]): Allowed HTTP methods
- `allow_headers` (Optional[List[str]]): Allowed headers
- `expose_headers` (Optional[List[str]]): Exposed headers
- `max_age` (int): Preflight cache duration in seconds

**Returns:** `CORSMiddleware`

**Raises:**
- `ValueError`: If wildcard origins combined with credentials

**Example:**
```python
app.add_middleware(
    CORSPreset.custom(
        allow_origins=["https://app.example.com"],
        allow_methods=["GET", "POST"],
        max_age=1200
    )
)
```

---

### CORSConfig

Pydantic settings for type-safe CORS configuration with environment variable support.

**Attributes:**
- `CORS_ORIGINS` (List[str]): Allowed origins (default: localhost)
- `CORS_ALLOW_CREDENTIALS` (bool): Allow credentials (default: `True`)
- `CORS_ALLOW_METHODS` (List[str]): Allowed methods (default: `["*"]`)
- `CORS_ALLOW_HEADERS` (List[str]): Allowed headers (default: `["*"]`)
- `CORS_EXPOSE_HEADERS` (List[str]): Exposed headers (default: `["X-Request-ID", "X-Process-Time"]`)
- `CORS_MAX_AGE` (int): Preflight cache duration (default: `3600`)

**Example:**
```python
from netrun_cors import CORSConfig

config = CORSConfig()
print(config.CORS_ORIGINS)  # ['http://localhost:3000', 'http://localhost:5173']
```

---

## Performance Considerations

### Preflight Caching

CORS preflight requests (OPTIONS) can add latency. Use `max_age` to cache preflight responses:

| Environment | max_age | Rationale |
|-------------|---------|-----------|
| Development | 600s (10 min) | Fast iteration, frequent changes |
| Staging | 1800s (30 min) | Balance between testing and performance |
| Production | 3600s (1 hour) | Maximum performance, stable configuration |

---

### Origin Matching Performance

Explicit origin lists have O(n) lookup time. For large origin lists (100+), consider:
1. Using a reverse proxy (Nginx, Cloudflare) for CORS
2. Implementing origin caching in your application
3. Grouping origins by environment (dev, staging, prod)

---

## Troubleshooting

### Common Issues

#### 1. CORS Error: "No 'Access-Control-Allow-Origin' header"

**Cause:** Origin not whitelisted in CORS configuration

**Solution:** Add origin to allowed list:
```python
app.add_middleware(
    CORSPreset.production(
        origins=[
            "https://app.example.com",
            "https://new-origin.example.com"  # Add missing origin
        ]
    )
)
```

---

#### 2. CORS Error: "Wildcard with credentials"

**Cause:** Attempting to use `allow_origins=["*"]` with `allow_credentials=True`

**Solution:** Use explicit origins or disable credentials:
```python
# Option 1: Explicit origins (recommended)
app.add_middleware(
    CORSPreset.production(origins=["https://app.example.com"])
)

# Option 2: Disable credentials
app.add_middleware(
    CORSPreset.custom(allow_origins=["*"], allow_credentials=False)
)
```

---

#### 3. OAuth Callback Failure

**Cause:** OAuth platform domain not whitelisted

**Solution:** Use `oauth` preset with appropriate platforms:
```python
app.add_middleware(
    CORSPreset.oauth(
        app_origins=["https://app.example.com"],
        platforms=["google", "twitter", "linkedin"]
    )
)
```

---

#### 4. Azure Container Apps Staging Issues

**Cause:** Dynamic environment hash not matching

**Solution:** Use `staging` preset with wildcard support:
```python
app.add_middleware(
    CORSPreset.staging(
        container_apps=["intirkast-frontend"],
        region="eastus2"
    )
)
```

---

## Contributing

Contributions welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-preset`)
3. Write tests for new functionality
4. Ensure tests pass (`pytest`)
5. Run linters (`black`, `ruff`, `mypy`)
6. Submit a pull request

---

## License

MIT License - see LICENSE file for details.

---

## Support

**Issues:** [GitHub Issues](https://github.com/netrunsystems/netrun-cors/issues)
**Email:** support@netrunsystems.com
**Documentation:** [GitHub Repository](https://github.com/netrunsystems/netrun-cors)

---

## Changelog

### v1.0.0 (2025-11-25)

**Initial Release:**
- 4 preset configurations (development, staging, production, oauth)
- OWASP compliance validation
- 8 OAuth platform support
- Azure Container Apps integration
- Pydantic configuration support
- Comprehensive test suite (90%+ coverage)

---

**Developed by [Netrun Systems](https://netrunsystems.com)**
