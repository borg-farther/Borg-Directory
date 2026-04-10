# Smithery.ai MCP Server Listing Guide for agent-borg

## Overview

This guide provides step-by-step instructions for listing **agent-borg** (a Python MCP server with 14 tools) on Smithery.ai and other MCP registries/directories.

**agent-borg Details:**
- **GitHub:** https://github.com/bensargotest-sys/guild-tools
- **PyPI:** https://pypi.org/project/agent-borg/
- **Tools:** 14 MCP tools for AI agent workflows

---

## Smithery.ai Listing Process

### Method 1: Web UI (Recommended)

1. **Go to the publishing page**
   - Visit https://smithery.ai/new
   - Log in with your account (or create one)

2. **Enter your server URL**
   - Enter your MCP server's public HTTPS URL
   - For hosted servers, this would be your deployed endpoint
   - For local development, you'd need a publicly accessible URL (consider ngrok for testing)

3. **Complete the publishing flow**
   - Smithery will scan your server automatically to extract metadata (tools, prompts, resources)
   - If authentication is required, you'll be prompted to authenticate

4. **Server requirements**
   - Streamable HTTP transport
   - OAuth support (if auth is required)
   - Server must return 401 (not 403) for unauthenticated requests when OAuth is used

### Method 2: CLI

```bash
# Install Smithery CLI
npm install -g @smithery/cli@latest

# Authenticate
smithery auth login

# Publish your MCP server
smithery mcp publish "https://your-server-url.com/mcp" -n @your-org/agent-borg

# With config schema (if needed)
smithery mcp publish "https://your-server-url.com/mcp" -n @your-org/agent-borg --config-schema '{"type":"object","properties":{"apiKey":{"type":"string"}}}'
```

### Method 3: Static Server Card (Fallback)

If automatic scanning fails (auth wall, required configuration, etc.), you can serve a static server card at `/.well-known/mcp/server-card.json` on your server:

```json
{
  "serverInfo": {
    "name": "agent-borg",
    "version": "2.4.0"
  },
  "authentication": {
    "required": false,
    "schemes": []
  },
  "tools": [
    {
      "name": "tool_name_1",
      "description": "Description of tool 1",
      "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    }
    // ... list all 14 tools
  ],
  "resources": [],
  "prompts": []
}
```

---

## Pre-Listing Checklist for agent-borg

### 1. Ensure MCP Protocol Compliance

agent-borg must implement the MCP protocol correctly:

- [ ] Implement Streamable HTTP transport
- [ ] Implement proper OAuth 2.0 flow (if auth required)
- [ ] Return 401 (not 403) for unauthenticated requests
- [ ] Serve MCP schema at the root endpoint

### 2. Prepare Server Metadata

Before listing, prepare:
- [ ] Server name: `agent-borg`
- [ ] Server version: `2.4.0` (or current version)
- [ ] Description: "Proven workflows for AI agents — execution-proven, safety-scanned, feedback-improving"
- [ ] Icon/logo for the server listing
- [ ] List of all 14 tools with descriptions and input schemas
- [ ] GitHub repository URL
- [ ] Documentation URL

### 3. Server URL Options

For agent-borg, you have these URL options:

**Option A: Deploy as a hosted service**
- Deploy agent-borg to a cloud provider (AWS, GCP, Azure, etc.)
- Use a public HTTPS URL like `https://api.yourdomain.com/mcp`

**Option B: Use Smithery Gateway**
- Smithery Gateway can proxy to your upstream server
- You bring your own hosting

**Option C: Static Server Card + Discovery**
- Serve the server-card.json at `/.well-known/mcp/server-card.json`
- This bypasses the need for a live server scan

---

## Troubleshooting

### 403 Forbidden During Scan

If Smithery fails to scan your server with 403 errors:

1. **Check Cloudflare/WAF settings**
   - Smithery sends requests with User-Agent: `SmitheryBot/1.0 (+https://smithery.ai)`
   - These requests originate from Cloudflare Workers
   - Add an allow rule for `SmitheryBot` user agent

2. **For Cloudflare Bot Fight Mode (Free)**
   - Option 1: Add IP Access Rule for Smithery's IP range
   - Option 2: Disable Bot Fight Mode
   - Option 3: Upgrade to Pro plan

3. **For Cloudflare Pro+ with Super Bot Fight Mode**
   - Create WAF custom rule:
     - Expression: `(http.user_agent contains "SmitheryBot")`
     - Action: Skip > Super Bot Fight Mode

### Common Issues

| Issue | Solution |
|-------|----------|
| Server not responding | Ensure your server is running and publicly accessible |
| Auth failures | Verify OAuth implementation returns 401, not 403 |
| Tools not detected | Add static server-card.json or check MCP protocol compliance |
| CORS errors | Ensure your server allows cross-origin requests |

---

## Other MCP Registries & Directories

### 1. MCP Official Registry (modelcontextprotocol.io)

The official MCP project maintains a registry of servers:
- **GitHub:** https://github.com/modelcontextprotocol/awesome
- **Process:** Submit a PR to add your server to the awesome list
- **Format:** Add your server to the README with name, description, and link

### 2. OpenAI Agents SDK Directory

The OpenAI Agents SDK may have its own MCP server listing:
- Check https://platform.openai.com/docs/agents-sdk/mcp-servers

### 3. Composio

Composio maintains an MCP server directory:
- **URL:** https://composio.dev
- **Process:** Similar submission process for MCP servers

### 4. GitHub Topics

Add relevant GitHub topics to your repository:
- `mcp-server`
- `model-context-protocol`
- `mcp`
- `ai-agents`

### 5. NPM Registry (for JS/TS servers)

If agent-borg has a JS/TS wrapper, publish to npm:
- `npm publish`
- Add keywords: `mcp`, `mcp-server`, `model-context-protocol`

---

## agent-borg Specific Considerations

### Current Architecture

agent-borg is a Python package installed via pip:
- **Package:** `agent-borg`
- **Installation:** `pip install agent-borg`
- **Structure:** Python-based MCP server

### Options for Smithery Listing

Since agent-borg is a Python package, you have these options:

**Option 1: Create a hosted wrapper service**
1. Create a small HTTP wrapper that runs agent-borg
2. Deploy it (e.g., as a FastAPI service on a cloud provider)
3. Submit the public URL to Smithery

**Option 2: Create an npm package wrapper**
1. Create a Node.js wrapper that invokes the Python package
2. Publish to npm as `@smitheryai/agent-borg` or similar
3. Submit to Smithery via CLI or web UI

**Option 3: Direct Python hosting**
1. Many platforms support direct Python deployment (Railway, Render, Fly.io, etc.)
2. Expose agent-borg via HTTP using a framework like FastAPI
3. Submit the URL to Smithery

### Recommended Approach

1. **Short term:** Create a FastAPI wrapper for agent-borg and deploy to Railway/Render
2. **Submit URL:** `https://your-app.railway.app/mcp` to Smithery
3. **Alternative:** Submit to Smithery CLI with the same URL

---

## API Reference (for programmatic listing)

Smithery provides a REST API for server management:

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/servers` | List all servers |
| POST | `/api/v1/servers` | Create a new server |
| GET | `/api/v1/servers/{id}` | Get server details |
| PUT | `/api/v1/servers/{id}` | Update server |
| DELETE | `/api/v1/servers/{id}` | Delete server |

### Authentication

- Requires API key via `Authorization: Bearer <token>` header
- Create tokens at https://smithery.ai/settings

### Example: Create Server

```bash
curl -X POST https://smithery.ai/api/v1/servers \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "agent-borg",
    "url": "https://your-server.com/mcp",
    "description": "Proven workflows for AI agents"
  }'
```

---

## Quick Start Commands

```bash
# 1. Install Smithery CLI
npm install -g @smithery/cli@latest

# 2. Authenticate
smithery auth login

# 3. Test connection (when server is deployed)
smithery mcp add https://your-server.com/mcp --id agent-borg

# 4. List tools
smithery tool list agent-borg

# 5. Publish to registry
smithery mcp publish https://your-server.com/mcp -n @your-org/agent-borg
```

---

## Support & Resources

- **Smithery Docs:** https://smithery.ai/docs
- **Smithery Discord:** https://discord.gg/Afd38S5p9A
- **Smithery GitHub:** https://github.com/smithery-ai
- **MCP Specification:** https://modelcontextprotocol.io
- **agent-borg GitHub:** https://github.com/bensargotest-sys/guild-tools
- **agent-borg PyPI:** https://pypi.org/project/agent-borg/

---

## Next Steps

1. **Deploy agent-borg MCP server** with a public HTTPS URL
2. **Test locally** using Smithery CLI `smithery mcp add`
3. **Submit listing** via https://smithery.ai/new or CLI
4. **Monitor** server scans and fix any 403/troubleshooting issues
5. **Submit to other registries** (MCP awesome list, etc.)
