# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-04

### Added
- Initial stable release of netrun-cors
- 4 preset CORS configurations: development, staging, production, oauth
- Development preset for local development with permissive localhost origins
- Production preset with explicit origin whitelisting for secure deployments
- Staging preset with Azure Container Apps wildcard support
- OAuth preset for social platform integration (8 platforms supported)
- OWASP compliance validation preventing wildcard + credentials vulnerability
- Custom CORS configuration with full control and validation
- Environment variable configuration support via CORSConfig
- Azure Container Apps integration with automatic wildcard environment hash generation
- Type-safe configuration with Pydantic 2.0+
- Comprehensive test coverage (90%+)
- Support for Python 3.11 and 3.12
- Automatic origin validation and security checks

### Features
- **Development Preset**: Permissive CORS for localhost:3000, localhost:5173, 127.0.0.1:3000 with HTTP support
- **Production Preset**: Strict origin whitelisting (HTTPS recommended), credential support, 1-hour preflight caching
- **Staging Preset**: Azure Container Apps support with wildcard environment hashes, 30-minute caching
- **OAuth Preset**: Automatic whitelisting of social platform callback domains (8 platforms)
- **Custom Configuration**: Full control over origins, methods, headers, and caching
- **OWASP Compliance**: Validates against security best practices (prevents wildcard + credentials)
- **Security Best Practices**: HTTPS enforcement, minimal header exposure, preflight caching optimization

### Supported OAuth Platforms
- Google (https://accounts.google.com)
- Twitter (https://twitter.com)
- LinkedIn (https://www.linkedin.com)
- Facebook (https://www.facebook.com)
- TikTok (https://www.tiktok.com)
- Instagram (https://www.instagram.com)
- Pinterest (https://www.pinterest.com)
- Threads (https://www.threads.net)

### Configuration Options
- `allow_origins`: List of allowed origin URLs
- `allow_credentials`: Enable/disable credential support (default: True)
- `allow_methods`: HTTP methods (default: wildcard)
- `allow_headers`: Request headers (default: wildcard)
- `expose_headers`: Response headers exposed to browser
- `max_age`: Preflight cache duration in seconds

### Dependencies
- fastapi >= 0.109.0
- pydantic >= 2.0.0
- pydantic-settings >= 2.0.0
- starlette >= 0.27.0

### Optional Dependencies
- pytest >= 7.4.0, pytest-asyncio >= 0.21.0, pytest-cov >= 4.1.0 (testing)
- httpx >= 0.25.0 (HTTP client for testing)
- black >= 23.0.0 (code formatting)
- ruff >= 0.1.0 (linting)
- mypy >= 1.7.0 (type checking)

### Code Reduction
- Migration from manual CORS configuration (18 lines) to netrun-cors (2 lines)
- 89% reduction in CORS configuration boilerplate
- Simplified OAuth platform integration

---

## Release Notes

### What's Included

This initial release provides enterprise-grade CORS middleware presets for FastAPI applications. It eliminates manual CORS configuration while enforcing OWASP security best practices across development, staging, production, and OAuth integration scenarios.

### Key Benefits

- **Standardized Security**: OWASP-compliant configurations prevent common misconfigurations
- **Reduced Boilerplate**: 89% code reduction compared to manual CORS setup
- **Production Ready**: Explicit whitelisting, HTTPS enforcement, and credential management
- **Cloud Native**: Azure Container Apps support with automatic wildcard generation
- **Developer Friendly**: Clear presets for common deployment scenarios

### Compatibility

- Python: 3.11, 3.12
- FastAPI: 0.109+
- Starlette: 0.27+

### Installation

```bash
pip install netrun-cors
pip install netrun-cors[dev]  # With development dependencies
```

### Quick Start Examples

```python
# Development
app.add_middleware(CORSPreset.development())

# Production
app.add_middleware(CORSPreset.production(origins=["https://app.example.com"]))

# Staging (Azure)
app.add_middleware(CORSPreset.staging(container_apps=["my-app"], region="eastus2"))

# OAuth
app.add_middleware(CORSPreset.oauth(app_origins=["https://app.example.com"], platforms=["google", "twitter"]))
```

### Performance Considerations

- Preflight caching reduces unnecessary OPTIONS requests
- O(n) origin matching for explicit lists (efficient for typical use cases)
- Reverse proxy recommended for 100+ origins

### Support

- Documentation: https://github.com/netrunsystems/netrun-cors
- GitHub: https://github.com/netrunsystems/netrun-cors
- Issues: https://github.com/netrunsystems/netrun-cors/issues
- Email: support@netrunsystems.com
- Website: https://netrunsystems.com

---

**[1.0.0] - 2025-12-04**
