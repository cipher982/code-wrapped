#!/usr/bin/env python3
"""Compare cipher982 and code-wrapped parsing implementations."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add cipher982 scripts to path
sys.path.insert(0, str(Path.home() / "git" / "cipher982" / "scripts"))

# Import cipher982 parsers
from parse_claude import parse_claude_sessions as parse_claude_982
from parse_codex import parse_codex_sessions as parse_codex_982

# Import code-wrapped parsers
from code_wrapped.parsers import parse_claude_sessions, parse_codex_sessions

def compare_implementations():
    """Compare both implementations for 7-day window."""

    # Define 7-day window
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)

    # Paths
    claude_dir = Path.home() / ".claude" / "projects"
    codex_dir = Path.home() / ".codex" / "sessions"

    print("=" * 80)
    print("COMPARISON: cipher982 vs code-wrapped (7-day window)")
    print("=" * 80)
    print(f"Start: {start_date.date()}")
    print(f"End:   {end_date.date()}")
    print()

    # Test Claude parser
    print("CLAUDE SESSIONS")
    print("-" * 80)

    # cipher982 implementation
    cipher982_claude = parse_claude_982(claude_dir, days_back=7)
    print(f"cipher982:")
    print(f"  Sessions (7d): {cipher982_claude['sessions_7d']}")
    print(f"  Turns (7d):    {cipher982_claude['turns_7d']}")
    print(f"  Top repos:     {cipher982_claude['repos'][:3]}")

    # code-wrapped implementation
    wrapped_sessions = list(parse_claude_sessions(
        claude_dir,
        start_date=start_date,
        end_date=end_date
    ))
    wrapped_turns = sum(s.turn_count for s in wrapped_sessions)

    # Count by repo
    repo_counts = {}
    for session in wrapped_sessions:
        if session.repo:
            repo_counts[session.repo] = repo_counts.get(session.repo, 0) + 1
    top_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    print(f"code-wrapped:")
    print(f"  Sessions (7d): {len(wrapped_sessions)}")
    print(f"  Turns (7d):    {wrapped_turns}")
    print(f"  Top repos:     {[(r, c) for r, c in top_repos]}")

    # Compare
    session_diff = len(wrapped_sessions) - cipher982_claude['sessions_7d']
    turn_diff = wrapped_turns - cipher982_claude['turns_7d']
    session_diff_pct = (session_diff / cipher982_claude['sessions_7d'] * 100) if cipher982_claude['sessions_7d'] else 0
    turn_diff_pct = (turn_diff / cipher982_claude['turns_7d'] * 100) if cipher982_claude['turns_7d'] else 0

    print(f"\nDifference:")
    print(f"  Sessions: {session_diff:+d} ({session_diff_pct:+.1f}%)")
    print(f"  Turns:    {turn_diff:+d} ({turn_diff_pct:+.1f}%)")

    print()
    print("=" * 80)
    print()

    # Test Codex parser
    print("CODEX SESSIONS")
    print("-" * 80)

    # cipher982 implementation
    cipher982_codex = parse_codex_982(codex_dir, days_back=7)
    print(f"cipher982:")
    print(f"  Sessions (7d): {cipher982_codex['sessions_7d']}")
    print(f"  Turns (7d):    {cipher982_codex['turns_7d']}")
    print(f"  Top repos:     {cipher982_codex['repos'][:3]}")

    # code-wrapped implementation
    wrapped_sessions = list(parse_codex_sessions(
        codex_dir,
        start_date=start_date,
        end_date=end_date
    ))
    wrapped_turns = sum(s.turn_count for s in wrapped_sessions)

    # Count by repo
    repo_counts = {}
    for session in wrapped_sessions:
        if session.repo:
            repo_counts[session.repo] = repo_counts.get(session.repo, 0) + 1
    top_repos = sorted(repo_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    print(f"code-wrapped:")
    print(f"  Sessions (7d): {len(wrapped_sessions)}")
    print(f"  Turns (7d):    {wrapped_turns}")
    print(f"  Top repos:     {[(r, c) for r, c in top_repos]}")

    # Compare
    session_diff = len(wrapped_sessions) - cipher982_codex['sessions_7d']
    turn_diff = wrapped_turns - cipher982_codex['turns_7d']
    session_diff_pct = (session_diff / cipher982_codex['sessions_7d'] * 100) if cipher982_codex['sessions_7d'] else 0
    turn_diff_pct = (turn_diff / cipher982_codex['turns_7d'] * 100) if cipher982_codex['turns_7d'] else 0

    print(f"\nDifference:")
    print(f"  Sessions: {session_diff:+d} ({session_diff_pct:+.1f}%)")
    print(f"  Turns:    {turn_diff:+d} ({turn_diff_pct:+.1f}%)")

    print()
    print("=" * 80)

if __name__ == "__main__":
    compare_implementations()
