# AGENTS.md

This repository root is:
- `/Users/miyoungjang/Repository/quant/quant-investment2`

Codex should treat this directory as the default project root.

Execution workflow is documented in:
- `WORKFLOW.md`

## Default Working Rules
- Always run commands from this root unless a task requires a subdirectory.
- Never inspect or modify sibling repositories unless explicitly instructed.
- Prefer `rg`/`rg --files` for search.
- Do not modify files outside this repository unless explicitly requested.
- Validate changes with lightweight checks before finishing.
- Follow PR-only policy:
  - Never merge by direct push to `main`.
  - Use feature branch -> PR -> review -> squash merge.
- At task end, always include a short retrospective:
  - user directives/corrections,
  - delay causes,
  - auto-approval candidates,
  - next-run defaults.

## GitHub Safety Guardrails (Codex + Claude Common)
1. Repeat `code -> PR -> revise` until LGTM, but do not commit intermediate steps.
   - Leave one final consolidated PR comment summarizing all review rounds and fixes.
2. If a request can cause high-volume actions in a short time (e.g., \"create 100 issues\"), do not create 100 issues directly.
   - Group and process in batches.
3. Keep at least 2 minutes between each issue creation.
4. During issue execution, keep at least 2 minutes between each PR merge operation.

## Default Issue Workflow (Auto, Unless User Overrides)
For every issue, follow this execution order by default with Claude Code MCP collaboration:
1. Direction review
   - Clarify scope, acceptance criteria, and risks before coding.
2. Implementation delegation
   - Delegate implementation tasks where useful, then integrate results.
3. Code review
   - Perform structured review focused on correctness, regressions, and tests.
4. Fix review findings
   - Apply fixes from review findings before finalizing.
5. Merge
   - Merge only after validations pass and self-review is `LGTM`.

Operational rules:
- Do not require the user to restate this workflow each time.
- Keep one final consolidated PR comment that summarizes:
  - direction decisions,
  - review findings,
  - fixes applied,
  - final validation results.

## Issue Lock Rule (Mandatory for Codex)
- Goal: prevent duplicate agent work on the same issue.
- On issue start, Codex must immediately:
  - add `in-progress` label,
  - add `start` comment including `agent`, `started_at` (UTC), `scope`, `branch`.
- Before starting implementation, Codex must check:
  - `in-progress` label exists, and
  - recent `start` comment from another active agent.
  - If both are true, stop and pick another issue.
- On completion, Codex must:
  - add `done` comment with changed files and verification commands,
  - remove `in-progress` label.

Recommended commands:
```bash
gh issue edit <number> --add-label in-progress
gh issue comment <number> --body "start: agent=<name>, started_at=<YYYY-MM-DD HH:MM UTC>, scope=<scope>, branch=<branch>"
gh issue comment <number> --body "done: files=<...>, verify=<...>"
gh issue edit <number> --remove-label in-progress
```

## Auto-Execution Defaults
- PR completion:
  - After Codex self-review `LGTM` and passing validations, execute squash merge immediately.
  - After merge, continue to the next task automatically.
- Workspace routing:
  - `/Users/miyoungjang/Repository/quant/quant-investment` -> frontend tasks only
  - `/Users/miyoungjang/Repository/quant/quant-investment2` -> condition-related issue discovery/creation only
  - `/Users/miyoungjang/Repository/quant/quant-investment3` -> backend issue work only

## Codex Preflight Checklist
- Git user is configured (`user.name`, `user.email`).
- Remote access works (`ssh -T git@github.com` and `git fetch`).
- Codex auth is available (`~/.codex/auth.json` or `OPENAI_API_KEY`).
- Trust level includes this repo path in `~/.codex/config.toml`.

## Collaboration Docs
- PR and merge rules: `CONTRIBUTING.md`
- PR template: `.github/pull_request_template.md`

## Project Onboarding (Claude Parity)
- Read order:
  1. `README.md`
  2. `config/base_config.yaml`
  3. `config/screening_criteria.yaml`
  4. `config/portfolio.yaml`
- Optional docs by task:
  - options: `docs/OPTIONS_TRACKER_README.md`
  - market calendar/timezone: `docs/MARKET_CALENDAR_README.md`
  - strategy builder: `docs/STRATEGY_BUILDER_README.md`

## MCP / Tooling Defaults
- MCP servers are defined in `.mcp.json`.
- Default enabled set should match Claude setup:
  - `context7`
  - `playwright`
  - `shadcn`
  - `stitch`
  - `codex`

## Local Dev Defaults
- API dev server (Claude setup parity): `source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload`
- Web dev server (Claude setup parity): `cd web && PORT=3002 npm run dev`
- Prefer these ports unless user requests otherwise.

## Agent Team Defaults (Claude Parity)
- Lead-first model:
  - Lead agent handles planning/review/integration/git.
  - Implementation can be delegated to subagents.
- Directory ownership contract:
  - quant/data teams: `engine/`, `discovery/`, `screener/`, `pipeline/`, `data_enrichment/`, `news/`, `models/`, `llm/`
  - portfolio team: `portfolio/`
  - backend API team: `api/`
  - frontend team: `web/`
  - A subagent should not modify directories owned by another team unless explicitly instructed.
- Execution pattern default:
  - Prefer Subagent (`Task`) for single-directory or independent parallel work.
  - Use Agent Teams only when teammate outputs depend on each other and direct teammate messaging is required.
- Team execution guardrails:
  - Spawn prompts must include objective, target files, constraints, and acceptance criteria.
  - Keep one integration owner (lead) responsible for final conflict resolution and PR quality.
  - For risky or multi-file changes, require a review pass before merge.
