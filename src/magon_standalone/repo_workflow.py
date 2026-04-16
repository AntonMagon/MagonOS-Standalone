"""Helpers for the repo-level project memory workflow."""

from __future__ import annotations

from dataclasses import dataclass

ACTIVE_START = "<!-- ACTIVE:START -->"
ACTIVE_END = "<!-- ACTIVE:END -->"
WORKLOG_START = "<!-- WORKLOG:START -->"
WORKLOG_END = "<!-- WORKLOG:END -->"


@dataclass(frozen=True)
class FinalizeRecord:
    timestamp_label: str
    branch: str
    summary: str
    changed: list[str]
    verified: list[str]
    risk: str
    focus: str


def _replace_block(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"missing_marker_block:{start_marker}")
    end += len(end_marker)
    return text[:start] + replacement + text[end:]


def render_active_block(record: FinalizeRecord) -> str:
    return "\n".join(
        [
            ACTIVE_START,
            f"- Updated at: `{record.timestamp_label}`",
            f"- Branch: `{record.branch}`",
            f"- Current focus: {record.focus}",
            f"- Last verified workflow status: {', '.join(record.verified)}",
            f"- Biggest operational risk: {record.risk}",
            ACTIVE_END,
        ]
    )


def render_worklog_entry(record: FinalizeRecord) -> str:
    lines = [
        f"### {record.timestamp_label} | {record.branch}",
        f"- Summary: {record.summary}",
        "- Changed:",
    ]
    lines.extend([f"  - {item}" for item in record.changed])
    lines.append("- Verified:")
    lines.extend([f"  - {item}" for item in record.verified])
    lines.append("- Risk:")
    lines.append(f"  - {record.risk}")
    return "\n".join(lines)


def prepend_worklog_entry(text: str, entry: str) -> str:
    marker = f"{WORKLOG_START}\n"
    if marker not in text or WORKLOG_END not in text:
        raise ValueError("missing_worklog_markers")
    return text.replace(marker, f"{marker}{entry}\n", 1)


def update_project_memory(markdown: str, record: FinalizeRecord) -> str:
    updated = _replace_block(markdown, ACTIVE_START, ACTIVE_END, render_active_block(record))
    return prepend_worklog_entry(updated, render_worklog_entry(record))
