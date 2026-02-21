#!/usr/bin/env python3
"""
PostToolUse hook for agent task tracking.

Reads TaskCreate/TaskUpdate tool events from stdin and forwards them
to the local agent-task API via fire-and-forget curl.

Any error is silently swallowed so the hook never blocks the main session.
"""

import json
import subprocess
import sys

API_BASE = "http://127.0.0.1:8765/api/agent-tasks"


def main() -> None:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
    except Exception:
        sys.exit(0)

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    tool_response = event.get("tool_response", {})
    session_id = event.get("session_id", "")

    if tool_name == "TaskCreate":
        # Extract task_id from the tool_response (created task)
        task_id = tool_response.get("taskId") or tool_response.get("id", "")
        if not task_id:
            sys.exit(0)

        payload = {
            "task_id": str(task_id),
            "session_id": session_id or None,
            "agent_type": tool_input.get("metadata", {}).get("agent_type") if tool_input.get("metadata") else None,
            "team_name": tool_input.get("metadata", {}).get("team_name") if tool_input.get("metadata") else None,
            "subject": tool_input.get("subject", ""),
            "description": tool_input.get("description"),
            "status": "pending",
            "metadata_json": tool_input.get("metadata"),
        }

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
        task_id = tool_input.get("taskId") or tool_input.get("id", "")
        if not task_id:
            sys.exit(0)

        payload = {
            "task_id": str(task_id),
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

        subprocess.Popen(
            [
                "curl", "-s", "-X", "PUT",
                f"{API_BASE}/{task_id}",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                "--connect-timeout", "2",
                "--max-time", "5",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
