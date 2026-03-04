# Agentation Setup Guide

Visual feedback tool for AI agents. Click elements on the page to capture CSS selectors, React component hierarchy, and position info — then pass structured output to coding agents.

- **GitHub**: https://github.com/benjitaylor/agentation
- **Docs**: https://agentation.dev/faq
- **npm**: https://www.npmjs.com/package/agentation

## Requirements

- React 18+
- Desktop browser (mobile not supported)
- Node.js (for MCP server)

## Setup (3 steps)

### 1. Install package

```bash
cd web
npm install agentation -D
```

### 2. Add React component

Create `web/src/components/dev/AgentationProvider.tsx`:

```tsx
'use client';

import dynamic from 'next/dynamic';

const AgentationLazy = dynamic(
  () => import('agentation').then((m) => ({ default: m.Agentation })),
  { ssr: false },
);

export default function AgentationProvider() {
  if (process.env.NODE_ENV !== 'development') return null;
  return <AgentationLazy />;
}
```

Add to layout (`web/src/app/[locale]/layout.tsx`):

```tsx
import AgentationProvider from '@/components/dev/AgentationProvider';

// Inside the layout JSX, after MainLayout:
<MainLayout>{children}</MainLayout>
<AgentationProvider />
```

> **Note**: Must be a Client Component with `dynamic({ ssr: false })` because Next.js Server Components don't support `next/dynamic` with `ssr: false`.

### 3. Register MCP server (Claude Code)

**Global** (recommended — works in all projects):

```bash
claude mcp add --scope user agentation -- npx agentation-mcp server
```

**Per-project** (alternative):

```bash
cd <project-root>
npx agentation-mcp init
```

## Usage

1. Run dev server: `cd web && npm run dev`
2. Open browser — Agentation toolbar appears at bottom-right
3. Click the toolbar to activate, then click any element
4. Copy the structured output (CSS selector + component path + notes)
5. Paste to AI agent prompt

### Output Modes

| Mode | Detail Level | Use Case |
|------|-------------|----------|
| Compact | Selector + memo | Quick fixes |
| Standard | + bounding box | General use |
| Detailed | + full context | Layout work |
| Forensic | + computed styles | CSS debugging |

### Agent Sync (MCP)

Enable "Agent Sync" in the toolbar settings to stream annotations directly to Claude Code via MCP in real-time.

## Production Safety

- `AgentationProvider` checks `process.env.NODE_ENV !== 'development'` — returns `null` in production
- `agentation` is installed as `devDependency` — not included in production bundle
- No runtime overhead in production builds

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Toolbar not visible | Check dev server is running (`npm run dev`, not `npm run build`) |
| MCP not connecting | Run `claude mcp list` to verify registration |
| SSR error | Ensure `AgentationProvider` is a Client Component (`'use client'`) with `ssr: false` |
