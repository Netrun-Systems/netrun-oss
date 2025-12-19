"""
Charlotte tools for Netrun Dogfood MCP Server.

Provides 12 tools for AI orchestration and LLM mesh:
- READ: list_models, get_model, list_conversations, get_conversation,
        mesh_status, list_nodes, health
- CREATE: chat, reason, tts, stt
- DELETE: delete_conversation

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
    """Return all Charlotte tools."""
    return [
        # CREATE operations
        Tool(
            name="charlotte_chat",
            description="Send a message to an AI model via Charlotte",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model ID to use (e.g., gpt-4, claude-3, llama-3.1)",
                        "default": "gpt-4"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt"
                    },
                    "conversation_id": {
                        "type": "string",
                        "description": "Optional conversation ID to continue"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0-2)",
                        "default": 0.7
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response",
                        "default": 2048
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="charlotte_reason",
            description="Advanced reasoning request with chain-of-thought",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The reasoning query"
                    },
                    "model": {
                        "type": "string",
                        "description": "Model ID (prefer reasoning-optimized models)",
                        "default": "gpt-4-turbo"
                    },
                    "reasoning_type": {
                        "type": "string",
                        "description": "Type of reasoning",
                        "enum": ["analytical", "creative", "mathematical", "code", "general"],
                        "default": "general"
                    },
                    "depth": {
                        "type": "string",
                        "description": "Reasoning depth",
                        "enum": ["shallow", "medium", "deep"],
                        "default": "medium"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="charlotte_tts",
            description="Convert text to speech",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech"
                    },
                    "voice": {
                        "type": "string",
                        "description": "Voice to use",
                        "enum": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                        "default": "nova"
                    },
                    "speed": {
                        "type": "number",
                        "description": "Speech speed (0.25-4.0)",
                        "default": 1.0
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format",
                        "enum": ["mp3", "opus", "aac", "flac"],
                        "default": "mp3"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="charlotte_stt",
            description="Convert speech to text (transcription)",
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_url": {
                        "type": "string",
                        "description": "URL to audio file"
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code (e.g., en, es, fr)",
                        "default": "en"
                    },
                    "timestamps": {
                        "type": "boolean",
                        "description": "Include word timestamps",
                        "default": False
                    }
                },
                "required": ["audio_url"]
            }
        ),
        # READ operations
        Tool(
            name="charlotte_list_models",
            description="List available LLM models in Charlotte mesh",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "Filter by provider",
                        "enum": ["openai", "anthropic", "meta", "google", "local", "all"],
                        "default": "all"
                    },
                    "capability": {
                        "type": "string",
                        "description": "Filter by capability",
                        "enum": ["chat", "reasoning", "code", "vision", "audio"],
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="charlotte_get_model",
            description="Get details for a specific model",
            inputSchema={
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "string",
                        "description": "Model ID"
                    }
                },
                "required": ["model_id"]
            }
        ),
        Tool(
            name="charlotte_list_conversations",
            description="List chat conversation history",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum conversations to return",
                        "default": 20
                    },
                    "model": {
                        "type": "string",
                        "description": "Filter by model used"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="charlotte_get_conversation",
            description="Get full conversation history",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID"
                    }
                },
                "required": ["conversation_id"]
            }
        ),
        Tool(
            name="charlotte_mesh_status",
            description="Check Charlotte mesh network health and status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="charlotte_list_nodes",
            description="List nodes in the Charlotte mesh network",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by node status",
                        "enum": ["online", "offline", "degraded", "all"],
                        "default": "all"
                    }
                },
                "required": []
            }
        ),
        # DELETE operations
        Tool(
            name="charlotte_delete_conversation",
            description="Delete a conversation from history",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "Conversation ID to delete"
                    }
                },
                "required": ["conversation_id"]
            }
        ),
        # Health check
        Tool(
            name="charlotte_health",
            description="Check Charlotte API health status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


async def handle_tool(name: str, arguments: dict[str, Any], auth: DogfoodAuth) -> List[TextContent]:
    """Handle Charlotte tool calls."""
    config = get_config()
    base_url = config.charlotte_api_url

    try:
        headers = await auth.get_auth_headers("charlotte")

        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            # Route to appropriate endpoint
            if name == "charlotte_chat":
                payload = {
                    "message": arguments["message"],
                    "model": arguments.get("model", "gpt-4"),
                    "temperature": arguments.get("temperature", 0.7),
                    "max_tokens": arguments.get("max_tokens", 2048),
                }
                if "system_prompt" in arguments:
                    payload["system_prompt"] = arguments["system_prompt"]
                if "conversation_id" in arguments:
                    payload["conversation_id"] = arguments["conversation_id"]
                response = await client.post(f"{base_url}/chat", headers=headers, json=payload)

            elif name == "charlotte_reason":
                payload = {
                    "query": arguments["query"],
                    "model": arguments.get("model", "gpt-4-turbo"),
                    "reasoning_type": arguments.get("reasoning_type", "general"),
                    "depth": arguments.get("depth", "medium"),
                }
                response = await client.post(f"{base_url}/reason", headers=headers, json=payload)

            elif name == "charlotte_tts":
                payload = {
                    "text": arguments["text"],
                    "voice": arguments.get("voice", "nova"),
                    "speed": arguments.get("speed", 1.0),
                    "format": arguments.get("format", "mp3"),
                }
                response = await client.post(f"{base_url}/tts", headers=headers, json=payload)

            elif name == "charlotte_stt":
                payload = {
                    "audio_url": arguments["audio_url"],
                    "language": arguments.get("language", "en"),
                    "timestamps": arguments.get("timestamps", False),
                }
                response = await client.post(f"{base_url}/stt", headers=headers, json=payload)

            elif name == "charlotte_list_models":
                params = {}
                if "provider" in arguments and arguments["provider"] != "all":
                    params["provider"] = arguments["provider"]
                if "capability" in arguments:
                    params["capability"] = arguments["capability"]
                response = await client.get(f"{base_url}/models", headers=headers, params=params)

            elif name == "charlotte_get_model":
                model_id = arguments["model_id"]
                response = await client.get(f"{base_url}/models/{model_id}", headers=headers)

            elif name == "charlotte_list_conversations":
                params = {"limit": arguments.get("limit", 20)}
                if "model" in arguments:
                    params["model"] = arguments["model"]
                response = await client.get(f"{base_url}/conversations", headers=headers, params=params)

            elif name == "charlotte_get_conversation":
                conv_id = arguments["conversation_id"]
                response = await client.get(f"{base_url}/conversations/{conv_id}", headers=headers)

            elif name == "charlotte_mesh_status":
                response = await client.get(f"{base_url}/mesh/status", headers=headers)

            elif name == "charlotte_list_nodes":
                params = {"status": arguments.get("status", "all")}
                response = await client.get(f"{base_url}/mesh/nodes", headers=headers, params=params)

            elif name == "charlotte_delete_conversation":
                conv_id = arguments["conversation_id"]
                response = await client.delete(f"{base_url}/conversations/{conv_id}", headers=headers)

            elif name == "charlotte_health":
                response = await client.get(f"{base_url}/health", headers=headers)

            else:
                return [TextContent(type="text", text=f"Unknown Charlotte tool: {name}")]

            # Handle response
            if response.status_code >= 400:
                return [TextContent(
                    type="text",
                    text=f"Charlotte API error ({response.status_code}): {response.text}"
                )]

            return [TextContent(
                type="text",
                text=json.dumps(response.json(), indent=2)
            )]

    except Exception as e:
        return [TextContent(type="text", text=f"Charlotte error: {str(e)}")]
