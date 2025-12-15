# Service #61: Unified Logging - Week 1 Recreation Roadmap

**Date**: 2025-11-24
**Status**: READY TO EXECUTE
**Effort**: 11.5 hours (1.5 days)
**Owner**: @backend-developer + @code-reusability-specialist
**Timeline**: November 24-25, 2025

---

## Executive Summary

**Objective**: Recreate Service #61 Week 1 implementation using extracted patterns from existing projects

**Code Reuse Available**: 60% (GhostGrid AuditLogger + Intirkast Correlation ID)
**New Development Required**: 40% (Azure App Insights + Unified API)

**Effort Breakdown**:
- Pattern Extraction: 3.5 hours (30%)
- New Development: 5 hours (43%)
- Package Structure: 1.5 hours (13%)
- Integration: 1.5 hours (13%)
- **TOTAL**: 11.5 hours

**Timeline**: Start November 24, 15:00 PST → Complete November 25, 18:00 PST

---

## Pattern Extraction Plan

### Phase 1: Extract Reusable Patterns (3.5 hours)

#### Task 1.1: Extract JSON Formatter from GhostGrid (1 hour)
**Source**: `D:\Users\Garza\Documents\GitHub\GhostGrid Optical Network\ghostgrid-sim\src\security\audit_logger.py`
**Target**: `Service_61_Unified_Logging/netrun_logging/json_formatter.py`

**Reusable Components**:
```python
# From GhostGrid AuditLogger (lines 74-83)
def _configure_logger(self):
    """Configure JSON-formatted logging for audit trail."""
    if not self.logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": %(message)s}'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

# From GhostGrid AuditLogger (lines 105-114)
audit_entry = {
    "event_type": event.value,
    "organization_id": str(organization_id) if organization_id else None,
    "user_id": str(user_id) if user_id else None,
    "correlation_id": correlation_id,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "metadata": metadata or {},
}
log_message = json.dumps(audit_entry)
```

**Adaptation Required**:
- Generalize from `AuditLogger` to `JSONFormatter`
- Remove security-specific fields (event_type, organization_id)
- Add support for arbitrary key-value pairs (structured logging)
- Add exception formatting (stack traces)

**Deliverable**:
```python
# netrun_logging/json_formatter.py
class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging

    Outputs logs as JSON with:
    - timestamp (ISO 8601 UTC)
    - level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger name
    - message
    - correlation_id (if available)
    - extra fields (arbitrary key-value pairs)
    - exception info (if exception occurred)
    """
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS:
                log_entry[key] = value

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)
```

**Testing**:
```python
# Manual test
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.info("Test message", user_id="123", action="login")
# Expected output: {"timestamp": "2025-11-24T15:00:00", "level": "INFO", ...}
```

---

#### Task 1.2: Extract Correlation ID from Intirkast (1 hour)
**Source**: `D:\Users\Garza\Documents\GitHub\Intirkast\src\backend\app\api\dependencies.py`
**Target**: `Service_61_Unified_Logging/netrun_logging/correlation_id.py`

**Reusable Components**:
```python
# From Intirkast dependencies.py (lines 115-133)
def get_correlation_id(request: Request) -> str:
    """
    Extract correlation ID from request state
    Used for distributed tracing and log correlation across services.
    """
    return getattr(request.state, "correlation_id", "unknown")
```

**Adaptation Required**:
- Create `CorrelationContext` class for thread-local storage
- Add UUID4 generation: `CorrelationContext.generate_id()`
- Add context manager: `with CorrelationContext(correlation_id):`
- Add FastAPI middleware integration

**Deliverable**:
```python
# netrun_logging/correlation_id.py
import uuid
import contextvars
from typing import Optional

# Thread-local storage for correlation ID
_correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

class CorrelationContext:
    """
    Thread-safe correlation ID context manager

    Usage:
        correlation_id = CorrelationContext.generate_id()
        with CorrelationContext(correlation_id):
            logger.info("Request started")
            # All logs in this context include correlation_id
    """

    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self.token = None

    def __enter__(self):
        self.token = _correlation_id_var.set(self.correlation_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _correlation_id_var.reset(self.token)

    @staticmethod
    def generate_id() -> str:
        """Generate new UUID4 correlation ID"""
        return str(uuid.uuid4())

    @staticmethod
    def get() -> Optional[str]:
        """Get current correlation ID from context"""
        return _correlation_id_var.get()

# FastAPI dependency (from Intirkast pattern)
def get_correlation_id_dependency(request: Request) -> str:
    """Extract correlation ID from FastAPI request state"""
    return getattr(request.state, "correlation_id", "unknown")
```

**Testing**:
```python
# Manual test
correlation_id = CorrelationContext.generate_id()
print(f"Generated ID: {correlation_id}")  # UUID4 format

with CorrelationContext(correlation_id):
    assert CorrelationContext.get() == correlation_id
    logger.info("Inside context")  # Should include correlation_id

assert CorrelationContext.get() is None  # Outside context
```

---

#### Task 1.3: Extract Context Enrichment from GhostGrid (1 hour)
**Source**: `D:\Users\Garza\Documents\GitHub\GhostGrid Optical Network\ghostgrid-sim\src\security\audit_logger.py`
**Target**: `Service_61_Unified_Logging/netrun_logging/context_enrichment.py`

**Reusable Components**:
```python
# From GhostGrid AuditLogger (lines 85-112)
def log_event(
    self,
    event: SecurityEvent,
    organization_id: Optional[UUID],
    user_id: Optional[UUID],
    correlation_id: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    severity: str = "INFO",
):
    audit_entry = {
        "event_type": event.value,
        "organization_id": str(organization_id) if organization_id else None,
        "user_id": str(user_id) if user_id else None,
        "correlation_id": correlation_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
```

**Adaptation Required**:
- Generalize metadata injection beyond security events
- Add application metadata (app_name, environment, version)
- Add environment variable capture
- Add custom context fields

**Deliverable**:
```python
# netrun_logging/context_enrichment.py
import os
from typing import Dict, Any, Optional

class ContextEnricher:
    """
    Enrich log entries with application and environment context

    Usage:
        enricher = ContextEnricher(
            app_name="netrun-crm",
            environment="production",
            version="1.2.3"
        )
        enriched_log = enricher.enrich(log_entry)
    """

    def __init__(
        self,
        app_name: str,
        environment: Optional[str] = None,
        version: Optional[str] = None,
        **custom_context
    ):
        self.app_name = app_name
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.version = version or os.getenv("APP_VERSION", "unknown")
        self.custom_context = custom_context

    def enrich(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add context fields to log entry"""
        enriched = log_entry.copy()
        enriched.update({
            "app_name": self.app_name,
            "environment": self.environment,
            "version": self.version,
            **self.custom_context
        })
        return enriched

# Global context storage
_global_context: Dict[str, Any] = {}

def set_global_context(**context):
    """Set global context fields (added to all logs)"""
    _global_context.update(context)

def get_global_context() -> Dict[str, Any]:
    """Get current global context"""
    return _global_context.copy()

def clear_global_context():
    """Clear all global context"""
    _global_context.clear()
```

**Testing**:
```python
# Manual test
enricher = ContextEnricher(
    app_name="test-app",
    environment="staging",
    version="1.0.0",
    datacenter="us-west-2"
)

log_entry = {"message": "Test", "level": "INFO"}
enriched = enricher.enrich(log_entry)

assert enriched["app_name"] == "test-app"
assert enriched["environment"] == "staging"
assert enriched["datacenter"] == "us-west-2"
```

---

#### Task 1.4: Extract Severity Routing from GhostGrid (0.5 hours)
**Source**: `D:\Users\Garza\Documents\GitHub\GhostGrid Optical Network\ghostgrid-sim\src\security\audit_logger.py`
**Target**: Integrated into `netrun_logging/logger.py`

**Reusable Components**:
```python
# From GhostGrid AuditLogger (lines 116-124)
# Log at appropriate severity level
if severity == "CRITICAL":
    self.logger.critical(log_message)
elif severity == "ERROR":
    self.logger.error(log_message)
elif severity == "WARNING":
    self.logger.warning(log_message)
else:
    self.logger.info(log_message)
```

**Adaptation Required**:
- Add DEBUG level support
- Create severity mapping enum

**Deliverable**:
```python
# Integrated into netrun_logging/logger.py
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

def log_at_level(logger: logging.Logger, level: LogLevel, message: str, **kwargs):
    """Route log message to appropriate severity level"""
    if level == LogLevel.CRITICAL:
        logger.critical(message, **kwargs)
    elif level == LogLevel.ERROR:
        logger.error(message, **kwargs)
    elif level == LogLevel.WARNING:
        logger.warning(message, **kwargs)
    elif level == LogLevel.DEBUG:
        logger.debug(message, **kwargs)
    else:
        logger.info(message, **kwargs)
```

---

## New Development Plan

### Phase 2: Build New Components (5 hours)

#### Task 2.1: Azure App Insights Integration (3 hours)
**Target**: `Service_61_Unified_Logging/netrun_logging/azure_insights.py`

**Dependencies**:
```toml
# pyproject.toml
dependencies = [
    "azure-monitor-opentelemetry>=1.0.0",
    "opencensus-ext-azure>=1.1.0",
]
```

**Implementation**:
```python
# netrun_logging/azure_insights.py
from typing import Optional
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

class AzureInsightsHandler:
    """
    Azure Application Insights integration handler

    Usage:
        handler = AzureInsightsHandler(
            connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
            service_name="netrun-crm"
        )
        logger.addHandler(handler.get_handler())
    """

    def __init__(
        self,
        connection_string: str,
        service_name: str,
        enable_sampling: bool = True,
        sampling_rate: float = 1.0
    ):
        self.connection_string = connection_string
        self.service_name = service_name
        self.enable_sampling = enable_sampling
        self.sampling_rate = sampling_rate
        self._handler = None

    def get_handler(self) -> logging.Handler:
        """Get configured Azure Log Handler"""
        if self._handler is None:
            self._handler = AzureLogHandler(
                connection_string=self.connection_string
            )
            # Add custom properties
            self._handler.add_telemetry_processor(
                self._add_custom_properties
            )
        return self._handler

    def _add_custom_properties(self, envelope):
        """Add custom properties to telemetry"""
        envelope.data.baseData.properties["service_name"] = self.service_name
        return True

# Global Azure handler
_azure_handler: Optional[AzureInsightsHandler] = None

def configure_azure_insights(
    connection_string: str,
    service_name: str,
    **kwargs
) -> AzureInsightsHandler:
    """Configure global Azure App Insights handler"""
    global _azure_handler
    _azure_handler = AzureInsightsHandler(
        connection_string=connection_string,
        service_name=service_name,
        **kwargs
    )
    return _azure_handler

def get_azure_handler() -> Optional[logging.Handler]:
    """Get global Azure handler if configured"""
    return _azure_handler.get_handler() if _azure_handler else None
```

**Testing**:
```python
# Manual test (requires Azure App Insights instance)
connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
handler = AzureInsightsHandler(
    connection_string=connection_string,
    service_name="test-app"
)

logger = logging.getLogger(__name__)
logger.addHandler(handler.get_handler())
logger.info("Test Azure log", custom_field="value")

# Check Azure portal for log entry (may take 2-3 minutes)
```

**Fallback (if Azure not available)**:
```python
# Mock handler for testing without Azure credentials
class MockAzureHandler(logging.Handler):
    def emit(self, record):
        print(f"[MOCK AZURE] {record.getMessage()}")
```

---

#### Task 2.2: Unified Logger API (2 hours)
**Target**: `Service_61_Unified_Logging/netrun_logging/logger.py`

**Implementation**:
```python
# netrun_logging/logger.py
import logging
from typing import Optional
from .json_formatter import JSONFormatter
from .correlation_id import CorrelationContext
from .context_enrichment import ContextEnricher, get_global_context
from .azure_insights import get_azure_handler

# Logger registry
_loggers = {}

def configure_logging(
    app_name: str,
    environment: Optional[str] = None,
    azure_insights_connection_string: Optional[str] = None,
    log_level: str = "INFO",
    **custom_context
):
    """
    Configure global logging for application

    Usage:
        configure_logging(
            app_name="netrun-crm",
            environment="production",
            azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
            log_level="INFO"
        )
    """
    # Set global context
    from .context_enrichment import set_global_context
    set_global_context(
        app_name=app_name,
        environment=environment or "development",
        **custom_context
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Add JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # Add Azure handler if configured
    if azure_insights_connection_string:
        from .azure_insights import configure_azure_insights
        azure_handler = configure_azure_insights(
            connection_string=azure_insights_connection_string,
            service_name=app_name
        )
        root_logger.addHandler(azure_handler.get_handler())

def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger with structured logging support

    Usage:
        logger = get_logger(__name__)
        logger.info("User logged in", user_id="123")
    """
    if name not in _loggers:
        logger = logging.getLogger(name)

        # Add filter to inject correlation ID
        class CorrelationIDFilter(logging.Filter):
            def filter(self, record):
                record.correlation_id = CorrelationContext.get()
                # Add global context
                for key, value in get_global_context().items():
                    setattr(record, key, value)
                return True

        logger.addFilter(CorrelationIDFilter())
        _loggers[name] = logger

    return _loggers[name]
```

**Testing**:
```python
# Manual test
configure_logging(
    app_name="test-app",
    environment="development",
    log_level="DEBUG"
)

logger = get_logger(__name__)

# Test basic logging
logger.info("Test message")

# Test structured logging
logger.info("User action", user_id="123", action="login", ip="192.168.1.1")

# Test correlation ID
correlation_id = CorrelationContext.generate_id()
with CorrelationContext(correlation_id):
    logger.info("Inside correlation context")

# Test exception logging
try:
    raise ValueError("Test exception")
except Exception as e:
    logger.error("Exception occurred", exc_info=True)
```

---

### Phase 3: Package Structure (1.5 hours)

#### Task 3.1: Create pyproject.toml (1 hour)
**Target**: `Service_61_Unified_Logging/pyproject.toml`

**Implementation**:
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "netrun-logging"
version = "1.0.0"
description = "Unified structured logging service with JSON formatting, correlation ID tracking, and Azure App Insights integration"
authors = [
    {name = "Daniel Garza", email = "daniel@netrunsystems.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.9"
keywords = ["logging", "structured-logging", "json", "azure", "correlation-id"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "azure-monitor-opentelemetry>=1.0.0",
    "opencensus-ext-azure>=1.1.0",
    "python-json-logger>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.5.0",
    "ruff>=0.1.0",
    "bandit>=1.7.5",
]

[project.urls]
Homepage = "https://netrunsystems.com"
Repository = "https://github.com/netrunsystems/netrun-logging"
Documentation = "https://netrun-logging.readthedocs.io"

[tool.setuptools.packages.find]
where = ["."]
include = ["netrun_logging*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "--cov=netrun_logging --cov-report=html --cov-report=term"

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]
```

---

#### Task 3.2: Create Package README (0.5 hours)
**Target**: `Service_61_Unified_Logging/README.md`

**Implementation**:
```markdown
# netrun-logging

Unified structured logging service with JSON formatting, correlation ID tracking, and Azure App Insights integration.

## Installation

```bash
pip install netrun-logging
```

## Quick Start

```python
from netrun_logging import configure_logging, get_logger
import os

# Configure logging
configure_logging(
    app_name="my-app",
    environment=os.getenv("ENVIRONMENT", "development"),
    azure_insights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    log_level="INFO"
)

# Get logger
logger = get_logger(__name__)

# Basic logging
logger.info("Application started")

# Structured logging
logger.info(
    "User logged in",
    user_id="12345",
    ip_address="192.168.1.1",
    login_method="oauth"
)

# Correlation ID tracking
from netrun_logging import CorrelationContext

correlation_id = CorrelationContext.generate_id()
with CorrelationContext(correlation_id):
    logger.info("Request started")
    # All logs in this context include correlation_id
```

## Features

- ✅ JSON-formatted structured logging
- ✅ Correlation ID tracking (thread-safe)
- ✅ Context enrichment (app metadata, environment variables)
- ✅ Azure Application Insights integration
- ✅ FastAPI middleware support
- ✅ Automatic exception formatting
- ✅ Type-safe API

## Documentation

Full documentation: https://netrun-logging.readthedocs.io

## License

MIT License - Copyright (c) 2025 Netrun Systems
```

---

### Phase 4: FastAPI Middleware Integration (1.5 hours)

#### Task 4.1: Create LoggingMiddleware (1.5 hours)
**Target**: `Service_61_Unified_Logging/netrun_logging/middleware.py`

**Implementation**:
```python
# netrun_logging/middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .correlation_id import CorrelationContext
from .logger import get_logger
import time

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic request/response logging

    Features:
    - Generates correlation ID for each request
    - Logs request start/end with timing
    - Logs response status code
    - Adds correlation ID to request state

    Usage:
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = CorrelationContext.generate_id()

        # Add to request state (for dependency injection)
        request.state.correlation_id = correlation_id

        # Log request start
        start_time = time.time()
        with CorrelationContext(correlation_id):
            logger.info(
                "Request started",
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            # Process request
            try:
                response = await call_next(request)

                # Log request end
                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    "Request completed",
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                )

                # Add correlation ID to response headers
                response.headers["X-Correlation-ID"] = correlation_id

                return response

            except Exception as e:
                # Log exception
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    "Request failed",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    duration_ms=round(duration_ms, 2),
                    exc_info=True
                )
                raise
```

**Testing**:
```python
# Manual test with FastAPI app
from fastapi import FastAPI, Depends
from netrun_logging import configure_logging, get_logger, LoggingMiddleware
from netrun_logging.correlation_id import CorrelationContext

configure_logging(app_name="test-api", log_level="DEBUG")
app = FastAPI()
app.add_middleware(LoggingMiddleware)

logger = get_logger(__name__)

@app.get("/test")
async def test_endpoint():
    logger.info("Inside endpoint handler")
    return {"message": "Success", "correlation_id": CorrelationContext.get()}

# Run: uvicorn test_app:app --reload
# Test: curl http://localhost:8000/test
# Check logs: Should see correlation_id in all log entries
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] JSON formatter implemented and tested
- [ ] Correlation ID tracking system implemented and tested
- [ ] Context enrichment layer implemented and tested
- [ ] Azure App Insights integration implemented and tested (or mocked)
- [ ] Unified Logger API implemented and tested
- [ ] FastAPI middleware implemented and tested
- [ ] Package structure created (pyproject.toml, setup.py, README.md)

### Quality Gates
- [ ] Manual testing with sample FastAPI app passes
- [ ] Azure App Insights connection successful (or mocked gracefully)
- [ ] JSON logs output correctly (valid JSON, all fields present)
- [ ] Correlation IDs propagate across log calls within context
- [ ] Context enrichment works (global context fields added to logs)
- [ ] Package installable locally: `pip install -e .`
- [ ] Can run: `from netrun_logging import get_logger; logger = get_logger(__name__)`

### Documentation Requirements
- [ ] Package README.md created with quick start guide
- [ ] All public functions have docstrings
- [ ] Usage examples documented

### Ready for Week 2 When
- [ ] All functional requirements met
- [ ] All quality gates passed
- [ ] Package installable and importable
- [ ] Manual testing demonstrates core functionality works

---

## Timeline

### Day 1: November 24, 2025 (6 hours)

**15:00-16:00 (1h)**: Task 1.1 - Extract JSON Formatter from GhostGrid
**16:00-17:00 (1h)**: Task 1.2 - Extract Correlation ID from Intirkast
**17:00-18:00 (1h)**: Task 1.3 - Extract Context Enrichment from GhostGrid
**18:00-18:30 (0.5h)**: Task 1.4 - Extract Severity Routing from GhostGrid

**Break**: 18:30-19:00

**19:00-22:00 (3h)**: Task 2.1 - Build Azure App Insights Integration

**End of Day 1**: 22:00 (6 hours completed)

---

### Day 2: November 25, 2025 (5.5 hours)

**09:00-11:00 (2h)**: Task 2.2 - Build Unified Logger API
**11:00-12:00 (1h)**: Task 3.1 - Create pyproject.toml
**12:00-12:30 (0.5h)**: Task 3.2 - Create Package README

**Break**: 12:30-13:00

**13:00-14:30 (1.5h)**: Task 4.1 - Create LoggingMiddleware
**14:30-15:30 (1h)**: Manual Testing & Validation

**End of Day 2**: 15:30 (5.5 hours completed)

**TOTAL**: 11.5 hours

---

## Risk Mitigation

### Risk 1: Azure App Insights Complexity
**Mitigation**: Use `opencensus-ext-azure` (simpler than OpenTelemetry)
**Contingency**: Create mock handler, defer real Azure integration to Week 2

### Risk 2: Pattern Extraction Takes Longer
**Mitigation**: GhostGrid and Intirkast code already reviewed (reuse 90% as-is)
**Contingency**: Skip context enrichment, add in Week 2.5

### Risk 3: FastAPI Middleware Complexity
**Mitigation**: Intirkast already has similar pattern (dependencies.py)
**Contingency**: Create basic middleware, enhance in Week 2

---

## Success Metrics

### Code Reuse Metrics
- ✅ JSON Formatter: 80% reused from GhostGrid (1h vs 8h traditional)
- ✅ Correlation ID: 90% reused from Intirkast (1h vs 6h traditional)
- ✅ Context Enrichment: 70% reused from GhostGrid (1h vs 5h traditional)
- ⚠️ Azure Integration: 0% reused (3h vs 3h traditional)
- ⚠️ Unified API: 20% reused (2h vs 10h traditional)

**Total Time Savings**: 28 hours (traditional 32h vs agentic 11.5h + reuse)

### Business Impact
- **Week 2 Unblocked**: Can proceed with testing & documentation
- **PyPI Publication**: On track for Week 2 (Day 2)
- **Integration Rollout**: 11 projects can integrate Week 3-5

---

## Next Steps (After Recreation Complete)

1. **Update IMPLEMENTATION_BACKLOG.md**
   - Mark Week 1 as "RECREATED (11.5h actual vs 60h planned)"
   - Update Week 2 start date to November 26, 2025
   - Add note: "Week 1 code artifacts not found, recreated using pattern extraction"

2. **Commit Week 1 Code to Git**
   - Commit SHA required in IMPLEMENTATION_BACKLOG.md
   - Tag: `service-61-week-1-recreation`
   - Commit message: "Service #61 Week 1 Recreation: Extracted patterns from GhostGrid + Intirkast"

3. **Begin Week 2: Testing & Documentation**
   - Test suite development (5h)
   - API documentation (3h)
   - PyPI packaging (3h)
   - Integration templates (2h)

---

**Contact**: Daniel Garza, Netrun Systems
**Email**: daniel@netrunsystems.com
**Generated**: November 24, 2025 16:00 PST
**SDLC Compliance**: v2.2
**Correlation ID**: REUSE-20251124-160000-B8C3D1
