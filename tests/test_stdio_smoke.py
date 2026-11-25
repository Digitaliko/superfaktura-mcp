"""Smoke: start the server over stdio as an MCP client would and list its tools.
No credentials are passed, so no tool can reach SuperFaktura.

SMOKE_COMMAND overrides how the server starts; CI sets it to the built wheel run by uvx."""

import asyncio
import os
import shlex
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).resolve().parent.parent / "server.py"


def test_stdio_lists_all_tools(tmp_path):
    cmd = shlex.split(os.getenv("SMOKE_COMMAND", "")) or [sys.executable, str(SERVER)]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", str(tmp_path))}
    transport = StdioTransport(command=cmd[0], args=cmd[1:], env=env, cwd=str(tmp_path))  # no .env, no keys

    async def list_names():
        async with Client(transport) as client:
            return sorted(t.name for t in await client.list_tools())

    names = asyncio.run(list_names())
    assert len(names) == 19
    assert {"create_invoice", "list_clients", "create_expense"} <= set(names)
