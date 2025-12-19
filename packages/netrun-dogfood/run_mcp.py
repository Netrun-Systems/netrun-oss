#!/usr/bin/env python
"""
MCP Server Runner with Environment Loading

This script loads environment variables from .env files before
starting the netrun-dogfood MCP server.

Environment files checked (in order):
1. .env.mcp in the current project directory
2. .env in the current project directory
3. ~/.meridian.env (user-level config)

Usage in .mcp.json:
{
  "mcpServers": {
    "netrun-dogfood": {
      "command": "python",
      "args": ["run_mcp.py"],
      "cwd": "/path/to/netrun-dogfood"
    }
  }
}
"""

import os
import sys
from pathlib import Path


def load_env_file(path: Path) -> int:
    """Load environment variables from a file. Returns count of vars loaded."""
    if not path.exists():
        return 0

    count = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                os.environ[key] = value
                count += 1
    return count


def main():
    # Get the directory where Claude Code invoked us from (PROJECT_DIR env var)
    # This is typically set by Claude Code to the project being worked on
    project_dir = os.environ.get('PROJECT_DIR', os.getcwd())

    # Also check common locations
    env_locations = [
        Path(project_dir) / '.env.mcp',
        Path(project_dir) / '.env',
        Path.home() / '.meridian.env',
        Path(__file__).parent / '.env',
    ]

    for env_path in env_locations:
        count = load_env_file(env_path)
        if count > 0:
            print(f"Loaded {count} env vars from {env_path}", file=sys.stderr)

    # Now run the actual MCP server
    from netrun_dogfood.server import main as server_main
    server_main()


if __name__ == '__main__':
    main()
