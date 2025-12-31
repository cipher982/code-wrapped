"""Parse Cursor IDE session data from SQLite database."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .base import AgentType, Session


def get_cursor_db_path() -> Path:
    """Return the default Cursor database path."""
    return Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"


def parse_cursor_sessions(
    db_path: Path | None = None,
    year: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Iterator[Session]:
    """Parse Cursor IDE composer sessions from global storage database.

    Args:
        db_path: Path to state.vscdb (defaults to standard location)
        year: Filter to specific year
        start_date: Filter sessions starting after this date
        end_date: Filter sessions starting before this date

    Yields:
        Session objects for each valid session
    """
    if db_path is None:
        db_path = get_cursor_db_path()

    if not db_path.exists():
        return

    # Set date filters
    if year and not start_date:
        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
    if year and not end_date:
        end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # First pass: count messages (bubbles) per composer
        cursor.execute("SELECT key FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'")
        message_counts: dict[str, int] = {}
        for (key,) in cursor.fetchall():
            parts = key.split(":")
            if len(parts) >= 2:
                composer_id = parts[1]
                message_counts[composer_id] = message_counts.get(composer_id, 0) + 1

        # Second pass: get composer metadata
        cursor.execute("SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'")

        for key, value_blob in cursor.fetchall():
            try:
                if not value_blob:
                    continue

                composer_id = key.split(":")[1]
                data = json.loads(value_blob)

                created_at = data.get("createdAt")
                if not created_at:
                    continue

                timestamp = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)

                # Apply date filters
                if start_date and timestamp < start_date:
                    continue
                if end_date and timestamp > end_date:
                    continue

                # Get actual message count from bubbles
                turn_count = message_counts.get(composer_id, 1)
                mode = data.get("unifiedMode", "unknown")

                yield Session(
                    id=composer_id,
                    agent=AgentType.CURSOR,
                    started_at=timestamp,
                    turn_count=turn_count,
                    user_message_count=turn_count // 2,  # Estimate
                    assistant_message_count=turn_count // 2,
                    # Cursor doesn't track per-repo like Claude/Codex
                    repo=None,
                    # Store mode in tools_used for Cursor-specific tracking
                    tools_used={"cursor_mode": 1} if mode and mode != "unknown" else {},
                )

            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        conn.close()

    except sqlite3.Error:
        return
