# Bidirectional MCP Setup: Claude Code <-> Codex CLI

This guide documents the bidirectional MCP (Model Context Protocol) configuration between Claude Code and OpenAI Codex CLI, enabling each tool to invoke the other as an MCP server.

## Overview

| Direction | Caller (Client) | Callee (Server) | Status |
|-----------|-----------------|-----------------|--------|
| Forward | Claude Code | Codex CLI | Configured |
| Reverse | Codex CLI | Claude Code | Configured |

### Why Bidirectional?

- **Claude Code -> Codex**: Delegate code implementation, reviews, and file modifications to Codex while Claude Code orchestrates
- **Codex -> Claude Code**: Leverage Claude's file editing, code analysis, and tool capabilities from within Codex sessions
- **Token optimization**: When one model's context is exhausted, hand off to the other

## Prerequisites

| Tool | Version | Path |
|------|---------|------|
| Claude Code | 2.1.50+ | `/Users/miyoungjang/.local/bin/claude` |
| Codex CLI | 0.104.0+ | `/opt/homebrew/bin/codex` |

```bash
# Verify installations
claude --version   # Expected: 2.x.x (Claude Code)
codex --version    # Expected: codex-cli 0.x.x
```

## Setup

### Direction 1: Claude Code -> Codex (Forward)

Claude Code calls Codex as an MCP server using `npx @openai/codex mcp-server`.

**Config file**: `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "codex": {
      "command": "npx",
      "args": ["-y", "@openai/codex", "mcp-server"]
    }
  }
}
```

**How to add (CLI)**:
```bash
claude mcp add codex -- npx -y @openai/codex mcp-server
```

**Verification**:
```bash
claude mcp list
# Should show: codex (stdio)
```

**Usage within Claude Code**:
Claude Code automatically discovers `mcp__codex__codex` and `mcp__codex__codex-reply` tools. Use them to delegate tasks:

```
# Start a Codex session
mcp__codex__codex(prompt="Fix the bug in auth.py", cwd="/path/to/project")

# Continue a conversation
mcp__codex__codex-reply(threadId="...", prompt="Also add tests")
```

### Direction 2: Codex -> Claude Code (Reverse)

Codex calls Claude Code as an MCP server using `claude mcp serve`.

**Config file**: `~/.codex/config.toml`

```toml
[mcp_servers.claude-code]
command = "/Users/miyoungjang/.local/bin/claude"
args = ["mcp", "serve"]
```

**How to add (CLI)**:
```bash
codex mcp add claude-code -- /Users/miyoungjang/.local/bin/claude mcp serve
```

> **Note**: Use the absolute path to `claude` binary. The `claude` command may not be in Codex's PATH during stdio server startup.

**Verification**:
```bash
codex mcp list
# Expected output:
# Name         Command                               Args       Status
# claude-code  /Users/miyoungjang/.local/bin/claude  mcp serve  enabled

codex mcp get claude-code
# Shows full details including transport: stdio
```

**Available tools from Claude Code MCP server**:

When Codex connects to Claude Code as an MCP server, it gets access to Claude's built-in tools:

| Tool | Description |
|------|-------------|
| `View` | Read files |
| `Edit` | Edit files with precise string replacement |
| `Write` | Create or overwrite files |
| `LS` | List directory contents |
| `Grep` | Search file contents with regex |
| `Glob` | Find files by pattern |
| `Bash` | Execute shell commands |

## Configuration Files Summary

### Claude Code (`~/.claude/settings.json`)

```json
{
  "mcpServers": {
    "codex": {
      "command": "npx",
      "args": ["-y", "@openai/codex", "mcp-server"]
    }
  }
}
```

### Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.claude-code]
command = "/Users/miyoungjang/.local/bin/claude"
args = ["mcp", "serve"]
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Developer Workflow                      │
│                                                          │
│  ┌─────────────┐   MCP (stdio)    ┌─────────────┐      │
│  │             │ ───────────────> │             │      │
│  │ Claude Code │                  │  Codex CLI  │      │
│  │  (Opus 4)   │ <─────────────── │ (GPT-5.3)   │      │
│  │             │   MCP (stdio)    │             │      │
│  └─────────────┘                  └─────────────┘      │
│        │                                │                │
│        │  Tools: Edit, Bash,            │  Tools: codex, │
│        │  Grep, Read, Write             │  codex-reply   │
│        │                                │                │
│        └────────────┬───────────────────┘                │
│                     │                                    │
│              Shared Workspace                            │
│           (quant-investment/)                            │
└──────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Claude Code MCP server not starting from Codex

**Symptom**: `codex mcp list` shows `claude-code` but tools are not available.

**Fix**: Ensure Claude Code has been run at least once with permissions accepted. The MCP serve mode is headless and cannot prompt for permissions interactively.

```bash
# Run once to accept permissions
claude --dangerously-skip-permissions
# Then Ctrl+C after it starts
```

### Codex MCP server not connecting from Claude Code

**Symptom**: `mcp__codex__codex` tool not available.

**Fix**: Ensure `npx` is available and `@openai/codex` can be downloaded.

```bash
npx -y @openai/codex --version
```

### PATH issues

**Symptom**: `spawn claude ENOENT` or similar.

**Fix**: Always use the absolute path in config files:

```bash
which claude    # /Users/miyoungjang/.local/bin/claude
which codex     # /opt/homebrew/bin/codex
```

### Timeout issues

For long-running tasks, increase the timeout:

**Codex side** (`config.toml`):
```toml
[mcp_servers.claude-code]
command = "/Users/miyoungjang/.local/bin/claude"
args = ["mcp", "serve"]
tool_timeout_sec = 120
startup_timeout_sec = 30
```

**Claude Code side**: Set `MCP_TIMEOUT` environment variable:
```bash
MCP_TIMEOUT=30000 claude  # 30 second startup timeout
```

## Related

- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp)
- [Codex MCP Configuration](https://developers.openai.com/codex/mcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
