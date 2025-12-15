# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-04

### Added
- Initial stable release of netrun-env (Service #69)
- Schema-based environment variable validation for .env files
- Comprehensive security checks for development, staging, and production environments
- Automatic JSON schema generation from example .env files
- Security enforcement with minimum secret length requirements (32 characters)
- JWT algorithm whitelisting (RS256/RS384/RS512/ES256 only - asymmetric algorithms)
- HTTPS enforcement in production and staging environments
- Secret strength validation and placeholder detection
- Type inference for automatic detection of URLs, emails, integers, booleans, and secrets
- Environment file comparison with secret masking for diff operations
- Command-line interface for all validation and comparison operations
- Support for Python 3.8, 3.9, 3.10, 3.11, and 3.12
- CI/CD integration examples for GitHub Actions and pre-commit hooks
- Full type safety and comprehensive testing

### Features
- **Schema-Based Validation**: Generate and validate against JSON schemas for consistency
- **Security Enforcement**:
  - Minimum secret length enforcement (32 characters)
  - JWT algorithm whitelisting (asymmetric algorithms only)
  - HTTPS enforcement in production/staging
  - Secret strength validation
  - Placeholder detection (e.g., [PASSWORD_HERE], [SECRET_KEY_HERE])
- **Type Inference**: Automatic detection of URLs, emails, integers, booleans, and secrets
- **Environment Comparison**: Diff two environment files with secret masking for sensitive data
- **CLI Interface**: Simple command-line tools for schema generation, validation, and comparison
- **Security Levels**: Three levels - development (permissive), staging (moderate), production (strictest)

### Commands
- `netrun-env generate-schema`: Generate schema from .env.example files
- `netrun-env validate`: Validate .env files against schemas with configurable security levels
- `netrun-env diff`: Compare environment files with secret masking and diff reporting
- `--strict` mode: Treat warnings as errors
- `--security-level`: Choose validation level (development, staging, production)
- `--format json`: Output results in JSON format
- `--no-mask`: Show unmasked secrets (use with caution)
- `--fail-on-diff`: Exit with error if differences found (useful in CI)

### Schema Format
- Variables with type, required, minLength, min, max, protocols, allowed_values, and example fields
- Supported types: string, integer, boolean, url, secret, email, path
- Protocol validation for URLs (https, postgresql, postgresql+asyncpg, etc.)

### Dependencies
- click >= 8.0.0 (CLI framework)
- pydantic >= 2.0.0 (data validation)
- python-dotenv >= 1.0.0 (.env file parsing)

### Optional Dependencies
- pytest >= 7.0.0, pytest-cov >= 4.0.0 (testing)
- black >= 23.0.0 (code formatting)
- ruff >= 0.1.0 (linting)
- mypy >= 1.0.0 (type checking)

### Environment Variable Patterns (Detected as Secrets)
- *_SECRET*, *_KEY, *_TOKEN, *_PASSWORD, *_CREDENTIAL*, *_API_KEY

### Allowed JWT Algorithms
- Asymmetric only: RS256, RS384, RS512, ES256, ES384, ES512
- Forbidden: HS256, HS384, HS512, none

---

## Release Notes

### What's Included

This initial release provides comprehensive environment variable validation and security enforcement for Netrun Systems services. It prevents common security misconfigurations such as weak secrets, insecure JWT algorithms, and HTTP-only URLs in production environments.

### Key Features

- **Schema Generation**: Automatically infer validation rules from example .env files
- **Security-First**: Enforces asymmetric JWT algorithms, minimum secret lengths, and HTTPS in production
- **Developer-Friendly**: Clear error messages and validation reports
- **CI/CD Ready**: GitHub Actions examples and pre-commit hook integration
- **Type Inference**: Automatically detects variable types (URL, email, integer, secret, etc.)

### Compatibility

- Python: 3.8, 3.9, 3.10, 3.11, 3.12
- Works with any .env file format compatible with python-dotenv

### Installation

```bash
pip install netrun-env
pip install netrun-env[dev]  # With development dependencies
```

### Usage Examples

```bash
# Generate schema from .env.example
netrun-env generate-schema --from .env.example --out .env.schema.json

# Validate environment with production security level
netrun-env validate --env .env.production --schema .env.schema.json --security-level production

# Compare staging and production environments
netrun-env diff --env1 .env.staging --env2 .env.production
```

### Support

- Documentation: https://github.com/netrunsystems/netrun-service-library
- GitHub: https://github.com/netrunsystems/netrun-service-library
- Issues: https://github.com/netrunsystems/netrun-service-library/issues
- Email: support@netrunsystems.com
- Website: https://netrunsystems.com

---

**[1.0.0] - 2025-12-04**
