"""
SecureVault tools for Netrun Dogfood MCP Server.

Provides 10 tools for password management:
- READ: list_credentials, get_credential, search, list_folders, health
- CREATE: create_credential, create_folder, generate_password
- UPDATE: update_credential
- DELETE: delete_credential

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
    """Return all SecureVault tools."""
    return [
        # READ operations
        Tool(
            name="securevault_list_credentials",
            description="List stored credentials (passwords hidden)",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Filter by folder ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 50
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="securevault_get_credential",
            description="Retrieve a specific credential (password included)",
            inputSchema={
                "type": "object",
                "properties": {
                    "credential_id": {
                        "type": "string",
                        "description": "Credential ID"
                    }
                },
                "required": ["credential_id"]
            }
        ),
        Tool(
            name="securevault_search",
            description="Search credentials by name, URL, or username",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "field": {
                        "type": "string",
                        "description": "Field to search",
                        "enum": ["all", "name", "url", "username"],
                        "default": "all"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="securevault_list_folders",
            description="List credential folders",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_id": {
                        "type": "string",
                        "description": "Parent folder ID (omit for root folders)"
                    }
                },
                "required": []
            }
        ),
        # CREATE operations
        Tool(
            name="securevault_create_credential",
            description="Store a new credential",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Credential name/title"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username/email"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password (or use generate=true)"
                    },
                    "url": {
                        "type": "string",
                        "description": "Associated URL"
                    },
                    "folder": {
                        "type": "string",
                        "description": "Folder ID to store in"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes"
                    },
                    "generate": {
                        "type": "boolean",
                        "description": "Auto-generate a secure password",
                        "default": False
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="securevault_create_folder",
            description="Create a credential folder",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Folder name"
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "Parent folder ID (omit for root)"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="securevault_generate_password",
            description="Generate a secure random password",
            inputSchema={
                "type": "object",
                "properties": {
                    "length": {
                        "type": "integer",
                        "description": "Password length",
                        "default": 24,
                        "minimum": 8,
                        "maximum": 128
                    },
                    "uppercase": {
                        "type": "boolean",
                        "description": "Include uppercase letters",
                        "default": True
                    },
                    "lowercase": {
                        "type": "boolean",
                        "description": "Include lowercase letters",
                        "default": True
                    },
                    "numbers": {
                        "type": "boolean",
                        "description": "Include numbers",
                        "default": True
                    },
                    "symbols": {
                        "type": "boolean",
                        "description": "Include symbols",
                        "default": True
                    },
                    "exclude_ambiguous": {
                        "type": "boolean",
                        "description": "Exclude ambiguous characters (0, O, l, 1)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        # UPDATE operations
        Tool(
            name="securevault_update_credential",
            description="Modify an existing credential",
            inputSchema={
                "type": "object",
                "properties": {
                    "credential_id": {
                        "type": "string",
                        "description": "Credential ID to update"
                    },
                    "name": {
                        "type": "string",
                        "description": "New name"
                    },
                    "username": {
                        "type": "string",
                        "description": "New username"
                    },
                    "password": {
                        "type": "string",
                        "description": "New password"
                    },
                    "url": {
                        "type": "string",
                        "description": "New URL"
                    },
                    "folder": {
                        "type": "string",
                        "description": "Move to folder ID"
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes"
                    }
                },
                "required": ["credential_id"]
            }
        ),
        # DELETE operations
        Tool(
            name="securevault_delete_credential",
            description="Remove a credential from the vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "credential_id": {
                        "type": "string",
                        "description": "Credential ID to delete"
                    }
                },
                "required": ["credential_id"]
            }
        ),
        # Health check
        Tool(
            name="securevault_health",
            description="Check SecureVault daemon health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


async def handle_tool(name: str, arguments: dict[str, Any], auth: DogfoodAuth) -> List[TextContent]:
    """Handle SecureVault tool calls."""
    config = get_config()
    base_url = config.securevault_api_url

    try:
        headers = await auth.get_auth_headers("securevault")

        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            # Route to appropriate endpoint
            if name == "securevault_list_credentials":
                params = {"limit": arguments.get("limit", 50)}
                if "folder" in arguments:
                    params["folder"] = arguments["folder"]
                response = await client.get(f"{base_url}/credentials", headers=headers, params=params)

            elif name == "securevault_get_credential":
                cred_id = arguments["credential_id"]
                response = await client.get(f"{base_url}/credentials/{cred_id}", headers=headers)

            elif name == "securevault_search":
                params = {
                    "query": arguments["query"],
                    "field": arguments.get("field", "all"),
                }
                response = await client.get(f"{base_url}/credentials/search", headers=headers, params=params)

            elif name == "securevault_list_folders":
                params = {}
                if "parent_id" in arguments:
                    params["parent_id"] = arguments["parent_id"]
                response = await client.get(f"{base_url}/folders", headers=headers, params=params)

            elif name == "securevault_create_credential":
                payload = {"name": arguments["name"]}
                for key in ["username", "password", "url", "folder", "notes", "generate"]:
                    if key in arguments:
                        payload[key] = arguments[key]
                response = await client.post(f"{base_url}/credentials", headers=headers, json=payload)

            elif name == "securevault_create_folder":
                payload = {"name": arguments["name"]}
                if "parent_id" in arguments:
                    payload["parent_id"] = arguments["parent_id"]
                response = await client.post(f"{base_url}/folders", headers=headers, json=payload)

            elif name == "securevault_generate_password":
                payload = {
                    "length": arguments.get("length", 24),
                    "uppercase": arguments.get("uppercase", True),
                    "lowercase": arguments.get("lowercase", True),
                    "numbers": arguments.get("numbers", True),
                    "symbols": arguments.get("symbols", True),
                    "exclude_ambiguous": arguments.get("exclude_ambiguous", True),
                }
                response = await client.post(f"{base_url}/generate", headers=headers, json=payload)

            elif name == "securevault_update_credential":
                cred_id = arguments.pop("credential_id")
                response = await client.patch(f"{base_url}/credentials/{cred_id}", headers=headers, json=arguments)

            elif name == "securevault_delete_credential":
                cred_id = arguments["credential_id"]
                response = await client.delete(f"{base_url}/credentials/{cred_id}", headers=headers)

            elif name == "securevault_health":
                response = await client.get(f"{base_url}/health", headers=headers)

            else:
                return [TextContent(type="text", text=f"Unknown SecureVault tool: {name}")]

            # Handle response
            if response.status_code >= 400:
                return [TextContent(
                    type="text",
                    text=f"SecureVault API error ({response.status_code}): {response.text}"
                )]

            return [TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2)
            )]

    except Exception as e:
        return [TextContent(type="text", text=f"SecureVault error: {str(e)}")]
