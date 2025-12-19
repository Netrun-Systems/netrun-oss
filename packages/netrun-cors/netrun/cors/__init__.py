"""
netrun-cors: Enterprise CORS middleware presets for FastAPI applications.

Provides standardized CORS configurations for development, staging, production,
and OAuth-enabled environments.

v1.1.0: Added netrun-logging integration for structured CORS logging

Usage:
    from netrun_cors import CORSPreset

    app.add_middleware(CORSPreset.development())
    # or
    app.add_middleware(CORSPreset.production(origins=["https://app.example.com"]))
"""

__version__ = "2.1.0"
__author__ = "Netrun Systems"
__email__ = "support@netrunsystems.com"

from netrun.cors.presets import CORSPreset
from netrun.cors.config import CORSConfig
from netrun.cors.middleware import CORSMiddleware

__all__ = ["CORSPreset", "CORSConfig", "CORSMiddleware", "__version__"]
