#!/usr/bin/env python3
"""Debug the exact exception being thrown."""

import json
import traceback
from pathlib import Path
from code_wrapped.parsers.base import (
    AgentType,
    Session,
    extract_repo_from_path,
    parse_iso_timestamp,
)
from code_wrapped.parsers.claude import (
    find_field_in_session,
    extract_token_count,
    extract_tool_uses,
    extract_user_prompts,
    extract_errors,
)

def debug_parse_with_exception(file_path):
    """Parse and catch the exception."""
    print(f"Parsing: {file_path}")
    print("=" * 80)

    try:
        with open(file_path) as f:
            lines = f.readlines()

        if not lines:
            print("No lines!")
            return

        # Parse all messages
        messages = []
        for line in lines:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not messages:
            print("No messages!")
            return

        # Extract session metadata
        cwd = find_field_in_session(lines, "cwd")
        session_id = find_field_in_session(lines, "sessionId")
        timestamp_str = find_field_in_session(lines, "timestamp")
        branch = find_field_in_session(lines, "gitBranch")

        if not timestamp_str:
            print("No timestamp!")
            return

        started_at = parse_iso_timestamp(timestamp_str)
        if not started_at:
            print("Failed to parse timestamp!")
            return

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

        print("Creating Session object...")
        session = Session(
            id=session_id or file_path.stem,
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

        print(f"SUCCESS! Created session: {session.id}")
        print(f"  Repo: {session.repo}")
        print(f"  Turns: {session.turn_count}")
        print(f"  Tokens: {session.token_count}")

    except Exception as e:
        print(f"EXCEPTION CAUGHT: {type(e).__name__}: {e}")
        print()
        print("Full traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    file_path = Path.home() / ".claude" / "projects" / "-Users-davidrose-git-zerg" / "agent-a062a34.jsonl"
    debug_parse_with_exception(file_path)
