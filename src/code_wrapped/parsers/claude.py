"""Parse Claude Code session data from ~/.claude/projects/"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .base import (
    AgentType,
    Session,
    extract_repo_from_path,
    parse_iso_timestamp,
    sanitize_prompt,
)


def get_claude_sessions_dir() -> Path:
    """Return the default Claude sessions directory."""
    return Path.home() / ".claude" / "projects"


def find_field_in_session(lines: list[str], field: str, max_lines: int = 10) -> Any | None:
    """Walk session lines until we find a non-null value for the given field."""
    for line in lines[:max_lines]:
        try:
            obj = json.loads(line)
            value = obj.get(field)
            if value and value != "null":
                return value
        except json.JSONDecodeError:
            continue
    return None


def extract_tool_uses(messages: list[dict]) -> dict[str, int]:
    """Extract tool usage counts from messages."""
    tools: dict[str, int] = defaultdict(int)

    for msg in messages:
        content = msg.get("message", {}).get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_name = item.get("name", "unknown")
                    tools[tool_name] += 1

    return dict(tools)


def extract_errors(messages: list[dict]) -> list[str]:
    """Extract error messages from tool results."""
    errors: list[str] = []

    for msg in messages:
        # Check for tool_result errors
        if msg.get("type") == "user":
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        if item.get("is_error"):
                            error_content = item.get("content", "")
                            if error_content and len(error_content) < 500:
                                errors.append(error_content[:200])

        # Check toolUseResult for errors
        tool_result = msg.get("toolUseResult", {})
        if tool_result.get("stderr"):
            stderr = tool_result["stderr"]
            if len(stderr) < 500:
                errors.append(stderr[:200])

    return errors[:10]  # Limit to 10 errors per session


def extract_user_prompts(messages: list[dict]) -> list[str]:
    """Extract and sanitize user prompts from messages."""
    prompts: list[str] = []

    for msg in messages:
        if msg.get("type") == "user":
            content = msg.get("message", {}).get("content")
            if isinstance(content, str):
                prompts.append(sanitize_prompt(content))
            elif isinstance(content, list):
                # Skip tool results, only get actual user text
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_result":
                        continue
                    if isinstance(item, str):
                        prompts.append(sanitize_prompt(item))

    return prompts


def extract_token_count(messages: list[dict]) -> int | None:
    """Sum up token usage from assistant messages."""
    total_input = 0
    total_output = 0

    for msg in messages:
        if msg.get("type") == "assistant":
            usage = msg.get("message", {}).get("usage", {})
            total_input += usage.get("input_tokens", 0)
            total_input += usage.get("cache_creation_input_tokens", 0)
            total_input += usage.get("cache_read_input_tokens", 0)
            total_output += usage.get("output_tokens", 0)

    return total_input + total_output if (total_input or total_output) else None


def parse_session_file(session_file: Path) -> Session | None:
    """Parse a single Claude session file into a Session object."""
    try:
        with open(session_file) as f:
            lines = f.readlines()

        if not lines:
            return None

        # Parse all messages
        messages: list[dict] = []
        for line in lines:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not messages:
            return None

        # Extract session metadata
        cwd = find_field_in_session(lines, "cwd")
        session_id = find_field_in_session(lines, "sessionId")
        timestamp_str = find_field_in_session(lines, "timestamp")
        branch = find_field_in_session(lines, "gitBranch")

        if not timestamp_str:
            return None

        started_at = parse_iso_timestamp(timestamp_str)
        if not started_at:
            return None

        # Find end timestamp
        ended_at = None
        for msg in reversed(messages):
            ts = msg.get("timestamp")
            if ts:
                ended_at = parse_iso_timestamp(ts)
                break

        # Count messages by type
        user_count = sum(1 for m in messages if m.get("type") == "user")
        assistant_count = sum(1 for m in messages if m.get("type") == "assistant")

        return Session(
            id=session_id or session_file.stem,
            agent=AgentType.CLAUDE,
            started_at=started_at,
            ended_at=ended_at,
            repo=extract_repo_from_path(cwd),
            branch=branch,
            turn_count=len(messages),
            user_message_count=user_count,
            assistant_message_count=assistant_count,
            token_count=extract_token_count(messages),
            tools_used=extract_tool_uses(messages),
            user_prompts=extract_user_prompts(messages),
            errors=extract_errors(messages),
        )

    except Exception as e:
        # Return None for unparseable sessions
        return None


def parse_claude_sessions(
    sessions_dir: Path | None = None,
    year: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Iterator[Session]:
    """Parse all Claude sessions within the time window.

    Args:
        sessions_dir: Directory containing Claude sessions (default: ~/.claude/projects)
        year: Filter to specific year (e.g., 2025)
        start_date: Filter sessions starting after this date
        end_date: Filter sessions starting before this date

    Yields:
        Session objects for each valid session
    """
    if sessions_dir is None:
        sessions_dir = get_claude_sessions_dir()

    if not sessions_dir.exists():
        return

    # Set date filters
    if year and not start_date:
        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
    if year and not end_date:
        end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    # Find all session files
    session_files = list(sessions_dir.rglob("*.jsonl"))

    for session_file in session_files:
        session = parse_session_file(session_file)

        if session is None:
            continue

        # Apply date filters
        if start_date and session.started_at < start_date:
            continue
        if end_date and session.started_at > end_date:
            continue

        yield session
