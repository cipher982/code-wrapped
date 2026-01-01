#!/usr/bin/env python3
"""Debug Claude parser differences."""

import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add cipher982 scripts to path
sys.path.insert(0, str(Path.home() / "git" / "cipher982" / "scripts"))

from parse_claude import parse_claude_sessions as parse_claude_982

# Import code-wrapped parsers
from code_wrapped.parsers.claude import parse_session_file

def debug_parsing():
    """Debug why code-wrapped finds fewer sessions."""

    # Define 7-day window
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    # Paths
    claude_dir = Path.home() / ".claude" / "projects"

    # Find all session files
    session_files = list(claude_dir.rglob("*.jsonl"))
    print(f"Total session files found: {len(session_files)}")
    print()

    # Test parsing with code-wrapped
    parsed_count = 0
    failed_count = 0
    out_of_range_count = 0
    no_timestamp_count = 0

    for session_file in session_files[:100]:  # Sample first 100
        session = parse_session_file(session_file)

        if session is None:
            failed_count += 1
            # Try to see why it failed
            try:
                with open(session_file) as f:
                    lines = f.readlines()
                if not lines:
                    continue

                # Check if we can find timestamp
                has_timestamp = False
                for line in lines[:10]:
                    try:
                        obj = json.loads(line)
                        if obj.get("timestamp"):
                            has_timestamp = True
                            break
                    except:
                        pass

                if not has_timestamp:
                    no_timestamp_count += 1
            except:
                pass
        else:
            # Check if in range
            if start_date <= session.started_at <= end_date:
                parsed_count += 1
                if parsed_count <= 3:
                    print(f"Sample parsed session:")
                    print(f"  File: {session_file.name}")
                    print(f"  ID: {session.id}")
                    print(f"  Repo: {session.repo}")
                    print(f"  Started: {session.started_at}")
                    print(f"  Turns: {session.turn_count}")
                    print()
            else:
                out_of_range_count += 1

    print(f"\nResults (first 100 files):")
    print(f"  Parsed successfully: {parsed_count + out_of_range_count}")
    print(f"  In date range: {parsed_count}")
    print(f"  Out of range: {out_of_range_count}")
    print(f"  Failed to parse: {failed_count}")
    print(f"  Missing timestamp: {no_timestamp_count}")

    # Now check what cipher982 counts
    print("\n" + "=" * 80)
    print("Checking cipher982 turn counting...")
    print("=" * 80)

    # Look at a sample session and count turns both ways
    sample_file = None
    for f in session_files:
        session = parse_session_file(f)
        if session and start_date <= session.started_at <= end_date:
            sample_file = f
            break

    if sample_file:
        with open(sample_file) as f:
            lines = f.readlines()

        # Count messages vs lines
        messages = []
        for line in lines:
            try:
                messages.append(json.loads(line))
            except:
                pass

        print(f"\nSample file: {sample_file.name}")
        print(f"  Total lines: {len(lines)}")
        print(f"  Valid JSON messages: {len(messages)}")
        print(f"  code-wrapped counts: {len(messages)} (valid messages)")
        print(f"  cipher982 counts: {len(lines)} (all lines)")
        print()
        print("  cipher982 uses len(lines) as turn_count")
        print("  code-wrapped uses len(messages) as turn_count")
        print()
        print("  This explains the turn count discrepancy!")

if __name__ == "__main__":
    debug_parsing()
