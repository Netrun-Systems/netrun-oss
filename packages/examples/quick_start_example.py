#!/usr/bin/env python3
"""
Netrun Service Library - Quick Start Example

Demonstrates the core packages in a minimal FastAPI application.

Requirements:
    pip install netrun-logging netrun-errors netrun-auth netrun-cors
    pip install fastapi uvicorn

Run:
    uvicorn quick_start_example:app --reload

Test:
    curl http://localhost:8000/health
    curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"demo","password":"password"}'
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ============================================================================
# 1. LOGGING - Always configure first
# ============================================================================
from netrun_logging import configure_logging, get_logger

configure_logging(
    service_name="quick-start-api",
    environment="development",
    log_level="INFO",
)

logger = get_logger(__name__)

# ============================================================================
# 2. ERROR HANDLING
# ============================================================================
from netrun_errors import AuthenticationError, ValidationError
from netrun_errors.handlers import register_exception_handlers

# ============================================================================
# 3. AUTHENTICATION
# ============================================================================
from netrun_auth import JWTManager

jwt_manager = JWTManager(
    secret_key="demo-secret-change-in-production",
    algorithm="HS256",
    expiry_minutes=60,
)

# ============================================================================
# 4. CORS
# ============================================================================
from netrun_cors import create_cors_middleware

cors_middleware = create_cors_middleware(
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
)

# ============================================================================
# APPLICATION SETUP
# ============================================================================
app = FastAPI(title="Netrun Quick Start", version="1.0.0")

# Add middleware
app.add_middleware(cors_middleware.__class__, **cors_middleware.__dict__)

# Register exception handlers
register_exception_handlers(app)


# ============================================================================
# MODELS
# ============================================================================
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============================================================================
# ENDPOINTS
# ============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("health_check_called")
    return {"status": "healthy", "service": "quick-start-api"}


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate and return JWT token."""
    # Demo validation - replace with real auth
    if request.username != "demo" or request.password != "password":
        logger.warning("login_failed", username=request.username)
        raise AuthenticationError(
            message="Invalid credentials",
            error_code="AUTH_001",
        )

    # Generate token
    token = jwt_manager.create_token(
        sub=request.username,
        roles=["user"],
    )

    logger.info("login_successful", username=request.username)
    return LoginResponse(access_token=token)


@app.get("/protected")
async def protected_endpoint():
    """Example protected endpoint."""
    # In production, use dependency injection to validate JWT
    return {"message": "This would require authentication"}


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("quick_start_example:app", host="0.0.0.0", port=8000, reload=True)
