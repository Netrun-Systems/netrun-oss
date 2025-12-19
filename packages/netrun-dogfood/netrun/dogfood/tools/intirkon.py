"""
Intirkon tools for Netrun Dogfood MCP Server.

Provides 13 tools for Azure multi-tenant management:
- READ: list_tenants, get_tenant, get_costs, get_resources, get_health,
        get_alerts, get_advisor, get_compliance, health
- CREATE: create_alert, run_action
- UPDATE: update_alert
- DELETE: delete_alert

Author: Netrun Systems
Version: 1.0.0
"""

import json
from typing import Any, List
import httpx

from mcp.types import Tool, TextContent

from netrun_dogfood.config import get_config
from netrun_dogfood.auth import DogfoodAuth


def get_tools() -> List[Tool]:
    """Return all Intirkon tools."""
    return [
        # READ operations
        Tool(
            name="intirkon_list_tenants",
            description="List all managed Azure tenants in Intirkon",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status (active, inactive, all)",
                        "enum": ["active", "inactive", "all"],
                        "default": "active"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="intirkon_get_tenant",
            description="Get details for a specific Azure tenant",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID"
                    }
                },
                "required": ["tenant_id"]
            }
        ),
        Tool(
            name="intirkon_get_costs",
            description="Query Azure cost data for a tenant or all tenants",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID (optional, omit for all tenants)"
                    },
                    "period": {
                        "type": "string",
                        "description": "Cost period",
                        "enum": ["today", "week", "month", "quarter", "year"],
                        "default": "month"
                    },
                    "group_by": {
                        "type": "string",
                        "description": "Group costs by",
                        "enum": ["service", "resource_group", "subscription", "tag"],
                        "default": "service"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="intirkon_get_resources",
            description="Inventory Azure resources across tenants",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID (optional)"
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "Filter by resource type (e.g., Microsoft.Compute/virtualMachines)"
                    },
                    "resource_group": {
                        "type": "string",
                        "description": "Filter by resource group name"
                    },
                    "tags": {
                        "type": "object",
                        "description": "Filter by tags (key-value pairs)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="intirkon_get_health",
            description="Check resource health status across tenants",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID (optional)"
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by health status",
                        "enum": ["healthy", "degraded", "unhealthy", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="intirkon_get_alerts",
            description="Get cost and security alerts",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID (optional)"
                    },
                    "type": {
                        "type": "string",
                        "description": "Alert type filter",
                        "enum": ["cost", "security", "health", "all"],
                        "default": "all"
                    },
                    "severity": {
                        "type": "string",
                        "description": "Minimum severity",
                        "enum": ["critical", "high", "medium", "low"],
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="intirkon_get_advisor",
            description="Get Azure Advisor recommendations",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID (optional)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Recommendation category",
                        "enum": ["cost", "security", "reliability", "performance", "operational_excellence"],
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="intirkon_get_compliance",
            description="Get policy compliance status",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID (optional)"
                    },
                    "policy_name": {
                        "type": "string",
                        "description": "Filter by policy name"
                    }
                },
                "required": []
            }
        ),
        # CREATE operations
        Tool(
            name="intirkon_create_alert",
            description="Create a new alert rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Alert name"
                    },
                    "type": {
                        "type": "string",
                        "description": "Alert type",
                        "enum": ["cost", "security", "health"]
                    },
                    "severity": {
                        "type": "string",
                        "description": "Alert severity",
                        "enum": ["critical", "high", "medium", "low"]
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Alert threshold (for cost alerts)"
                    },
                    "condition": {
                        "type": "object",
                        "description": "Alert condition configuration"
                    }
                },
                "required": ["tenant_id", "name", "type", "severity"]
            }
        ),
        Tool(
            name="intirkon_run_action",
            description="Execute an Azure action (restart, scale, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Azure tenant ID"
                    },
                    "resource_id": {
                        "type": "string",
                        "description": "Full Azure resource ID"
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to execute",
                        "enum": ["restart", "start", "stop", "scale_up", "scale_down", "resize"]
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Action-specific parameters"
                    }
                },
                "required": ["tenant_id", "resource_id", "action"]
            }
        ),
        # UPDATE operations
        Tool(
            name="intirkon_update_alert",
            description="Modify an existing alert rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "alert_id": {
                        "type": "string",
                        "description": "Alert ID to update"
                    },
                    "name": {
                        "type": "string",
                        "description": "New alert name"
                    },
                    "severity": {
                        "type": "string",
                        "description": "New severity",
                        "enum": ["critical", "high", "medium", "low"]
                    },
                    "threshold": {
                        "type": "number",
                        "description": "New threshold value"
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable/disable alert"
                    }
                },
                "required": ["alert_id"]
            }
        ),
        # DELETE operations
        Tool(
            name="intirkon_delete_alert",
            description="Remove an alert rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "alert_id": {
                        "type": "string",
                        "description": "Alert ID to delete"
                    }
                },
                "required": ["alert_id"]
            }
        ),
        # Health check
        Tool(
            name="intirkon_health",
            description="Check Intirkon API health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


async def handle_tool(name: str, arguments: dict[str, Any], auth: DogfoodAuth) -> List[TextContent]:
    """Handle Intirkon tool calls."""
    config = get_config()
    base_url = config.intirkon_api_url

    try:
        headers = await auth.get_auth_headers("intirkon")

        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            # Route to appropriate endpoint
            if name == "intirkon_list_tenants":
                params = {"status": arguments.get("status", "active")}
                response = await client.get(f"{base_url}/tenants", headers=headers, params=params)

            elif name == "intirkon_get_tenant":
                tenant_id = arguments["tenant_id"]
                response = await client.get(f"{base_url}/tenants/{tenant_id}", headers=headers)

            elif name == "intirkon_get_costs":
                params = {
                    "period": arguments.get("period", "month"),
                    "group_by": arguments.get("group_by", "service"),
                }
                if "tenant_id" in arguments:
                    params["tenant_id"] = arguments["tenant_id"]
                response = await client.get(f"{base_url}/costs/summary", headers=headers, params=params)

            elif name == "intirkon_get_resources":
                params = {}
                for key in ["tenant_id", "resource_type", "resource_group"]:
                    if key in arguments:
                        params[key] = arguments[key]
                if "tags" in arguments:
                    params["tags"] = json.dumps(arguments["tags"])
                response = await client.get(f"{base_url}/resources", headers=headers, params=params)

            elif name == "intirkon_get_health":
                params = {"status": arguments.get("status", "all")}
                if "tenant_id" in arguments:
                    params["tenant_id"] = arguments["tenant_id"]
                response = await client.get(f"{base_url}/health/resources", headers=headers, params=params)

            elif name == "intirkon_get_alerts":
                params = {"type": arguments.get("type", "all")}
                for key in ["tenant_id", "severity"]:
                    if key in arguments:
                        params[key] = arguments[key]
                response = await client.get(f"{base_url}/alerts", headers=headers, params=params)

            elif name == "intirkon_get_advisor":
                params = {}
                for key in ["tenant_id", "category"]:
                    if key in arguments:
                        params[key] = arguments[key]
                response = await client.get(f"{base_url}/advisor", headers=headers, params=params)

            elif name == "intirkon_get_compliance":
                params = {}
                for key in ["tenant_id", "policy_name"]:
                    if key in arguments:
                        params[key] = arguments[key]
                response = await client.get(f"{base_url}/compliance", headers=headers, params=params)

            elif name == "intirkon_create_alert":
                response = await client.post(f"{base_url}/alerts", headers=headers, json=arguments)

            elif name == "intirkon_run_action":
                response = await client.post(f"{base_url}/actions", headers=headers, json=arguments)

            elif name == "intirkon_update_alert":
                alert_id = arguments.pop("alert_id")
                response = await client.patch(f"{base_url}/alerts/{alert_id}", headers=headers, json=arguments)

            elif name == "intirkon_delete_alert":
                alert_id = arguments["alert_id"]
                response = await client.delete(f"{base_url}/alerts/{alert_id}", headers=headers)

            elif name == "intirkon_health":
                response = await client.get(f"{base_url}/health", headers=headers)

            else:
                return [TextContent(type="text", text=f"Unknown Intirkon tool: {name}")]

            # Handle response
            if response.status_code >= 400:
                return [TextContent(
                    type="text",
                    text=f"Intirkon API error ({response.status_code}): {response.text}"
                )]

            return [TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2)
            )]

    except Exception as e:
        return [TextContent(type="text", text=f"Intirkon error: {str(e)}")]
