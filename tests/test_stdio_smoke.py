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


def _list_names(tmp_path, **extra_env):
    cmd = shlex.split(os.getenv("SMOKE_COMMAND", "")) or [sys.executable, str(SERVER)]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", str(tmp_path)), **extra_env}
    transport = StdioTransport(command=cmd[0], args=cmd[1:], env=env, cwd=str(tmp_path))  # no .env, no keys

    async def list_names():
        async with Client(transport) as client:
            return sorted(t.name for t in await client.list_tools())

    return asyncio.run(list_names())


def test_stdio_lists_all_tools(tmp_path):
    names = _list_names(tmp_path)
    assert len(names) == 21
    assert {"create_invoice", "list_clients", "create_expense"} <= set(names)


def test_stdio_read_only_lists_only_read_tools(tmp_path):
    # Under SMOKE_COMMAND (the wheel run by uvx) the dependencies are resolved fresh, as a user's
    # `uvx superfaktura-mcp` resolves them, not from uv.lock: the declared range must keep this working.
    names = _list_names(tmp_path, SUPERFAKTURA_READ_ONLY="1")
    assert len(names) == 9
    assert "list_invoices" in names and "create_invoice" not in names and "delete_invoice" not in names
