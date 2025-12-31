"""Parse Gemini CLI session data from ~/.gemini/tmp/*/logs.json"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .base import AgentType, Session, parse_iso_timestamp, sanitize_prompt


def get_gemini_sessions_dir() -> Path:
    """Return the default Gemini sessions directory."""
    return Path.home() / ".gemini" / "tmp"


def parse_gemini_sessions(
    sessions_dir: Path | None = None,
    year: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Iterator[Session]:
    """Parse Gemini CLI sessions from logs.json files.

    Args:
        sessions_dir: Directory containing Gemini sessions (default: ~/.gemini/tmp)
        year: Filter to specific year
        start_date: Filter sessions starting after this date
        end_date: Filter sessions starting before this date

    Yields:
        Session objects for each valid session
    """
    if sessions_dir is None:
        sessions_dir = get_gemini_sessions_dir()

    if not sessions_dir.exists():
        return

    # Set date filters
    if year and not start_date:
        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
    if year and not end_date:
        end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    # Find all logs.json files
    logs_files = list(sessions_dir.rglob("logs.json"))

    # Group messages by session
    sessions_data: dict[str, dict] = defaultdict(
        lambda: {
            "messages": [],
            "user_prompts": [],
            "first_timestamp": None,
            "last_timestamp": None,
        }
    )

    for logs_file in logs_files:
        try:
            with open(logs_file) as f:
                messages = json.load(f)

            for msg in messages:
                session_id = msg.get("sessionId")
                timestamp_str = msg.get("timestamp")

                if not session_id or not timestamp_str:
                    continue

                timestamp = parse_iso_timestamp(timestamp_str)
                if not timestamp:
                    continue

                # Apply date filters at message level
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue

                session = sessions_data[session_id]
                session["messages"].append(msg)

                # Track timestamps
                if session["first_timestamp"] is None or timestamp < session["first_timestamp"]:
                    session["first_timestamp"] = timestamp
                if session["last_timestamp"] is None or timestamp > session["last_timestamp"]:
                    session["last_timestamp"] = timestamp

                # Extract user prompts
                if msg.get("type") == "user":
                    content = msg.get("content", "")
                    if content:
                        session["user_prompts"].append(sanitize_prompt(content))

        except (json.JSONDecodeError, Exception):
            continue

    # Convert to Session objects
    for session_id, data in sessions_data.items():
        if not data["messages"] or not data["first_timestamp"]:
            continue

        user_count = sum(1 for m in data["messages"] if m.get("type") == "user")
        assistant_count = sum(1 for m in data["messages"] if m.get("type") == "model")

        yield Session(
            id=session_id,
            agent=AgentType.GEMINI,
            started_at=data["first_timestamp"],
            ended_at=data["last_timestamp"],
            turn_count=len(data["messages"]),
            user_message_count=user_count,
            assistant_message_count=assistant_count,
            user_prompts=data["user_prompts"],
        )
