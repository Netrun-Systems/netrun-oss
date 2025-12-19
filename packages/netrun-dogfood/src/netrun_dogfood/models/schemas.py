"""
Pydantic schemas for Netrun Dogfood MCP Server responses.

Author: Netrun Systems
Version: 1.0.0
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Intirkon Schemas
class TenantInfo(BaseModel):
    """Azure tenant information from Intirkon."""
    tenant_id: str
    display_name: str
    domain: str
    status: str
    subscription_count: int = 0
    resource_count: int = 0


class CostReport(BaseModel):
    """Azure cost report from Intirkon."""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    total_cost: float
    currency: str = "USD"
    breakdown_by_service: Dict[str, float] = Field(default_factory=dict)
    breakdown_by_resource_group: Dict[str, float] = Field(default_factory=dict)


class ResourceInfo(BaseModel):
    """Azure resource information from Intirkon."""
    resource_id: str
    name: str
    type: str
    resource_group: str
    location: str
    status: str
    tags: Dict[str, str] = Field(default_factory=dict)


class AlertInfo(BaseModel):
    """Alert configuration from Intirkon."""
    alert_id: str
    name: str
    type: str  # cost, security, health
    severity: str  # critical, high, medium, low
    threshold: Optional[float] = None
    enabled: bool = True
    created_at: datetime
    last_triggered: Optional[datetime] = None


# Charlotte Schemas
class ChatMessage(BaseModel):
    """Chat message for Charlotte AI."""
    role: str  # user, assistant, system
    content: str
    model: Optional[str] = None
    timestamp: Optional[datetime] = None


class ModelInfo(BaseModel):
    """LLM model information from Charlotte."""
    model_id: str
    name: str
    provider: str
    context_window: int
    input_cost_per_1k: float
    output_cost_per_1k: float
    capabilities: List[str] = Field(default_factory=list)


# Meridian Schemas
class Publication(BaseModel):
    """Publication from Meridian."""
    publication_id: str
    title: str
    description: Optional[str] = None
    type: str  # flipbook, pdf, document
    status: str  # draft, published, archived
    page_count: int = 0
    view_count: int = 0
    created_at: datetime
    updated_at: datetime
    share_url: Optional[str] = None


# NetrunSite Schemas
class BlogPost(BaseModel):
    """Blog post from NetrunSite."""
    post_id: str
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    author: str
    status: str  # draft, published, archived
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    published_at: Optional[datetime] = None
    view_count: int = 0


# SecureVault Schemas
class Credential(BaseModel):
    """Credential from SecureVault."""
    credential_id: str
    name: str
    username: Optional[str] = None
    url: Optional[str] = None
    folder: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Note: password is never returned in responses for security


class Folder(BaseModel):
    """Credential folder from SecureVault."""
    folder_id: str
    name: str
    parent_id: Optional[str] = None
    credential_count: int = 0
