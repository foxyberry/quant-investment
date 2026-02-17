# Google Stitch MCP Setup Guide

Setup guide for connecting Google Stitch MCP to Claude Code for AI-powered UI/UX design.

## Overview

Google Stitch is an AI tool that instantly generates UI/UX designs. Through MCP (Model Context Protocol), it integrates with Claude Code to automate the design-to-code workflow.

### Key Features
- AI-powered UI design generation
- Design system documentation
- React component code generation
- Figma/design file integration

## Prerequisites

| Requirement | Status | Notes |
|------------|--------|-------|
| Node.js v18+ | Required | For npx execution |
| Google Cloud CLI (gcloud) | Required | `~/google-cloud-sdk/bin/gcloud` |
| Google account login | Required | Google account with Cloud access |
| Google Cloud project | Required | Project with Stitch API enabled |
| Application Default Credentials | Required | `~/.config/gcloud/application_default_credentials.json` |

## Setup

### 1. `.mcp.json` Configuration

Add the stitch server to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "stitch": {
      "command": "npx",
      "args": ["-y", "@_davideast/stitch-mcp", "proxy"],
      "env": {
        "STITCH_PROJECT_ID": "your-google-cloud-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "~/.config/gcloud/application_default_credentials.json"
      }
    }
  }
}
```

### 2. Enable in Claude Code Settings

Add `"stitch"` to `enabledMcpjsonServers` in `.claude/settings.local.json`:

```json
{
  "enabledMcpjsonServers": ["stitch"]
}
```

### 3. Initialize stitch-mcp

```bash
npx -y @_davideast/stitch-mcp init
# → Select "Claude Code"
# → Select your Google Cloud project
```

### 4. Application Default Credentials (ADC)

```bash
gcloud auth application-default login
```

This will:
1. Open a browser window
2. Log in with your Google account
3. Authorize permissions
4. Create `~/.config/gcloud/application_default_credentials.json`

### 5. Restart Claude Code

After ADC setup, restart Claude Code. Verify with `/mcp` — `stitch` should appear in the server list.

## Diagnostics

```bash
npx -y @_davideast/stitch-mcp doctor
```

Expected output:
```
✔ Google Cloud CLI: Installed (bundled): v555.0.0
✔ User Authentication: Authenticated: <your-email>
✔ Application Credentials: Present
✔ Active Project: your-google-cloud-project-id
```

## Usage Examples

After connection, use in Claude Code:

```
# Generate UI design
"Design a login page UI"

# Generate components
"Convert this design to React components"

# Design system
"Create a design system for button components"
```

## Troubleshooting

### "Failed to reconnect to stitch"

Root causes (in order of likelihood):
1. **Active Project not set** — most common
2. `"stitch"` not in `enabledMcpjsonServers`
3. ADC credentials missing

Fix:
```bash
npx -y @_davideast/stitch-mcp init
# → Select Claude Code → Select project → Restart Claude Code
```

### ADC Authentication Failure

```bash
gcloud auth application-default revoke
gcloud auth application-default login
```

### gcloud Installation Paths

| Path | Purpose |
|------|---------|
| `~/google-cloud-sdk/bin/gcloud` | Primary gcloud (in PATH) |
| `~/.stitch-mcp/google-cloud-sdk/bin/gcloud` | stitch-mcp bundled version |

## References

- [@_davideast/stitch-mcp (npm)](https://www.npmjs.com/package/@_davideast/stitch-mcp)
- [Google Stitch](https://stitch.withgoogle.com/)
- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp)

## Changelog

| Date | Description |
|------|-------------|
| 2026-02-03 | Initial setup document |
| 2026-02-05 | Integration complete, switched to `@_davideast/stitch-mcp` |
| 2026-02-08 | Full document update to match actual setup |
| 2026-02-12 | Added to quant-investment project |
