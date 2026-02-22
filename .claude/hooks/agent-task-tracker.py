#!/usr/bin/env python3
"""
PostToolUse hook for agent task tracking.

Reads TaskCreate/TaskUpdate tool events from stdin and forwards them
to the local agent-task API via fire-and-forget curl.

Any error is silently swallowed so the hook never blocks the main session.

Debug mode:
  Set AGENT_TASK_HOOK_DEBUG=1 to write trace logs to a user-specific log file.
  Log path: /tmp/agent-task-hook-{uid}.log (permissions 0600)
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import quote

API_BASE = "http://127.0.0.1:8765/api/agent-tasks"
DEBUG = os.environ.get("AGENT_TASK_HOOK_DEBUG") == "1"
DEBUG_LOG = f"/tmp/agent-task-hook-{os.getuid()}.log"


def _log(msg: str) -> None:
    """Append a line to the debug log (only when DEBUG is enabled)."""
    if not DEBUG:
        return
    try:
        fd = os.open(DEBUG_LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def _extract_task_id(source: Dict[str, Any]) -> str:
    """Extract task_id from a dict, trying multiple key conventions."""
    return str(
        source.get("task_id")
        or source.get("taskId")
        or source.get("id")
        or ""
    )


def _extract_meta(tool_input: Dict[str, Any], key: str) -> Optional[str]:
    """Extract a meta field from top-level first, then metadata fallback."""
    val = tool_input.get(key)
    if val is not None:
        return val
    metadata = tool_input.get("metadata")
    if isinstance(metadata, dict):
        return metadata.get(key)
    return None


def main() -> None:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
    except Exception as e:
        _log(f"Failed to parse stdin: {e}")
        sys.exit(0)

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    tool_response = event.get("tool_response", {})
    session_id = event.get("session_id", "")

    _log(f"Event: tool={tool_name}, input_keys={list(tool_input.keys())}")

    if tool_name == "TaskCreate":
        # Extract task_id from the tool_response (created task)
        task_id = _extract_task_id(tool_response)
        if not task_id:
            _log("TaskCreate: no task_id found in response, skipping")
            sys.exit(0)

        payload = {
            "task_id": task_id,
            "session_id": session_id or None,
            "agent_type": _extract_meta(tool_input, "agent_type"),
            "team_name": _extract_meta(tool_input, "team_name"),
            "subject": tool_input.get("subject", ""),
            "description": tool_input.get("description"),
            "status": "pending",
            "metadata_json": tool_input.get("metadata"),
        }

        _log(f"TaskCreate: task_id={task_id}, status=pending")

        subprocess.Popen(
            [
                "curl", "-s", "-X", "POST", API_BASE,
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                "--connect-timeout", "2",
                "--max-time", "5",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    elif tool_name == "TaskUpdate":
        task_id = _extract_task_id(tool_input)
        if not task_id:
            _log("TaskUpdate: no task_id found in input, skipping")
            sys.exit(0)

        payload = {
            "task_id": task_id,
            "session_id": session_id or None,
        }
        if tool_input.get("status") is not None:
            payload["status"] = tool_input["status"]
        if tool_input.get("subject") is not None:
            payload["subject"] = tool_input["subject"]
        if tool_input.get("description") is not None:
            payload["description"] = tool_input["description"]
        if tool_input.get("metadata") is not None:
            payload["metadata_json"] = tool_input["metadata"]

        # Extract meta fields for update too
        agent_type = _extract_meta(tool_input, "agent_type")
        if agent_type is not None:
            payload["agent_type"] = agent_type
        team_name = _extract_meta(tool_input, "team_name")
        if team_name is not None:
            payload["team_name"] = team_name

        _log(f"TaskUpdate: task_id={task_id}, status={payload.get('status')}")

        # URL-encode task_id to safely handle special characters
        safe_id = quote(str(task_id), safe="")
        subprocess.Popen(
            [
                "curl", "-s", "-X", "PUT",
                f"{API_BASE}/{safe_id}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                "--connect-timeout", "2",
                "--max-time", "5",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    else:
        _log(f"Ignored tool: {tool_name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log(f"Unhandled exception: {e}")
    sys.exit(0)
