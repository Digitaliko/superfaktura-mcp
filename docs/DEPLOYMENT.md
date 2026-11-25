# Deployment Guide

superfaktura-mcp 0.1.0 is a local **stdio** MCP server. It runs on your computer and uses one SuperFaktura account per server process, taken from environment variables.

There is no hosted or HTTP mode in 0.1.0. An HTTP server would act with the owner's account for anyone who can reach it, so `--http` is refused. Hosted use with per-user credentials needs authentication first; it is tracked in the issues.

---

## Install and run

You need [uv](https://docs.astral.sh/uv/) (macOS: `brew install uv`).

```bash
uvx superfaktura-mcp                      # from PyPI
# or from source
git clone https://github.com/Digitaliko/superfaktura-mcp.git
cd superfaktura-mcp && uv run server.py
```

The server reads a `.env` file next to it when started directly (`cp .env.example .env`). MCP clients normally pass the variables in their config instead.

---

## Claude Desktop

```json
{
  "mcpServers": {
    "superfaktura": {
      "command": "/opt/homebrew/bin/uvx",
      "args": ["superfaktura-mcp"],
      "env": {
        "SUPERFAKTURA_EMAIL": "your-email@example.com",
        "SUPERFAKTURA_API_KEY": "your-api-key-here",
        "SUPERFAKTURA_COUNTRY": "sk"
      }
    }
  }
}
```

Use the path that `which uvx` prints: Claude Desktop does not read your shell's PATH. Sandbox: `"SUPERFAKTURA_COUNTRY": "sandbox-sk"`.

## Claude Code

```bash
claude mcp add superfaktura -e SUPERFAKTURA_EMAIL=you@example.com -e SUPERFAKTURA_API_KEY=your-key -- uvx superfaktura-mcp
```

---

## Getting API Credentials

1. Log in to your SuperFaktura account
2. Navigate to **Tools** → **API**
3. Copy your API key
4. Use your login email as `SUPERFAKTURA_EMAIL`

For more details, see the [SuperFaktura API documentation](https://github.com/superfaktura/docs/blob/master/intro.md#authentication).

---

## Country Codes

| Code | Region | URL |
|------|--------|-----|
| `sk` | Slovakia | https://moja.superfaktura.sk |
| `cz` | Czech Republic | https://moje.superfaktura.cz |
| `at` | Austria | https://meine.superfaktura.at |
| `sandbox-sk` | Slovakia Sandbox | https://sandbox.superfaktura.sk |
| `sandbox-cz` | Czech Sandbox | https://sandbox.superfaktura.cz |

Codes are case-insensitive. Tested end to end on sandbox.superfaktura.sk. CZ and AT use the documented URLs and are not tested yet.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPERFAKTURA_EMAIL` | Yes | - | Account email |
| `SUPERFAKTURA_API_KEY` | Yes | - | API key from Tools → API |
| `SUPERFAKTURA_COUNTRY` | No | `sk` | Country code (table above) |
| `SUPERFAKTURA_COMPANY_ID` | No | - | Company ID, for accounts with several companies |
| `SUPERFAKTURA_API_URL` | No | - | Custom API URL (overrides the country) |
| `SUPERFAKTURA_READ_ONLY` | No | - | `1` exposes only the read tools (no create, edit, delete, send, pay) |

---

## Testing

```bash
uv run pytest -q                                        # mocked, no account needed
npx @modelcontextprotocol/inspector uv run server.py     # MCP Inspector
```

The sandbox suites (`tests/test_sandbox*.py`) run only with `SANDBOX_SUPERFAKTURA_EMAIL` and `SANDBOX_SUPERFAKTURA_API_KEY`, and only against https://sandbox.superfaktura.sk or .cz.

---

## Troubleshooting

- **Server won't start:** check that `uvx` (or `python3`) is on the path the client uses; in Claude Desktop use the full path.
- **Authentication errors:** check the email and API key in **Tools** → **API**, and that the country code matches your account.
- **Tools not appearing:** restart the client after changing its config; with `SUPERFAKTURA_READ_ONLY=1` only the 9 read tools appear.
