"""
Netrun Dogfood MCP Server - Main entry point.

Provides unified API access to all Netrun Systems products:
- Intirkon (13 tools) - Azure multi-tenant management
- Charlotte (12 tools) - AI orchestration and LLM mesh
- Meridian (10 tools) - Document publishing
- NetrunSite (8 tools) - Website and blog API
- SecureVault (10 tools) - Password management

Total: 53 MCP tools with full CRUD operations.

Author: Netrun Systems
Version: 1.0.0
Date: 2025-11-29
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from netrun_dogfood.config import get_config, DogfoodConfig
from netrun_dogfood.auth import get_auth, DogfoodAuth

# Import tool modules
from netrun_dogfood.tools import (
    intirkon,
    charlotte,
    meridian,
    netrunsite,
    securevault,
)

logger = logging.getLogger(__name__)

# MCP Server instance
app = Server("netrun-dogfood")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools from all Netrun products."""
    config = get_config()
    tools = []

    # Health check tool (always available)
    tools.append(Tool(
        name="dogfood_health",
        description="Check health status of all Netrun Systems products and authentication status",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ))

    # Add product-specific tools if enabled
    if config.intirkon_enabled:
        tools.extend(intirkon.get_tools())

    if config.charlotte_enabled:
        tools.extend(charlotte.get_tools())

    if config.meridian_enabled:
        tools.extend(meridian.get_tools())

    if config.netrunsite_enabled:
        tools.extend(netrunsite.get_tools())

    if config.securevault_enabled:
        tools.extend(securevault.get_tools())

    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route tool calls to appropriate product handlers."""
    config = get_config()
    auth = get_auth()

    # Health check
    if name == "dogfood_health":
        return await _health_check(config, auth)

    # Route to product handlers
    if name.startswith("intirkon_") and config.intirkon_enabled:
        return await intirkon.handle_tool(name, arguments, auth)

    if name.startswith("charlotte_") and config.charlotte_enabled:
        return await charlotte.handle_tool(name, arguments, auth)

    if name.startswith("meridian_") and config.meridian_enabled:
        return await meridian.handle_tool(name, arguments, auth)

    if name.startswith("netrunsite_") and config.netrunsite_enabled:
        return await netrunsite.handle_tool(name, arguments, auth)

    if name.startswith("securevault_") and config.securevault_enabled:
        return await securevault.handle_tool(name, arguments, auth)

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _health_check(config: DogfoodConfig, auth: DogfoodAuth) -> list[TextContent]:
    """Check health of all products and authentication."""
    import httpx

    results = {
        "authentication": {
            "configured": auth.is_configured,
            "tenant_id": config.azure_tenant_id[:8] + "..." if config.azure_tenant_id else "not set",
            "client_id": config.azure_client_id[:8] + "..." if config.azure_client_id else "not set",
        },
        "products": {},
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check each enabled product
        products = [
            ("intirkon", config.intirkon_enabled, config.intirkon_api_url),
            ("charlotte", config.charlotte_enabled, config.charlotte_api_url),
            ("meridian", config.meridian_enabled, config.meridian_api_url),
            ("netrunsite", config.netrunsite_enabled, config.netrunsite_api_url),
            ("securevault", config.securevault_enabled, config.securevault_api_url),
        ]

        for product_name, enabled, base_url in products:
            if not enabled:
                results["products"][product_name] = {"enabled": False}
                continue

            try:
                # Try health endpoint
                response = await client.get(f"{base_url}/health", timeout=5.0)
                results["products"][product_name] = {
                    "enabled": True,
                    "status": "healthy" if response.status_code == 200 else "degraded",
                    "status_code": response.status_code,
                    "url": base_url,
                }
            except Exception as e:
                results["products"][product_name] = {
                    "enabled": True,
                    "status": "unreachable",
                    "error": str(e),
                    "url": base_url,
                }

    import json
    return [TextContent(
        type="text",
        text=json.dumps(results, indent=2)
    )]


def main():
    """Run the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("Starting Netrun Dogfood MCP Server v1.0.0")
    logger.info("Products: Intirkon, Charlotte, Meridian, NetrunSite, SecureVault")
    logger.info("Total tools: 53 (Full CRUD)")

    async def run_server():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
