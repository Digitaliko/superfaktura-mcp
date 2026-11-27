"""Smoke: start the server over stdio as an MCP client would and list its tools.
No credentials are passed, so no tool can reach SuperFaktura.

SMOKE_COMMAND overrides how the server starts; CI sets it to the built wheel run by uvx."""

import asyncio
import os
import shlex
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

SERVER = Path(__file__).resolve().parent.parent / "server.py"


def _transport(tmp_path, **extra_env):
    cmd = shlex.split(os.getenv("SMOKE_COMMAND", "")) or [sys.executable, str(SERVER)]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", str(tmp_path)), **extra_env}
    return StdioTransport(command=cmd[0], args=cmd[1:], env=env, cwd=str(tmp_path))  # no .env, no keys


def _list_names(tmp_path, **extra_env):
    async def list_names():
        async with Client(_transport(tmp_path, **extra_env)) as client:
            return sorted(t.name for t in await client.list_tools())

    return asyncio.run(list_names())


def test_initialize_reports_the_package_version(tmp_path):
    # serverInfo.version is what an MCP client shows; it must be ours, not fastmcp's.
    async def server_info():
        async with Client(_transport(tmp_path)) as client:
            return client.initialize_result.serverInfo

    info = asyncio.run(server_info())
    project = tomllib.loads((SERVER.parent / "pyproject.toml").read_text())["project"]
    assert (info.name, info.version) == ("superfaktura", project["version"])


def test_stdio_lists_all_tools(tmp_path):
    names = _list_names(tmp_path)
    assert len(names) == 21
    assert {"create_invoice", "list_clients", "create_expense"} <= set(names)


def test_stdio_read_only_lists_only_read_tools(tmp_path):
    # Under SMOKE_COMMAND (the wheel run by uvx) the dependencies are resolved fresh, as a user's
    # `uvx superfaktura-mcp` resolves them, not from uv.lock: the declared range must keep this working.
    names = _list_names(tmp_path, SUPERFAKTURA_READ_ONLY="1")
    assert names == ["get_client", "get_expense", "get_invoice", "get_invoice_pdf", "list_clients",
                     "list_expense_categories", "list_expenses", "list_invoices", "list_tags"]
