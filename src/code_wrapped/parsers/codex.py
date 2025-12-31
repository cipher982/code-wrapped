"""Parse OpenAI Codex session data from ~/.codex/sessions/"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .base import (
    AgentType,
    Session,
    extract_repo_from_path,
    parse_iso_timestamp,
    sanitize_prompt,
)


def get_codex_sessions_dir() -> Path:
    """Return the default Codex sessions directory."""
    return Path.home() / ".codex" / "sessions"


def extract_tool_uses_codex(messages: list[dict]) -> dict[str, int]:
    """Extract tool usage from Codex response items."""
    tools: dict[str, int] = defaultdict(int)

    for msg in messages:
        if msg.get("type") == "response_item":
            payload = msg.get("payload", {})
            # Codex uses different tool format
            if payload.get("type") == "function_call":
                tool_name = payload.get("name", "unknown")
                tools[tool_name] += 1

    return dict(tools)


def extract_user_prompts_codex(messages: list[dict]) -> list[str]:
    """Extract user prompts from Codex messages."""
    prompts: list[str] = []

    for msg in messages:
        if msg.get("type") == "response_item":
            payload = msg.get("payload", {})
            if payload.get("role") == "user":
                content = payload.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "input_text":
                            text = item.get("text", "")
                            if text:
                                prompts.append(sanitize_prompt(text))

    return prompts


def parse_codex_session_file(session_file: Path) -> Session | None:
    """Parse a single Codex session file into a Session object.

    Handles two formats:
    1. Old format (*.json): {"session": {...}, "items": [...]}
    2. New format (*.jsonl): Line-delimited JSON with session_meta and response_item
    """
    try:
        # Codex can be .json or .jsonl
        if session_file.suffix == ".json":
            with open(session_file) as f:
                data = json.load(f)

            # Handle old format: {"session": {...}, "items": [...]}
            if isinstance(data, dict) and "session" in data:
                session_data = data.get("session", {})
                items = data.get("items", [])

                session_id = session_data.get("id")
                timestamp_str = session_data.get("timestamp")
                cwd = session_data.get("cwd")

                if not timestamp_str:
                    return None

                started_at = parse_iso_timestamp(timestamp_str)
                if not started_at:
                    return None

                # Count user/assistant messages from items
                user_count = sum(1 for item in items if item.get("role") == "user")
                assistant_count = sum(1 for item in items if item.get("role") == "assistant")

                # Extract tool uses from items
                tools: dict[str, int] = defaultdict(int)
                for item in items:
                    if item.get("type") == "function_call":
                        tool_name = item.get("name", "unknown")
                        tools[tool_name] += 1

                # Extract user prompts
                prompts: list[str] = []
                for item in items:
                    if item.get("role") == "user":
                        content = item.get("content", [])
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "input_text":
                                    text = c.get("text", "")
                                    if text:
                                        prompts.append(sanitize_prompt(text))

                return Session(
                    id=session_id or session_file.stem,
                    agent=AgentType.CODEX,
                    started_at=started_at,
                    repo=extract_repo_from_path(cwd),
                    turn_count=len(items),
                    user_message_count=user_count,
                    assistant_message_count=assistant_count,
                    tools_used=dict(tools),
                    user_prompts=prompts,
                )

            # Handle as list or single object
            elif isinstance(data, list):
                messages = data
            else:
                messages = [data]
        else:
            # JSONL format
            with open(session_file) as f:
                messages = [json.loads(line) for line in f if line.strip()]

        if not messages:
            return None

        # Find session metadata from first message (new JSONL format)
        first_msg = messages[0]
        session_id = None
        cwd = None
        timestamp_str = None

        if first_msg.get("type") == "session_meta":
            payload = first_msg.get("payload", {})
            session_id = payload.get("id")
            cwd = payload.get("cwd")
            timestamp_str = payload.get("timestamp") or first_msg.get("timestamp")
        else:
            timestamp_str = first_msg.get("timestamp")

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

        # Count messages
        user_count = sum(
            1
            for m in messages
            if m.get("type") == "response_item"
            and m.get("payload", {}).get("role") == "user"
        )
        assistant_count = sum(
            1
            for m in messages
            if m.get("type") == "response_item"
            and m.get("payload", {}).get("role") == "assistant"
        )

        return Session(
            id=session_id or session_file.stem,
            agent=AgentType.CODEX,
            started_at=started_at,
            ended_at=ended_at,
            repo=extract_repo_from_path(cwd),
            turn_count=len(messages),
            user_message_count=user_count,
            assistant_message_count=assistant_count,
            tools_used=extract_tool_uses_codex(messages),
            user_prompts=extract_user_prompts_codex(messages),
        )

    except Exception:
        return None


def parse_codex_sessions(
    sessions_dir: Path | None = None,
    year: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Iterator[Session]:
    """Parse all Codex sessions within the time window.

    Args:
        sessions_dir: Directory containing Codex sessions (default: ~/.codex/sessions)
        year: Filter to specific year
        start_date: Filter sessions starting after this date
        end_date: Filter sessions starting before this date

    Yields:
        Session objects for each valid session
    """
    if sessions_dir is None:
        sessions_dir = get_codex_sessions_dir()

    if not sessions_dir.exists():
        return

    # Set date filters
    if year and not start_date:
        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
    if year and not end_date:
        end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    # Find all session files (.json and .jsonl)
    session_files = list(sessions_dir.rglob("*.json")) + list(sessions_dir.rglob("*.jsonl"))

    for session_file in session_files:
        session = parse_codex_session_file(session_file)

        if session is None:
            continue

        # Apply date filters
        if start_date and session.started_at < start_date:
            continue
        if end_date and session.started_at > end_date:
            continue

        yield session
