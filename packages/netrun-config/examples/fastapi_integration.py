"""
FastAPI integration example for netrun-config.

Demonstrates dependency injection and settings usage in FastAPI applications.
"""

from typing import Annotated

try:
    from fastapi import Depends, FastAPI
except ImportError:
    print("FastAPI not installed. Install with: pip install fastapi")
    exit(1)

from netrun_config import BaseConfig, Field, get_settings


class APISettings(BaseConfig):
    """FastAPI application settings."""

    # Override app name
    app_name: str = Field(default="Netrun API", env="APP_NAME")

    # API-specific settings
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")


# Create FastAPI app
app = FastAPI()

# Type alias for dependency injection
SettingsDep = Annotated[APISettings, Depends(get_settings)]


@app.get("/")
async def root(settings: SettingsDep):
    """Root endpoint demonstrating settings injection."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_environment,
        "api_prefix": settings.api_prefix,
    }


@app.get("/health")
async def health_check(settings: SettingsDep):
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.app_environment,
        "debug": settings.app_debug,
    }


@app.get("/config")
async def get_config(settings: SettingsDep):
    """Configuration endpoint (development only)."""
    if not settings.is_development:
        return {"error": "Config endpoint only available in development"}

    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_environment,
        "debug": settings.app_debug,
        "cors_origins": settings.cors_origins,
        "log_level": settings.log_level,
        "rate_limit": settings.rate_limit_per_minute,
    }


if __name__ == "__main__":
    # Run with: python fastapi_integration.py
    import uvicorn

    settings = get_settings(APISettings)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
