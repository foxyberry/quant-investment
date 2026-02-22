# Contributing Guide

## PR-Only Merge Policy
- Direct push to `main` is prohibited by team rule.
- All code changes must go through a Pull Request.
- At least 1 reviewer approval is required before merge.
- Merge method: `Squash and merge` only.
- All open review conversations must be resolved before merge.
- CI/check commands in PR description must pass.

## Branch Strategy
- Base branch: `main`
- Feature branches:
  - `feat/<short-topic>`
  - `fix/<short-topic>`
  - `chore/<short-topic>`
  - `docs/<short-topic>`

Examples:
- `feat/realtime-chat`
- `fix/task-status-transition`

## Required PR Checklist
- Link issue(s): `Closes #...` or `Refs #...`
- Explain scope and non-scope
- List changed files/areas
- Add validation steps and results
- Include screenshots for UI changes
- Mention rollback plan for risky changes
- Add a short retrospective in PR description/comment:
  - user directives/corrections,
  - delays encountered,
  - automation opportunities (approved prefixes),
  - defaults for next run.

## Local Flow
```bash
git checkout -b feat/<topic>
# implement changes
git add .
git commit -m "feat: <summary>"
git push -u origin feat/<topic>
gh pr create --base main --fill
```

## Merge Flow
1. Reviewer approval
2. Checks green
3. Conversation resolved
4. Squash merge
5. Delete feature branch
