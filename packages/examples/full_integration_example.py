#!/usr/bin/env python3
"""
Netrun Service Library - Full Integration Example

This example demonstrates how all Netrun packages work together
in a production FastAPI application.

Requirements:
    pip install netrun-logging netrun-errors netrun-auth[all] netrun-config[all]
    pip install netrun-cors netrun-db-pool netrun-llm netrun-env
    pip install fastapi uvicorn

Run:
    uvicorn full_integration_example:app --reload
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import BaseModel

# ============================================================================
# 1. LOGGING CONFIGURATION (Always first)
# ============================================================================
from netrun_logging import configure_logging, get_logger
from netrun_logging.middleware import CorrelationMiddleware
from netrun_logging.ecosystem import (
    bind_request_context,
    log_operation_timing,
    log_timing,
    create_audit_logger,
)

configure_logging(
    service_name="netrun-demo-api",
    environment="development",
    log_level="DEBUG",
    json_format=True,
)

logger = get_logger(__name__)
audit_logger = create_audit_logger("demo-api")

# ============================================================================
# 2. ERROR HANDLING
# ============================================================================
from netrun_errors import (
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
)
from netrun_errors.handlers import register_exception_handlers

# ============================================================================
# 3. CONFIGURATION
# ============================================================================
from netrun_config import BaseSettings


class AppSettings(BaseSettings):
    """Application configuration with validation."""

    app_name: str = "Netrun Demo API"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./demo.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "demo-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    class Config:
        env_prefix = "DEMO_"


settings = AppSettings()
logger.info("configuration_loaded", app_name=settings.app_name, debug=settings.debug)

# ============================================================================
# 4. AUTHENTICATION
# ============================================================================
from netrun_auth import JWTManager
from netrun_auth.models import TokenPayload

jwt_manager = JWTManager(
    secret_key=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    expiry_minutes=settings.jwt_expiry_minutes,
)

# ============================================================================
# 5. CORS CONFIGURATION
# ============================================================================
from netrun_cors import create_cors_middleware

cors_middleware = create_cors_middleware(
    allow_origins=["http://localhost:3000", "https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)

# ============================================================================
# 6. DATABASE POOL (Optional - requires PostgreSQL)
# ============================================================================
# from netrun_db_pool import DatabasePool, PoolConfig
#
# pool_config = PoolConfig(
#     database_url=settings.database_url,
#     pool_size=10,
#     max_overflow=5,
# )
# db_pool = DatabasePool(pool_config)


# ============================================================================
# APPLICATION SETUP
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("application_starting", app_name=settings.app_name)
    # await db_pool.initialize()  # Uncomment if using database
    yield
    logger.info("application_shutting_down")
    # await db_pool.close()  # Uncomment if using database


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# Add middlewares in order
app.add_middleware(CorrelationMiddleware)
app.add_middleware(cors_middleware.__class__, **cors_middleware.__dict__)

# Register exception handlers
register_exception_handlers(app)


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================
async def get_current_user(request: Request) -> Optional[TokenPayload]:
    """Extract and validate JWT from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    if not auth_header.startswith("Bearer "):
        raise AuthenticationError(
            message="Invalid authorization header format",
            error_code="AUTH_001",
        )

    token = auth_header[7:]
    try:
        payload = jwt_manager.decode_token(token)
        bind_request_context(
            method=request.method,
            path=str(request.url.path),
            user_id=payload.sub,
        )
        return payload
    except Exception as e:
        logger.warning("token_validation_failed", error=str(e))
        raise AuthenticationError(
            message="Invalid or expired token",
            error_code="AUTH_002",
        )


def require_auth(user: Optional[TokenPayload] = Depends(get_current_user)) -> TokenPayload:
    """Require authenticated user."""
    if user is None:
        raise AuthenticationError(
            message="Authentication required",
            error_code="AUTH_003",
        )
    return user


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    user_id: str
    username: str
    roles: list[str]


class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str


# ============================================================================
# API ENDPOINTS
# ============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("health_check_called")
    return {"status": "healthy", "service": settings.app_name}


@app.post("/auth/login", response_model=LoginResponse)
@log_timing(operation="user_login", level="info")
async def login(request: LoginRequest):
    """Authenticate user and return JWT."""
    # In production, validate against database
    if request.username != "demo" or request.password != "password":
        audit_logger.warning(
            "login_failed",
            username=request.username,
            reason="invalid_credentials",
        )
        raise AuthenticationError(
            message="Invalid username or password",
            error_code="AUTH_004",
        )

    # Generate JWT
    token = jwt_manager.create_token(
        sub=request.username,
        roles=["user", "admin"],
        custom_claims={"email": f"{request.username}@example.com"},
    )

    audit_logger.info("login_successful", username=request.username)

    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expiry_minutes * 60,
    )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(user: TokenPayload = Depends(require_auth)):
    """Get current authenticated user info."""
    logger.info("user_info_requested", user_id=user.sub)
    return UserResponse(
        user_id=user.sub,
        username=user.sub,
        roles=user.roles or [],
    )


@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(
    item: ItemCreate,
    user: TokenPayload = Depends(require_auth),
):
    """Create a new item."""
    with log_operation_timing("create_item", resource_type="item"):
        # Validation example
        if len(item.name) < 3:
            raise ValidationError(
                message="Item name must be at least 3 characters",
                field="name",
                error_code="VALIDATION_001",
            )

        # In production, save to database
        item_id = "item-123"

        audit_logger.info(
            "item_created",
            item_id=item_id,
            item_name=item.name,
            owner_id=user.sub,
        )

        return ItemResponse(
            id=item_id,
            name=item.name,
            description=item.description,
            owner_id=user.sub,
        )


@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    user: TokenPayload = Depends(require_auth),
):
    """Get item by ID."""
    logger.info("item_requested", item_id=item_id, user_id=user.sub)

    # In production, fetch from database
    if item_id != "item-123":
        raise NotFoundError(
            message=f"Item {item_id} not found",
            resource_type="item",
            resource_id=item_id,
            error_code="ITEM_001",
        )

    return ItemResponse(
        id=item_id,
        name="Demo Item",
        description="A demonstration item",
        owner_id="demo",
    )


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    user: TokenPayload = Depends(require_auth),
):
    """Delete item by ID."""
    # Check authorization
    if "admin" not in (user.roles or []):
        raise AuthorizationError(
            message="Admin role required to delete items",
            required_permission="admin",
            error_code="AUTHZ_001",
        )

    # In production, delete from database
    audit_logger.info(
        "item_deleted",
        item_id=item_id,
        deleted_by=user.sub,
    )

    return None


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "full_integration_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
