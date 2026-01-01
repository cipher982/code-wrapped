#!/usr/bin/env python3
"""Debug why a specific file fails to parse."""

import json
from pathlib import Path

def debug_file_parsing(file_path):
    """Debug why a file fails to parse."""
    print(f"Debugging: {file_path}")
    print("=" * 80)

    with open(file_path) as f:
        lines = f.readlines()

    print(f"Total lines: {len(lines)}")
    print()

    # Parse all messages
    messages = []
    for i, line in enumerate(lines):
        try:
            obj = json.loads(line)
            messages.append(obj)
        except json.JSONDecodeError as e:
            print(f"Line {i}: JSON decode error: {e}")

    print(f"Valid messages: {len(messages)}")
    print()

    if not messages:
        print("No valid messages found!")
        return

    # Check first message
    first_msg = messages[0]
    print("First message:")
    print(f"  Type: {first_msg.get('type')}")
    print(f"  Has timestamp: {'timestamp' in first_msg}")
    print(f"  Timestamp: {first_msg.get('timestamp')}")
    print(f"  Has cwd: {'cwd' in first_msg}")
    print(f"  CWD: {first_msg.get('cwd')}")
    print(f"  Has sessionId: {'sessionId' in first_msg}")
    print(f"  Session ID: {first_msg.get('sessionId')}")
    print(f"  Has message key: {'message' in first_msg}")
    print()

    # Now try to parse with code-wrapped logic
    from code_wrapped.parsers.claude import parse_session_file

    session = parse_session_file(Path(file_path))
    print(f"code-wrapped result: {session}")
    print()

    if session is None:
        print("FAILURE - Let's trace through the code...")
        print()

        # Manually trace through the parse_session_file logic
        from code_wrapped.parsers.claude import find_field_in_session, parse_iso_timestamp

        # Extract metadata using find_field_in_session
        cwd = find_field_in_session(lines, "cwd")
        session_id = find_field_in_session(lines, "sessionId")
        timestamp_str = find_field_in_session(lines, "timestamp")
        branch = find_field_in_session(lines, "gitBranch")

        print(f"find_field_in_session results:")
        print(f"  cwd: {cwd}")
        print(f"  sessionId: {session_id}")
        print(f"  timestamp: {timestamp_str}")
        print(f"  branch: {branch}")
        print()

        if not timestamp_str:
            print("ERROR: No timestamp found!")
            return

        started_at = parse_iso_timestamp(timestamp_str)
        print(f"Parsed timestamp: {started_at}")
        print()

        if not started_at:
            print("ERROR: Failed to parse timestamp!")
            return

        # Find end timestamp
        ended_at = None
        for msg in reversed(messages):
            ts = msg.get("timestamp")
            if ts:
                ended_at = parse_iso_timestamp(ts)
                break

        print(f"End timestamp: {ended_at}")
        print()

        # Count messages by type
        user_count = sum(1 for m in messages if m.get("type") == "user")
        assistant_count = sum(1 for m in messages if m.get("type") == "assistant")

        print(f"Message counts:")
        print(f"  Total: {len(messages)}")
        print(f"  User: {user_count}")
        print(f"  Assistant: {assistant_count}")
        print()

        # Check token extraction
        from code_wrapped.parsers.claude import extract_token_count
        tokens = extract_token_count(messages)
        print(f"Tokens: {tokens}")
        print()

        # Check tool extraction
        from code_wrapped.parsers.claude import extract_tool_uses
        tools = extract_tool_uses(messages)
        print(f"Tools: {tools}")
        print()

        # Should have all the data to create a session
        print("We have all the data needed to create a Session object!")
        print("The parser must be catching an exception...")


if __name__ == "__main__":
    file_path = Path.home() / ".claude" / "projects" / "-Users-davidrose-git-zerg" / "agent-a062a34.jsonl"
    debug_file_parsing(file_path)
