"""
Meridian tools for Netrun Dogfood MCP Server.

Provides 10 tools for document publishing:
- READ: list_publications, get_publication, get_analytics, list_templates, health
- CREATE: upload_document, create_flipbook, share_publication
- UPDATE: update_publication
- DELETE: delete_publication

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
    """Return all Meridian tools."""
    return [
        # READ operations
        Tool(
            name="meridian_list_publications",
            description="List all publications in Meridian",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status",
                        "enum": ["draft", "published", "archived", "all"],
                        "default": "all"
                    },
                    "type": {
                        "type": "string",
                        "description": "Filter by publication type",
                        "enum": ["flipbook", "pdf", "document", "all"],
                        "default": "all"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 20
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="meridian_get_publication",
            description="Get details for a specific publication",
            inputSchema={
                "type": "object",
                "properties": {
                    "publication_id": {
                        "type": "string",
                        "description": "Publication ID"
                    }
                },
                "required": ["publication_id"]
            }
        ),
        Tool(
            name="meridian_get_analytics",
            description="Get view statistics for publications",
            inputSchema={
                "type": "object",
                "properties": {
                    "publication_id": {
                        "type": "string",
                        "description": "Publication ID (optional, omit for aggregate)"
                    },
                    "period": {
                        "type": "string",
                        "description": "Analytics period",
                        "enum": ["day", "week", "month", "year", "all"],
                        "default": "month"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="meridian_list_templates",
            description="List available publication templates",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Template category",
                        "enum": ["business", "marketing", "education", "portfolio", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        ),
        # CREATE operations
        Tool(
            name="meridian_upload_document",
            description="Upload a PDF or document to Meridian",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Publication title"
                    },
                    "file_url": {
                        "type": "string",
                        "description": "URL to the PDF/document file"
                    },
                    "description": {
                        "type": "string",
                        "description": "Publication description"
                    },
                    "auto_publish": {
                        "type": "boolean",
                        "description": "Automatically publish after upload",
                        "default": False
                    }
                },
                "required": ["title", "file_url"]
            }
        ),
        Tool(
            name="meridian_create_flipbook",
            description="Convert a document to interactive flipbook",
            inputSchema={
                "type": "object",
                "properties": {
                    "publication_id": {
                        "type": "string",
                        "description": "Source publication ID"
                    },
                    "template_id": {
                        "type": "string",
                        "description": "Template to use"
                    },
                    "settings": {
                        "type": "object",
                        "description": "Flipbook settings",
                        "properties": {
                            "page_flip_sound": {"type": "boolean", "default": True},
                            "show_thumbnails": {"type": "boolean", "default": True},
                            "enable_zoom": {"type": "boolean", "default": True},
                            "enable_fullscreen": {"type": "boolean", "default": True}
                        }
                    }
                },
                "required": ["publication_id"]
            }
        ),
        Tool(
            name="meridian_share_publication",
            description="Generate a share link for a publication",
            inputSchema={
                "type": "object",
                "properties": {
                    "publication_id": {
                        "type": "string",
                        "description": "Publication ID"
                    },
                    "expires_in_days": {
                        "type": "integer",
                        "description": "Link expiration in days (0 for permanent)",
                        "default": 0
                    },
                    "require_email": {
                        "type": "boolean",
                        "description": "Require email to view",
                        "default": False
                    },
                    "password": {
                        "type": "string",
                        "description": "Optional password protection"
                    }
                },
                "required": ["publication_id"]
            }
        ),
        # UPDATE operations
        Tool(
            name="meridian_update_publication",
            description="Update publication metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "publication_id": {
                        "type": "string",
                        "description": "Publication ID to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status",
                        "enum": ["draft", "published", "archived"]
                    }
                },
                "required": ["publication_id"]
            }
        ),
        # DELETE operations
        Tool(
            name="meridian_delete_publication",
            description="Delete a publication",
            inputSchema={
                "type": "object",
                "properties": {
                    "publication_id": {
                        "type": "string",
                        "description": "Publication ID to delete"
                    }
                },
                "required": ["publication_id"]
            }
        ),
        # Health check
        Tool(
            name="meridian_health",
            description="Check Meridian API health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


async def handle_tool(name: str, arguments: dict[str, Any], auth: DogfoodAuth) -> List[TextContent]:
    """Handle Meridian tool calls."""
    config = get_config()
    base_url = config.meridian_api_url

    try:
        headers = await auth.get_auth_headers("meridian")

        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            # Route to appropriate endpoint
            if name == "meridian_list_publications":
                params = {
                    "limit": arguments.get("limit", 20)
                }
                for key in ["status", "type"]:
                    if key in arguments and arguments[key] != "all":
                        params[key] = arguments[key]
                response = await client.get(f"{base_url}/publications", headers=headers, params=params)

            elif name == "meridian_get_publication":
                pub_id = arguments["publication_id"]
                response = await client.get(f"{base_url}/publications/{pub_id}", headers=headers)

            elif name == "meridian_get_analytics":
                params = {"period": arguments.get("period", "month")}
                if "publication_id" in arguments:
                    pub_id = arguments["publication_id"]
                    response = await client.get(f"{base_url}/publications/{pub_id}/analytics", headers=headers, params=params)
                else:
                    response = await client.get(f"{base_url}/analytics", headers=headers, params=params)

            elif name == "meridian_list_templates":
                params = {}
                if "category" in arguments and arguments["category"] != "all":
                    params["category"] = arguments["category"]
                response = await client.get(f"{base_url}/templates", headers=headers, params=params)

            elif name == "meridian_upload_document":
                payload = {
                    "title": arguments["title"],
                    "file_url": arguments["file_url"],
                    "auto_publish": arguments.get("auto_publish", False),
                }
                if "description" in arguments:
                    payload["description"] = arguments["description"]
                response = await client.post(f"{base_url}/publications", headers=headers, json=payload)

            elif name == "meridian_create_flipbook":
                pub_id = arguments["publication_id"]
                payload = {}
                if "template_id" in arguments:
                    payload["template_id"] = arguments["template_id"]
                if "settings" in arguments:
                    payload["settings"] = arguments["settings"]
                response = await client.post(f"{base_url}/publications/{pub_id}/flipbook", headers=headers, json=payload)

            elif name == "meridian_share_publication":
                pub_id = arguments["publication_id"]
                payload = {
                    "expires_in_days": arguments.get("expires_in_days", 0),
                    "require_email": arguments.get("require_email", False),
                }
                if "password" in arguments:
                    payload["password"] = arguments["password"]
                response = await client.post(f"{base_url}/publications/{pub_id}/share", headers=headers, json=payload)

            elif name == "meridian_update_publication":
                pub_id = arguments.pop("publication_id")
                response = await client.patch(f"{base_url}/publications/{pub_id}", headers=headers, json=arguments)

            elif name == "meridian_delete_publication":
                pub_id = arguments["publication_id"]
                response = await client.delete(f"{base_url}/publications/{pub_id}", headers=headers)

            elif name == "meridian_health":
                response = await client.get(f"{base_url}/health", headers=headers)

            else:
                return [TextContent(type="text", text=f"Unknown Meridian tool: {name}")]

            # Handle response
            if response.status_code >= 400:
                return [TextContent(
                    type="text",
                    text=f"Meridian API error ({response.status_code}): {response.text}"
                )]

            return [TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2)
            )]

    except Exception as e:
        return [TextContent(type="text", text=f"Meridian error: {str(e)}")]
