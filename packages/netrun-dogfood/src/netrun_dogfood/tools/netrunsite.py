"""
NetrunSite tools for Netrun Dogfood MCP Server.

Provides 8 tools for website and blog API:
- READ: list_posts, get_post, get_analytics, health
- CREATE: create_post, submit_contact
- UPDATE: update_post
- DELETE: delete_post

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
    """Return all NetrunSite tools."""
    return [
        # READ operations
        Tool(
            name="netrunsite_list_posts",
            description="List blog posts from netrunsystems.com",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status",
                        "enum": ["draft", "published", "archived", "all"],
                        "default": "published"
                    },
                    "tag": {
                        "type": "string",
                        "description": "Filter by tag"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum posts to return",
                        "default": 20
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Pagination offset",
                        "default": 0
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="netrunsite_get_post",
            description="Get a specific blog post by ID or slug",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "string",
                        "description": "Post ID"
                    },
                    "slug": {
                        "type": "string",
                        "description": "Post slug (alternative to post_id)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="netrunsite_get_analytics",
            description="Get website and blog analytics",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Analytics period",
                        "enum": ["day", "week", "month", "year"],
                        "default": "month"
                    },
                    "metrics": {
                        "type": "array",
                        "description": "Metrics to include",
                        "items": {
                            "type": "string",
                            "enum": ["pageviews", "visitors", "bounce_rate", "avg_time"]
                        },
                        "default": ["pageviews", "visitors"]
                    }
                },
                "required": []
            }
        ),
        # CREATE operations
        Tool(
            name="netrunsite_create_post",
            description="Create a new blog post",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Post title"
                    },
                    "content": {
                        "type": "string",
                        "description": "Post content (markdown supported)"
                    },
                    "excerpt": {
                        "type": "string",
                        "description": "Post excerpt/summary"
                    },
                    "tags": {
                        "type": "array",
                        "description": "Post tags",
                        "items": {"type": "string"}
                    },
                    "status": {
                        "type": "string",
                        "description": "Post status",
                        "enum": ["draft", "published"],
                        "default": "draft"
                    },
                    "slug": {
                        "type": "string",
                        "description": "Custom URL slug (auto-generated if omitted)"
                    }
                },
                "required": ["title", "content"]
            }
        ),
        Tool(
            name="netrunsite_submit_contact",
            description="Submit a contact form entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Contact name"
                    },
                    "email": {
                        "type": "string",
                        "description": "Contact email"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company name"
                    },
                    "message": {
                        "type": "string",
                        "description": "Contact message"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject/topic",
                        "enum": ["general", "sales", "support", "partnership", "careers"]
                    }
                },
                "required": ["name", "email", "message"]
            }
        ),
        # UPDATE operations
        Tool(
            name="netrunsite_update_post",
            description="Update an existing blog post",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "string",
                        "description": "Post ID to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content"
                    },
                    "excerpt": {
                        "type": "string",
                        "description": "New excerpt"
                    },
                    "tags": {
                        "type": "array",
                        "description": "New tags",
                        "items": {"type": "string"}
                    },
                    "status": {
                        "type": "string",
                        "description": "New status",
                        "enum": ["draft", "published", "archived"]
                    }
                },
                "required": ["post_id"]
            }
        ),
        # DELETE operations
        Tool(
            name="netrunsite_delete_post",
            description="Delete a blog post",
            inputSchema={
                "type": "object",
                "properties": {
                    "post_id": {
                        "type": "string",
                        "description": "Post ID to delete"
                    }
                },
                "required": ["post_id"]
            }
        ),
        # Health check
        Tool(
            name="netrunsite_health",
            description="Check NetrunSite API health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


async def handle_tool(name: str, arguments: dict[str, Any], auth: DogfoodAuth) -> List[TextContent]:
    """Handle NetrunSite tool calls."""
    config = get_config()
    base_url = config.netrunsite_api_url

    try:
        headers = await auth.get_auth_headers("netrunsite")

        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            # Route to appropriate endpoint
            if name == "netrunsite_list_posts":
                params = {
                    "limit": arguments.get("limit", 20),
                    "offset": arguments.get("offset", 0),
                }
                if "status" in arguments and arguments["status"] != "all":
                    params["status"] = arguments["status"]
                if "tag" in arguments:
                    params["tag"] = arguments["tag"]
                response = await client.get(f"{base_url}/posts", headers=headers, params=params)

            elif name == "netrunsite_get_post":
                if "post_id" in arguments:
                    post_id = arguments["post_id"]
                    response = await client.get(f"{base_url}/posts/{post_id}", headers=headers)
                elif "slug" in arguments:
                    slug = arguments["slug"]
                    response = await client.get(f"{base_url}/posts/slug/{slug}", headers=headers)
                else:
                    return [TextContent(type="text", text="Either post_id or slug is required")]

            elif name == "netrunsite_get_analytics":
                params = {
                    "period": arguments.get("period", "month"),
                }
                if "metrics" in arguments:
                    params["metrics"] = ",".join(arguments["metrics"])
                response = await client.get(f"{base_url}/analytics", headers=headers, params=params)

            elif name == "netrunsite_create_post":
                payload = {
                    "title": arguments["title"],
                    "content": arguments["content"],
                    "status": arguments.get("status", "draft"),
                }
                for key in ["excerpt", "tags", "slug"]:
                    if key in arguments:
                        payload[key] = arguments[key]
                response = await client.post(f"{base_url}/posts", headers=headers, json=payload)

            elif name == "netrunsite_submit_contact":
                payload = {
                    "name": arguments["name"],
                    "email": arguments["email"],
                    "message": arguments["message"],
                }
                for key in ["company", "subject"]:
                    if key in arguments:
                        payload[key] = arguments[key]
                response = await client.post(f"{base_url}/contact", headers=headers, json=payload)

            elif name == "netrunsite_update_post":
                post_id = arguments.pop("post_id")
                response = await client.patch(f"{base_url}/posts/{post_id}", headers=headers, json=arguments)

            elif name == "netrunsite_delete_post":
                post_id = arguments["post_id"]
                response = await client.delete(f"{base_url}/posts/{post_id}", headers=headers)

            elif name == "netrunsite_health":
                response = await client.get(f"{base_url}/health", headers=headers)

            else:
                return [TextContent(type="text", text=f"Unknown NetrunSite tool: {name}")]

            # Handle response
            if response.status_code >= 400:
                return [TextContent(
                    type="text",
                    text=f"NetrunSite API error ({response.status_code}): {response.text}"
                )]

            return [TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2)
            )]

    except Exception as e:
        return [TextContent(type="text", text=f"NetrunSite error: {str(e)}")]
