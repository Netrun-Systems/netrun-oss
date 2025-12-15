# Changelog

All notable changes to netrun-logging are documented here.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [1.0.0] - 2025-11-24

### Added
- Initial public release
- Core logging functionality with JSON formatting
- Thread-safe correlation ID tracking
- Request-scoped log context management
- FastAPI middleware for automatic request/response logging
- Azure App Insights integration with graceful fallback
- Comprehensive API documentation
- Examples for basic usage, FastAPI, and Azure integration
- Full test coverage (95%+ of codebase)
- Type hints for all public APIs

### Features
- `configure_logging()` - Configure logging at application startup
- `get_logger()` - Get configured logger instances
- `generate_correlation_id()` - Generate UUID4 correlation IDs
- `get_correlation_id()` / `set_correlation_id()` - Correlation ID context management
- `correlation_id_context()` - Context manager for scoped correlation ID tracking
- `set_context()` / `get_context()` / `clear_context()` - Request-scoped logging context
- `JsonFormatter` - Machine-readable JSON log formatting
- `CorrelationIdMiddleware` - FastAPI middleware for correlation ID injection
- `LoggingMiddleware` - FastAPI middleware for request/response logging
- `add_logging_middleware()` - Helper to add both middlewares

### Performance
- Zero-copy log formatting
- Minimal overhead (<1ms per log on modern hardware)
- Efficient context variable usage with contextvars

### Quality
- 95%+ code coverage
- All functions type-hinted
- Comprehensive docstrings
- Multiple integration examples

---

## Upcoming Features

### [1.1.0] - Planned
- **Structured Logging Extensions**
  - Support for additional cloud providers (GCP Cloud Logging, AWS CloudWatch)
  - Custom field transformers
  - Sensitive data redaction

- **Performance Improvements**
  - Batch log sending to cloud providers
  - Configurable buffer sizes
  - Async handler support

- **Developer Experience**
  - CLI tool for local log inspection
  - Log filtering utilities
  - Integration with popular observability tools

### [2.0.0] - Future
- Full async/await support throughout
- Pluggable formatter architecture
- Custom middleware builder
- Advanced sampling strategies

---

## Version History

### Versions 0.x (Development)
- 0.1.0 - Initial development version with core functionality
- 0.2.0 - Added FastAPI middleware support
- 0.3.0 - Added Azure App Insights integration
- 0.4.0 - Added correlation ID tracking
- 0.5.0 - Added log context management
- 0.6.0 - Performance optimizations
- 0.7.0 - Improved error handling
- 0.8.0 - Added comprehensive testing
- 0.9.0 - Documentation and examples
- 0.9.5 - Final pre-release polish

---

## Migration Guide

### From Standard Python logging

Replace:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

With:

```python
from netrun_logging import configure_logging, get_logger

configure_logging(app_name="my-app")
logger = get_logger(__name__)
```

### Benefits
- Automatic JSON formatting
- Built-in correlation ID tracking
- Azure integration without extra code
- FastAPI middleware included

---

## Support & Reporting

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/netrun-services/netrun-logging/issues
- Documentation: https://netrun-logging.readthedocs.io
- Email: support@netrunsystems.com

---

## License

MIT License - See LICENSE file for details

Copyright (c) 2025 Netrun Systems
