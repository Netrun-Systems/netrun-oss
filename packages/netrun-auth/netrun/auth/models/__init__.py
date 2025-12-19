"""
Netrun Authentication - Model Configurations
=============================================

Casbin RBAC model configuration files.

Author: Netrun Systems
Version: 1.1.0
Date: 2025-12-03
"""

import os
from pathlib import Path

# Get model file paths
MODEL_DIR = Path(__file__).parent

RBAC_MODEL_PATH = str(MODEL_DIR / "rbac_model.conf")
RBAC_MODEL_TENANT_PATH = str(MODEL_DIR / "rbac_model_tenant.conf")

__all__ = [
    "RBAC_MODEL_PATH",
    "RBAC_MODEL_TENANT_PATH",
]
