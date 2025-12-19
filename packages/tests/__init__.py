"""
Netrun Namespace Package Import Tests
======================================

Comprehensive test suite for validating namespace package structure
and import mechanisms for the Netrun Service Library.

Test Coverage:
- Namespace package discovery (PEP 420)
- Individual package import validation
- Backwards compatibility with old import style
- Cross-package dependency resolution
- Type checking compliance (PEP 561)
- Python version compatibility (3.10, 3.11, 3.12)
- Dynamic imports and lazy loading
- Error handling and edge cases

Usage:
    pytest test_namespace_imports.py -v
    pytest -m namespace
    pytest -m integration
    pytest --cov=. --cov-report=html

Author: Netrun Systems
Version: 1.0.0
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Netrun Systems"
__all__ = [
    "__version__",
    "__author__",
]
