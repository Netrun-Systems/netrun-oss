"""
Netrun Systems - Enterprise Python Toolkit

This is the namespace package foundation for all Netrun packages.
Install individual packages to add functionality:

    pip install netrun-auth      # Authentication (netrun.auth)
    pip install netrun-config    # Configuration (netrun.config)
    pip install netrun-errors    # Error handling (netrun.errors)
    pip install netrun-logging   # Structured logging (netrun.logging)
    pip install netrun-db-pool   # Database pooling (netrun.db)
    pip install netrun-llm       # LLM integration (netrun.llm)
    pip install netrun-rbac      # RBAC with PostgreSQL RLS (netrun.rbac)

Example usage:
    from netrun.auth import JWTAuthMiddleware
    from netrun.config import Settings
    from netrun.errors import NetrunError
"""

__version__ = "1.0.0"
__author__ = "Netrun Systems"
__email__ = "dev@netrunsystems.com"

# Namespace package marker - allows subpackages from other distributions
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
