# Deployment Guide

This guide covers different deployment options for the SuperFaktura MCP server.

---

## Deployment Options

The server supports two authentication patterns:

1. **Local/Single-Tenant** - Uses environment variables
2. **Public MCP Server** - Uses custom headers from client configuration

Both patterns can work simultaneously with automatic fallback.

---

## Option 1: Local Development (Environment Variables)

Best for personal use and local development.

### Setup

1. Clone repository:
```bash
git clone https://github.com/digitaliko/superfaktura-mcp.git
cd superfaktura-mcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Edit `.env` with your credentials:
```env
SUPERFAKTURA_EMAIL=your-email@example.com
SUPERFAKTURA_API_KEY=your-api-key-here
SUPERFAKTURA_COUNTRY=sk
```

### Claude Desktop Configuration

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "superfaktura": {
      "command": "python3",
      "args": ["/absolute/path/to/superfaktura-mcp/server.py"],
      "env": {
        "SUPERFAKTURA_EMAIL": "your-email@example.com",
        "SUPERFAKTURA_API_KEY": "your-api-key-here",
        "SUPERFAKTURA_COUNTRY": "sk"
      }
    }
  }
}
```

**For sandbox environment:**
```json
{
  "mcpServers": {
    "superfaktura": {
      "command": "python3",
      "args": ["/absolute/path/to/superfaktura-mcp/server.py"],
      "env": {
        "SUPERFAKTURA_EMAIL": "your-email@example.com",
        "SUPERFAKTURA_API_KEY": "your-api-key-here",
        "SUPERFAKTURA_API_URL": "https://sandbox.superfaktura.sk"
      }
    }
  }
}
```

Restart Claude Desktop after configuration.

---

## Option 2: Public MCP Server (FastMCP Cloud)

Best for multi-tenant deployments where each user has their own credentials.

### Server Deployment

Deploy to FastMCP Cloud (or any other hosting platform):

1. **No environment variables needed** - The server accepts credentials via request headers

2. Deploy using your preferred method:
   - FastMCP Cloud
   - Vercel
   - AWS Lambda
   - Docker
   - Any Python hosting platform

### Client Configuration

Users configure their credentials in Claude Desktop config using custom headers:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "superfaktura": {
      "url": "https://your-mcp-server-url.com/mcp",
      "headers": {
        "X-SuperFaktura-Email": "user@example.com",
        "X-SuperFaktura-API-Key": "user-api-key",
        "X-SuperFaktura-Country": "sk",
        "X-SuperFaktura-Company-ID": "optional-company-id"
      }
    }
  }
}
```

**For sandbox:**
```json
{
  "mcpServers": {
    "superfaktura": {
      "url": "https://your-mcp-server-url.com/mcp",
      "headers": {
        "X-SuperFaktura-Email": "user@example.com",
        "X-SuperFaktura-API-Key": "user-api-key",
        "X-SuperFaktura-Country": "sandbox-sk"
      }
    }
  }
}
```

---

## Getting API Credentials

1. Log in to your SuperFaktura account
2. Navigate to **Tools** → **API**
3. Copy your API key
4. Use your login email as `SUPERFAKTURA_EMAIL`

**Recommended:** Create a dedicated API user with Administrator role in **Settings** → **Users**

For more details, refer to [SuperFaktura API documentation](https://github.com/superfaktura/docs/blob/master/intro.md#authentication).

---

## Country Codes

| Code | Region | URL |
|------|--------|-----|
| `sk` | Slovakia | https://moja.superfaktura.sk |
| `cz` | Czech Republic | https://moje.superfaktura.cz |
| `at` | Austria | https://meine.superfaktura.at |
| `sandbox-sk` | Slovakia Sandbox | https://sandbox.superfaktura.sk |
| `sandbox-cz` | Czech Sandbox | https://sandbox.superfaktura.cz |

**Custom API URL:**
For custom environments, set `SUPERFAKTURA_API_URL` (env var) or use custom country code mapping.

---

## Testing

### Run server directly:
```bash
python server.py
```

### Test with MCP Inspector:
```bash
npx @modelcontextprotocol/inspector python server.py
```

---

## Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY .env* ./

EXPOSE 8000

CMD ["python", "server.py"]
```

Build and run:
```bash
docker build -t superfaktura-mcp .
docker run -p 8000:8000 superfaktura-mcp
```

With environment variables:
```bash
docker run -p 8000:8000 \
  -e SUPERFAKTURA_EMAIL=your@email.com \
  -e SUPERFAKTURA_API_KEY=your-key \
  -e SUPERFAKTURA_COUNTRY=sk \
  superfaktura-mcp
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPERFAKTURA_EMAIL` | Yes* | - | Account email |
| `SUPERFAKTURA_API_KEY` | Yes* | - | API key from Tools → API |
| `SUPERFAKTURA_COUNTRY` | No | `sk` | Country code |
| `SUPERFAKTURA_COMPANY_ID` | No | - | Company ID (optional) |
| `SUPERFAKTURA_API_URL` | No | - | Custom API URL (overrides country) |

*Required unless using custom headers in public deployment

---

## Custom Headers Reference

For public MCP deployments, users can set these headers in Claude Desktop config:

| Header | Required | Description |
|--------|----------|-------------|
| `X-SuperFaktura-Email` | Yes* | Account email |
| `X-SuperFaktura-API-Key` | Yes* | API key |
| `X-SuperFaktura-Country` | No | Country code (default: `sk`) |
| `X-SuperFaktura-Company-ID` | No | Company ID (optional) |

*Required unless using environment variables

**Note:** Headers take precedence over environment variables.

---

## Troubleshooting

### Server won't start
- Check Python version (3.8+ required)
- Install dependencies: `pip install -r requirements.txt`
- Verify credentials are set (env vars or headers)

### Authentication errors
- Verify email and API key in SuperFaktura **Tools** → **API**
- Check country code matches your account
- For sandbox, use `sandbox-sk` or `sandbox-cz`

### Tools not appearing in Claude Desktop
- Restart Claude Desktop after config changes
- Check JSON syntax in config file
- Verify absolute path to server.py
- Check server logs for errors

### Public MCP deployment issues
- Ensure no environment variables are required in deployment
- Verify custom headers are properly configured in Claude Desktop
- Check that header names are lowercase in server code (`x-superfaktura-email`)
