"""Smoke: start the server over stdio as an MCP client would and list its tools.
No credentials are passed, so no tool can reach SuperFaktura."""

import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).resolve().parent.parent / "server.py"


def test_stdio_lists_all_tools(tmp_path):
    transport = StdioTransport(
        command=sys.executable, args=[str(SERVER)],
        env={"PATH": "/usr/bin:/bin"}, cwd=str(tmp_path),  # no .env, no keys
    )

    async def list_names():
        async with Client(transport) as client:
            return sorted(t.name for t in await client.list_tools())

    names = asyncio.run(list_names())
    assert len(names) == 19
    assert {"create_invoice", "list_clients", "create_expense"} <= set(names)
