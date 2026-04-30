"""Slack Block Kit formatting helpers for notification dispatch."""

from __future__ import annotations

import re
from typing import List

_SIGNAL_COLORS = {
    "🔴": "#E74C3C",
    "🟡": "#F39C12",
    "🟢": "#2ECC71",
    "🎯": "#3498DB",
}

_STOCK_SECTION_RE = re.compile(r"^####\s+\d+\.\s+(🔴|🟡|🟢)")
_ACTION_SECTION_RE = re.compile(r"^###\s+🎯")


def _to_slack_mrkdwn(text: str) -> str:
    """Convert markdown inline formatting to Slack mrkdwn syntax."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"_\1_", text)
    return text


def _split_text(text: str, max_len: int = 2900) -> list[str]:
    """Split text into chunks <= max_len, preferring newline boundaries."""
    chunks: list[str] = []
    while len(text) > max_len:
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def md_to_slack_blocks(content: str) -> List[dict]:
    """Convert report markdown to Slack Block Kit blocks."""
    blocks: list[dict] = []
    lines = content.split("\n")
    text_buffer: list[str] = []
    table_header: list[str] | None = None
    table_rows: list[list[str]] = []

    def flush_text() -> None:
        nonlocal text_buffer
        if not text_buffer:
            return
        joined = "\n".join(text_buffer).strip()
        text_buffer = []
        if not joined:
            return
        for chunk in _split_text(_to_slack_mrkdwn(joined)):
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})

    def flush_table() -> None:
        nonlocal table_header, table_rows
        if not table_header:
            return

        cols = len(table_header)
        if cols == 2:
            lines_out: list[str] = []
            for row in table_rows:
                if len(row) < 2:
                    continue
                key = _to_slack_mrkdwn(row[0].strip())
                val = _to_slack_mrkdwn(row[1].strip())
                lines_out.append(f"*{key}*: {val or '—'}")
            text = "\n".join(lines_out)
            for chunk in _split_text(text):
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})
        else:
            lines_out = [" | ".join(f"*{h.strip()}*" for h in table_header)]
            for row in table_rows:
                lines_out.append(" | ".join(_to_slack_mrkdwn(c.strip()) for c in row))
            text = "\n".join(lines_out)
            for chunk in _split_text(text):
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})

        table_header = None
        table_rows.clear()

    for line in lines:
        stripped = line.strip()

        if line.startswith("## "):
            flush_text()
            flush_table()
            blocks.append({
                "type": "header",
                "text": {"type": "plain_text", "text": line[3:].strip(), "emoji": True},
            })
            continue

        if line.startswith("### "):
            flush_text()
            flush_table()
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{_to_slack_mrkdwn(line[4:].strip())}*"},
            })
            continue

        if line.startswith("#### "):
            flush_text()
            flush_table()
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": _to_slack_mrkdwn(line[5:].strip())}],
            })
            continue

        if re.match(r"^-{3,}$", stripped):
            flush_text()
            flush_table()
            blocks.append({"type": "divider"})
            continue

        if line.startswith("> "):
            flush_text()
            flush_table()
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": _to_slack_mrkdwn(line[2:])}],
            })
            continue

        if line.startswith("|") and line.endswith("|"):
            flush_text()
            if re.match(r"^[\s|:-]+$", line):
                continue
            cells = line[1:-1].split("|")
            if table_header is None:
                table_header = cells
            else:
                table_rows.append(cells)
            continue

        if table_header is not None:
            flush_table()

        if not stripped:
            flush_text()
            continue

        text_buffer.append(line)

    flush_text()
    flush_table()
    return blocks


def md_to_report_payload(content: str) -> dict:
    """Convert report markdown to a Slack payload with colored attachments."""
    lines = content.split("\n")
    segments: list[tuple[str | None, list[str]]] = []
    current_color: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stock_m = _STOCK_SECTION_RE.match(line)
        action_m = _ACTION_SECTION_RE.match(line)

        if stock_m or action_m:
            if current_lines:
                segments.append((current_color, current_lines))
            current_lines = [line]
            if stock_m:
                current_color = _SIGNAL_COLORS.get(stock_m.group(1))
            else:
                current_color = _SIGNAL_COLORS["🎯"]
        else:
            current_lines.append(line)

    if current_lines:
        segments.append((current_color, current_lines))

    main_blocks: list[dict] = []
    color_blocks: dict[str, list[dict]] = {}

    for color, seg_lines in segments:
        seg_blocks = md_to_slack_blocks("\n".join(seg_lines))
        if color is None:
            main_blocks.extend(seg_blocks)
            continue
        color_blocks.setdefault(color, []).extend(seg_blocks)

    attachments: list[dict] = []
    for color, blocks in color_blocks.items():
        if not blocks:
            continue
        for i in range(0, len(blocks), 50):
            attachments.append({
                "color": color,
                "blocks": blocks[i:i + 50],
            })

    return {"blocks": main_blocks, "attachments": attachments}
