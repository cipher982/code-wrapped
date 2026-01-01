#!/usr/bin/env python3
"""Debug session counting differences - why are we missing 181 sessions?"""

import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# Add cipher982 scripts to path
sys.path.insert(0, str(Path.home() / "git" / "cipher982" / "scripts"))

from parse_claude import parse_claude_sessions as parse_claude_982, find_field_in_session

# Import code-wrapped parsers
from code_wrapped.parsers.claude import parse_session_file

def debug_session_counting():
    """Debug why we're finding different session counts."""

    # Define 7-day window
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    # Paths
    claude_dir = Path.home() / ".claude" / "projects"

    # Find all session files
    session_files = list(claude_dir.rglob("*.jsonl"))
    print(f"Total .jsonl files found: {len(session_files)}")
    print()

    # Parse with both implementations
    wrapped_parsed = 0
    wrapped_in_range = 0
    wrapped_failed = 0

    wrapped_sessions = []

    for session_file in session_files:
        session = parse_session_file(session_file)

        if session is None:
            wrapped_failed += 1
        else:
            wrapped_parsed += 1
            if start_date <= session.started_at <= end_date:
                wrapped_in_range += 1
                wrapped_sessions.append((session_file, session))

    print("code-wrapped results:")
    print(f"  Total files: {len(session_files)}")
    print(f"  Parsed: {wrapped_parsed}")
    print(f"  Failed: {wrapped_failed}")
    print(f"  In 7d range: {wrapped_in_range}")
    print()

    # Now manually parse like cipher982 does
    cipher982_in_range = 0
    cipher982_sessions = []

    for session_file in session_files:
        try:
            with open(session_file, 'r') as f:
                lines = f.readlines()

            if not lines:
                continue

            # Find timestamp like cipher982 does
            timestamp_str = find_field_in_session(lines, "timestamp")

            if not timestamp_str:
                continue

            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            if timestamp >= start_date and timestamp <= end_date:
                cipher982_in_range += 1
                cipher982_sessions.append(session_file)

        except Exception:
            continue

    print("cipher982 logic results:")
    print(f"  In 7d range: {cipher982_in_range}")
    print()

    # Find the diff
    print("=" * 80)
    print(f"DISCREPANCY: cipher982 finds {cipher982_in_range - wrapped_in_range} more sessions")
    print("=" * 80)
    print()

    # Find which files cipher982 finds but code-wrapped doesn't
    wrapped_files = {f for f, s in wrapped_sessions}
    cipher982_files = set(cipher982_sessions)

    missing_in_wrapped = cipher982_files - wrapped_files
    print(f"Files cipher982 finds but code-wrapped doesn't: {len(missing_in_wrapped)}")

    # Investigate a few
    for i, session_file in enumerate(list(missing_in_wrapped)[:5]):
        print(f"\nMissing file #{i+1}: {session_file.name}")

        # Try to parse with code-wrapped
        session = parse_session_file(session_file)
        print(f"  code-wrapped result: {session}")

        # Check what cipher982 sees
        with open(session_file) as f:
            lines = f.readlines()

        timestamp_str = find_field_in_session(lines, "timestamp")
        cwd = find_field_in_session(lines, "cwd")
        session_id = find_field_in_session(lines, "sessionId")

        print(f"  Lines: {len(lines)}")
        print(f"  Timestamp: {timestamp_str}")
        print(f"  CWD: {cwd}")
        print(f"  Session ID: {session_id}")

        # Show first few lines
        print(f"  First line preview:")
        for j, line in enumerate(lines[:3]):
            try:
                obj = json.loads(line)
                print(f"    Line {j}: type={obj.get('type')}, timestamp={obj.get('timestamp')[:30] if obj.get('timestamp') else None}")
            except:
                print(f"    Line {j}: [invalid JSON]")

if __name__ == "__main__":
    debug_session_counting()
