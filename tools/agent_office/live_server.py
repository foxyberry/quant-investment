#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class AgentDef:
    agent_id: str
    dirs: tuple[str, ...]


AGENTS: tuple[AgentDef, ...] = (
    AgentDef("chief", ("api/", "web/", "engine/", "portfolio/", "scripts/", "docs/", "tests/")),
    AgentDef("planner", ("docs/works/",)),
    AgentDef("designer", ("web/",)),
    AgentDef("quant", ("engine/", "discovery/", "screener/")),
    AgentDef("data", ("pipeline/", "data_enrichment/", "news/", "models/", "llm/")),
    AgentDef("portfolio", ("portfolio/",)),
    AgentDef("server", ("api/",)),
    AgentDef("frontend", ("web/",)),
    AgentDef("qa", ("tests/", "api/tests/")),
)

PROJECTS = (
    {
        "id": "qi1",
        "name": "quant-investment",
        "roomName": "개발1실",
        "color": "#6366f1",
        "bgColor": "rgba(99,102,241,0.15)",
    },
    {
        "id": "qi2",
        "name": "quant-investment2",
        "roomName": "개발2실",
        "color": "#f59e0b",
        "bgColor": "rgba(245,158,11,0.15)",
    },
)

STATUS_COLOR = {
    "active": "#22c55e",
    "waiting_input": "#38bdf8",
    "working": "#f59e0b",
    "idle": "#6b7280",
    "sleeping": "#374151",
}
STATUS_LABEL = {
    "active": "Active",
    "waiting_input": "Waiting",
    "working": "Working",
    "idle": "Idle",
    "sleeping": "Sleeping",
}
RATE_LIMIT_TS_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z).*(rate_limit_error|would exceed your account's rate limit)"
)
ISO_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
BASH_BLOCK_RE = re.compile(r"Bash\((?P<cmd>.*?)\)", re.DOTALL)
SECRET_RE = re.compile(r"(?i)(api[-_]?key|token|secret|password)\s*[:=]\s*([^\s\"']+)")
FORKED_USAGE_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}T[0-9:.]+Z).+Forked agent \[(?P<agent>[^\]]+)\] finished:.*totalUsage: input=(?P<input>\d+) output=(?P<output>\d+)"
)
QI1_PATH_RE = re.compile(r"/quant/quant-investment(?:/|$)")
QI2_PATH_RE = re.compile(r"/quant/quant-investment2(?:/|$)")


def run_git(repo: Path, args: list[str]) -> str:
    cmd = ["git", "-C", str(repo), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:
        return ""
    return proc.stdout.strip()


def branch_name(repo: Path) -> str:
    out = run_git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    return out or "unknown"


def count_commits(repo: Path, days: int, dirs: tuple[str, ...]) -> int:
    out = run_git(
        repo,
        ["rev-list", "--count", "--since", f"{days}.days", "HEAD", "--", *dirs],
    )
    return int(out) if out.isdigit() else 0


def tracked_files(repo: Path, dirs: tuple[str, ...]) -> int:
    out = run_git(repo, ["ls-files", "--", *dirs])
    if not out:
        return 0
    return len([line for line in out.splitlines() if line.strip()])


def last_active(repo: Path, dirs: tuple[str, ...]) -> str | None:
    out = run_git(repo, ["log", "-n", "1", "--pretty=format:%cI", "--", *dirs])
    return out or None


def has_uncommitted_changes(repo: Path, dirs: tuple[str, ...]) -> bool:
    out = run_git(repo, ["status", "--porcelain", "--", *dirs])
    return bool(out.strip())


def files_changed_for_commit(repo: Path, commit_hash: str, dirs: tuple[str, ...]) -> int:
    out = run_git(repo, ["show", "--pretty=format:", "--name-only", commit_hash, "--", *dirs])
    if not out:
        return 0
    return len([line for line in out.splitlines() if line.strip()])


def recent_activity(repo: Path, dirs: tuple[str, ...], limit: int = 2) -> list[dict[str, Any]]:
    fmt = "%h%x1f%cI%x1f%s"
    out = run_git(repo, ["log", f"-n{limit}", f"--pretty=format:{fmt}", "--", *dirs])
    acts: list[dict[str, Any]] = []
    if not out:
        return acts
    for row in out.splitlines():
        parts = row.split("\x1f")
        if len(parts) != 3:
            continue
        short_hash, date_iso, message = parts
        acts.append(
            {
                "hash": short_hash,
                "message": message,
                "date": date_iso,
                "files_changed": files_changed_for_commit(repo, short_hash, dirs),
            }
        )
    return acts


def parse_iso(iso_str: str | None) -> datetime | None:
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def state_from_last_active(last_active_iso: str | None, now_utc: datetime) -> str:
    dt = parse_iso(last_active_iso)
    if dt is None:
        return "sleeping"

    age = now_utc - dt.astimezone(timezone.utc)
    if age <= timedelta(minutes=20):
        return "active"
    if age <= timedelta(hours=2):
        return "waiting_input"
    if age <= timedelta(days=3):
        return "working"
    if age <= timedelta(days=14):
        return "idle"
    return "sleeping"


def detect_claude_rate_limit(now_utc: datetime) -> dict[str, Any]:
    debug_dir = Path.home() / ".claude" / "debug"
    if not debug_dir.exists():
        return {"is_limited": False, "last_hit_at": None}

    candidates = sorted(
        [p for p in debug_dir.glob("*.txt") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:8]
    newest_hit: datetime | None = None

    for path in candidates:
        try:
            with path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(size - 220_000, 0))
                tail = f.read().decode("utf-8", errors="ignore")
        except OSError:
            continue

        for m in RATE_LIMIT_TS_RE.finditer(tail):
            dt = parse_iso(m.group(1))
            if dt is None:
                continue
            dt_utc = dt.astimezone(timezone.utc)
            if newest_hit is None or dt_utc > newest_hit:
                newest_hit = dt_utc

    if newest_hit is None:
        return {"is_limited": False, "last_hit_at": None}

    is_limited = (now_utc - newest_hit) <= timedelta(hours=6)
    return {"is_limited": is_limited, "last_hit_at": newest_hit.isoformat()}


def detect_claude_code_state(now_utc: datetime, is_limited: bool) -> dict[str, Any]:
    debug_dir = Path.home() / ".claude" / "debug"
    newest_seen: datetime | None = None

    if debug_dir.exists():
        for p in debug_dir.glob("*.txt"):
            try:
                dt = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if newest_seen is None or dt > newest_seen:
                newest_seen = dt

    if is_limited:
        return {
            "state": "idle",
            "label": "Limited",
            "color": "#f87171",
            "last_active": newest_seen.isoformat() if newest_seen else None,
        }
    if newest_seen is None:
        return {"state": "idle", "label": "Idle", "color": STATUS_COLOR["idle"], "last_active": None}

    age = now_utc - newest_seen
    if age <= timedelta(minutes=3):
        state = "active"
    elif age <= timedelta(minutes=20):
        state = "waiting_input"
    elif age <= timedelta(hours=4):
        state = "working"
    else:
        state = "idle"

    return {
        "state": state,
        "label": STATUS_LABEL[state],
        "color": STATUS_COLOR[state],
        "last_active": newest_seen.isoformat(),
    }


def sanitize_command(cmd: str) -> str:
    s = " ".join(cmd.strip().split())
    s = SECRET_RE.sub(r"\1=***", s)
    s = re.sub(r"(?i)(bearer\s+)[a-z0-9._-]+", r"\1***", s)
    return s[:220]


def infer_cmd_status(context: str) -> tuple[str, str]:
    lower = context.lower()
    if "running in the background" in lower or "running" in lower:
        return ("running", "Running")
    if "failed" in lower or "error" in lower:
        return ("failed", "Failed")
    return ("done", "Done")


def parse_recent_commands(now_utc: datetime, limit: int = 10) -> list[dict[str, Any]]:
    debug_dir = Path.home() / ".claude" / "debug"
    if not debug_dir.exists():
        return []

    files = sorted(
        [p for p in debug_dir.glob("*.txt") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:8]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for path in files:
        try:
            with path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(size - 300_000, 0))
                text = f.read().decode("utf-8", errors="ignore")
        except OSError:
            continue

        file_ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        for m in BASH_BLOCK_RE.finditer(text):
            cmd = sanitize_command(m.group("cmd"))
            if not cmd:
                continue
            post = text[m.end() : m.end() + 280]
            status, label = infer_cmd_status(post)
            ts_match = ISO_TS_RE.search(text[max(0, m.start() - 220) : m.start()])
            ts = parse_iso(ts_match.group(0)).isoformat() if ts_match and parse_iso(ts_match.group(0)) else file_ts
            dedupe = (cmd, status)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            rows.append(
                {
                    "cmd": cmd,
                    "status": status,
                    "label": label,
                    "time": ts,
                    "source": path.name,
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


def detect_repo_key(text: str) -> str:
    # Check qi2 first because qi1 is a prefix of qi2.
    if QI2_PATH_RE.search(text):
        return "qi2"
    if QI1_PATH_RE.search(text):
        return "qi1"
    return "unknown"


def parse_runtime_telemetry(now_utc: datetime) -> dict[str, Any]:
    debug_dir = Path.home() / ".claude" / "debug"
    if not debug_dir.exists():
        return {
            "projects": {
                "qi1": {"active_commands": 0, "last_command": "", "last_seen": None, "observed_tokens": 0, "signal": "none"},
                "qi2": {"active_commands": 0, "last_command": "", "last_seen": None, "observed_tokens": 0, "signal": "none"},
            },
            "forked_agents": [],
        }

    files = sorted(
        [p for p in debug_dir.glob("*.txt") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:10]
    project_state = {
        "qi1": {"active_commands": 0, "last_command": "", "last_seen": None, "observed_tokens": 0, "signal": "none"},
        "qi2": {"active_commands": 0, "last_command": "", "last_seen": None, "observed_tokens": 0, "signal": "none"},
    }
    usage: dict[tuple[str, str], dict[str, Any]] = {}

    for path in files:
        try:
            with path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(size - 350_000, 0))
                text = f.read().decode("utf-8", errors="ignore")
        except OSError:
            continue

        file_repo_key = detect_repo_key(text)
        lines = text.splitlines()[-2000:]

        # Project runtime from Bash executions in this session.
        for ln in reversed(lines):
            if "Bash(" not in ln:
                continue
            m = BASH_BLOCK_RE.search(ln)
            if not m:
                continue
            cmd = sanitize_command(m.group("cmd"))
            ts_m = ISO_TS_RE.search(ln)
            ts_dt = parse_iso(ts_m.group(0)) if ts_m else None
            repo_key = detect_repo_key(ln)
            if repo_key == "unknown":
                repo_key = detect_repo_key(cmd)
            if repo_key == "unknown":
                continue
            if repo_key in ("qi1", "qi2"):
                st = project_state[repo_key]
                if not st["last_command"]:
                    st["last_command"] = cmd
                    st["last_seen"] = ts_dt.isoformat() if ts_dt else datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
                if ts_dt and (now_utc - ts_dt.astimezone(timezone.utc)) <= timedelta(minutes=10):
                    st["active_commands"] += 1
            break

        # Forked-agent token usage.
        for ln in lines:
            m = FORKED_USAGE_RE.search(ln)
            if not m:
                continue
            repo_key = detect_repo_key(ln)
            if repo_key == "unknown":
                repo_key = file_repo_key
            ag = m.group("agent")
            key = (repo_key, ag)
            if key not in usage:
                usage[key] = {
                    "repo": repo_key,
                    "agent": ag,
                    "events": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "last_time": None,
                }
            row = usage[key]
            row["events"] += 1
            in_tok = int(m.group("input"))
            out_tok = int(m.group("output"))
            row["input_tokens"] += in_tok
            row["output_tokens"] += out_tok
            if repo_key in ("qi1", "qi2"):
                project_state[repo_key]["observed_tokens"] += in_tok + out_tok
            ts = parse_iso(m.group("ts"))
            if ts:
                cur = parse_iso(row["last_time"]) if row["last_time"] else None
                if cur is None or ts > cur:
                    row["last_time"] = ts.isoformat()

    for key in ("qi1", "qi2"):
        st = project_state[key]
        if st["active_commands"] > 0:
            st["signal"] = "high"
        elif st["observed_tokens"] > 0:
            st["signal"] = "medium"
        elif st["last_seen"]:
            st["signal"] = "low"
        else:
            st["signal"] = "none"

    forked = sorted(
        usage.values(),
        key=lambda r: (r["repo"], -(r["input_tokens"] + r["output_tokens"])),
    )
    return {"projects": project_state, "forked_agents": forked[:20]}


def apply_rate_limit_override(status_data: dict[str, Any]) -> None:
    agents = status_data.get("agents", {})
    for agent in agents.values():
        state = agent.get("status", {}).get("state")
        if state in ("active", "working", "waiting_input"):
            agent["status"] = {"state": "idle", "label": STATUS_LABEL["idle"], "color": STATUS_COLOR["idle"]}

    summary = {"total_agents": len(AGENTS), "active": 0, "waiting_input": 0, "working": 0, "idle": 0, "sleeping": 0}
    for agent in agents.values():
        s = agent.get("status", {}).get("state", "sleeping")
        if s not in summary:
            s = "sleeping"
        summary[s] += 1
    status_data["summary"] = summary


def recalc_summary(status_data: dict[str, Any]) -> None:
    agents = status_data.get("agents", {})
    summary = {"total_agents": len(AGENTS), "active": 0, "waiting_input": 0, "working": 0, "idle": 0, "sleeping": 0}
    for agent in agents.values():
        s = agent.get("status", {}).get("state", "sleeping")
        if s not in summary:
            s = "sleeping"
        summary[s] += 1
    status_data["summary"] = summary


def enrich_chief_activity(status_data: dict[str, Any], now_utc: datetime, project_name: str, is_limited: bool) -> None:
    agents = status_data.get("agents", {})
    chief = agents.get("chief")
    if not chief:
        return

    summary = status_data.get("summary", {})
    waiting_count = int(summary.get("waiting_input", 0))
    active_count = int(summary.get("active", 0))
    working_count = int(summary.get("working", 0))

    if is_limited:
        chief_state = "idle"
        msg = "Claude limit 감지, 팀 작업을 일시 점검 중"
    elif waiting_count > 0:
        chief_state = "waiting_input"
        msg = f"사용자 응답 대기 {waiting_count}건 확인, 우선순위 정리 중"
    elif active_count + working_count > 0:
        chief_state = "active"
        msg = f"{project_name} 작업자 {active_count + working_count}명 조율 중"
    else:
        chief_state = "working"
        msg = "다음 작업 큐와 리뷰 순서를 정리 중"

    now_iso = now_utc.isoformat()
    chief["status"] = {"state": chief_state, "label": STATUS_LABEL[chief_state], "color": STATUS_COLOR[chief_state]}
    chief["last_active"] = now_iso
    chief["recent_activity"] = [
        {"hash": "chief", "message": msg, "date": now_iso, "files_changed": 0},
    ]
    recalc_summary(status_data)


def pick_claude_current_task(projects_payload: list[dict[str, Any]], is_limited: bool) -> str:
    if is_limited:
        return "Claude limit 감지, 요청 대기 및 작업 재배치 중"

    candidates: list[str] = []
    for proj in projects_payload:
        agents = proj.get("statusData", {}).get("agents", {})
        chief = agents.get("chief", {})
        acts = chief.get("recent_activity", [])
        if acts and acts[0].get("message"):
            candidates.append(str(acts[0]["message"]))

    if not candidates:
        return "진행 중인 조율 작업 없음"

    waiting = [msg for msg in candidates if "응답 대기" in msg]
    if waiting:
        return waiting[0]
    return candidates[0]


def build_agent_status(repo: Path, now_utc: datetime) -> dict[str, Any]:
    agents: dict[str, Any] = {}
    summary = {"total_agents": len(AGENTS), "active": 0, "waiting_input": 0, "working": 0, "idle": 0, "sleeping": 0}

    for agent in AGENTS:
        c7 = count_commits(repo, 7, agent.dirs)
        c30 = count_commits(repo, 30, agent.dirs)
        files = tracked_files(repo, agent.dirs)
        last = last_active(repo, agent.dirs)
        state = state_from_last_active(last, now_utc)
        dirty = has_uncommitted_changes(repo, agent.dirs)
        if dirty and state in ("idle", "sleeping", "waiting_input"):
            state = "working"
        summary[state] += 1

        agents[agent.agent_id] = {
            "status": {"state": state, "label": STATUS_LABEL[state], "color": STATUS_COLOR[state]},
            "stats": {"commits_7d": c7, "commits_30d": c30, "files_tracked": files, "dirty": dirty},
            "last_active": last,
            "recent_activity": recent_activity(repo, agent.dirs, limit=2),
        }

    return {"agents": agents, "summary": summary}


def build_payload(repo_map: dict[str, Path]) -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    rate_limit = detect_claude_rate_limit(now_utc)
    claude_code = detect_claude_code_state(now_utc, rate_limit["is_limited"])
    recent_commands = parse_recent_commands(now_utc, limit=10)
    runtime = parse_runtime_telemetry(now_utc)
    projects_payload: list[dict[str, Any]] = []

    for proj in PROJECTS:
        repo = repo_map[proj["id"]]
        status_data = build_agent_status(repo, now_utc)
        if rate_limit["is_limited"]:
            apply_rate_limit_override(status_data)
        enrich_chief_activity(status_data, now_utc, proj["name"], rate_limit["is_limited"])
        status_data["generated_at"] = now_utc.isoformat()
        projects_payload.append(
            {
                "id": proj["id"],
                "name": proj["name"],
                "roomName": proj["roomName"],
                "color": proj["color"],
                "bgColor": proj["bgColor"],
                "branch": branch_name(repo),
                "statusData": status_data,
            }
        )

    claude_code["current_task"] = pick_claude_current_task(projects_payload, rate_limit["is_limited"])

    return {
        "generated_at": now_utc.isoformat(),
        "projects": projects_payload,
        "claude_limit": rate_limit,
        "claude_code": claude_code,
        "recent_commands": recent_commands,
        "runtime": runtime,
    }


def make_handler(html_path: Path, repo_map: dict[str, Path]):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/", "/index.html"):
                try:
                    html = html_path.read_bytes()
                except OSError as exc:
                    self._send(500, f"Failed to read HTML: {exc}".encode(), "text/plain; charset=utf-8")
                    return
                self._send(200, html, "text/html; charset=utf-8")
                return

            if path == "/api/agent-office/status":
                payload = build_payload(repo_map)
                self._send(
                    200,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8",
                )
                return

            self._send(404, b"Not Found", "text/plain; charset=utf-8")

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_root = script_dir.parents[1]
    default_quant_root = default_root.parent

    parser = argparse.ArgumentParser(description="Serve Quant Agent Office with live git status.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--html",
        default=str(default_quant_root / "quant-desktop-live.html"),
        help="Path to quant-desktop-live.html",
    )
    parser.add_argument(
        "--qi1-repo",
        default=str(default_quant_root / "quant-investment"),
        help="Path to quant-investment repo",
    )
    parser.add_argument(
        "--qi2-repo",
        default=str(default_root),
        help="Path to quant-investment2 repo",
    )
    args = parser.parse_args()

    html_path = Path(args.html).resolve()
    repo_map = {
        "qi1": Path(args.qi1_repo).resolve(),
        "qi2": Path(args.qi2_repo).resolve(),
    }
    for repo in repo_map.values():
        if not (repo / ".git").exists():
            raise SystemExit(f"Not a git repo: {repo}")
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")

    server = ThreadingHTTPServer((args.host, args.port), make_handler(html_path, repo_map))
    print(f"Serving Agent Office at http://{args.host}:{args.port}")
    print(f"HTML: {html_path}")
    print(f"API:  http://{args.host}:{args.port}/api/agent-office/status")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
