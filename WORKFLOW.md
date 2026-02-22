# Workflow Guide

## Repository Scope Rule
- Always work inside `/Users/miyoungjang/Repository/quant/quant-investment2`.
- Do not switch to other repositories unless the user explicitly requests it.

## Default Execution Rule
- If required paths do not exist (for example `api/`, `.claude/`), create the scaffold in this repository and continue.
- Do not pause for confirmation when the intent is clear and implementation can proceed safely.

## GitHub Issue Tracking Rule
- When starting an issue: add a short `start` comment.
- After implementation: add `done` comment with changed files and verification commands.
- Keep parent issue as a progress index when an epic exists.

## PR Rule (Mandatory)
- Do not push implementation commits directly to `main`.
- Create a feature branch and open PR to `main`.
- Merge only after at least one approval and validation completion.
- Use squash merge.

PR quick flow:
```bash
git checkout -b feat/<topic>
git push -u origin feat/<topic>
gh pr create --base main --fill
```

## Post-Task Retrospective Rule (Mandatory)
At the end of every task, include a short retrospective block in the final update:
- `User Signals`: direct commands/corrections from user (what was emphasized)
- `Waiting Causes`: approvals/network/env delays that slowed execution
- `Automation Candidates`: command prefixes to auto-approve next time
- `Next-Run Defaults`: concrete defaults to avoid re-asking

Retrospective template:
```text
[Retrospective]
User Signals:
- ...
Waiting Causes:
- ...
Automation Candidates:
- ["..."]
Next-Run Defaults:
- ...
```

## Validation Rule
Run at minimum:
```bash
python3 -m py_compile api/main.py api/database.py api/routers/agent_task.py .claude/hooks/agent-task-tracker.py
python3 -m uvicorn api.main:app --port 8765
```

Smoke test:
```bash
curl -X GET http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/openapi.json
```
