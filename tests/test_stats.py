"""Tests for stats aggregation."""

import pytest
from datetime import datetime, timezone

from code_wrapped.parsers.base import AgentType, Session
from code_wrapped.stats import compute_streaks, aggregate_stats


class TestComputeStreaks:
    """Tests for streak computation."""

    def test_empty_sessions(self):
        assert compute_streaks({}) == (0, 0, 0)

    def test_single_day(self):
        result = compute_streaks({"2025-06-15": 5})
        assert result == (1, 1, 1)  # longest=1, current=1, active=1

    def test_consecutive_days(self):
        sessions = {
            "2025-06-15": 2,
            "2025-06-16": 3,
            "2025-06-17": 1,
        }
        result = compute_streaks(sessions)
        assert result == (3, 3, 3)  # 3-day streak

    def test_gap_breaks_streak(self):
        """A gap between days should break the streak."""
        sessions = {
            "2025-06-15": 2,
            "2025-06-16": 3,
            # Gap on 17th
            "2025-06-18": 1,
            "2025-06-19": 2,
        }
        result = compute_streaks(sessions)
        longest, current, active = result
        assert longest == 2  # Either 15-16 or 18-19
        assert current == 2  # 18-19 is most recent
        assert active == 4

    def test_zero_count_days_ignored(self):
        """Days with 0 sessions should not count."""
        sessions = {
            "2025-06-15": 2,
            "2025-06-16": 0,  # Should be ignored
            "2025-06-17": 1,
        }
        result = compute_streaks(sessions)
        longest, current, active = result
        assert active == 2  # Only 2 active days


class TestAggregateStats:
    """Tests for stats aggregation."""

    def test_empty_sessions(self):
        stats = aggregate_stats([], 2025)
        assert stats.total_sessions == 0
        assert stats.total_turns == 0

    def test_single_session(self):
        session = Session(
            id="test-1",
            agent=AgentType.CLAUDE,
            started_at=datetime(2025, 6, 15, 14, 0, tzinfo=timezone.utc),
            turn_count=10,
            user_message_count=5,
            assistant_message_count=5,
            repo="my-project",
            tools_used={"Bash": 3, "Edit": 2},
        )

        stats = aggregate_stats([session], 2025)

        assert stats.total_sessions == 1
        assert stats.total_turns == 10
        assert stats.all_repos["my-project"] == 1
        assert stats.all_tools["Bash"] == 3
        assert stats.agent_stats[AgentType.CLAUDE].session_count == 1

    def test_multiple_agents(self):
        sessions = [
            Session(
                id="claude-1",
                agent=AgentType.CLAUDE,
                started_at=datetime(2025, 6, 15, 14, 0, tzinfo=timezone.utc),
                turn_count=10,
            ),
            Session(
                id="codex-1",
                agent=AgentType.CODEX,
                started_at=datetime(2025, 6, 15, 15, 0, tzinfo=timezone.utc),
                turn_count=20,
            ),
        ]

        stats = aggregate_stats(sessions, 2025)

        assert stats.total_sessions == 2
        assert stats.total_turns == 30
        assert stats.agent_stats[AgentType.CLAUDE].session_count == 1
        assert stats.agent_stats[AgentType.CODEX].session_count == 1

    def test_hour_distribution(self):
        sessions = [
            Session(
                id="morning",
                agent=AgentType.CLAUDE,
                started_at=datetime(2025, 6, 15, 9, 0, tzinfo=timezone.utc),
                turn_count=5,
            ),
            Session(
                id="evening",
                agent=AgentType.CLAUDE,
                started_at=datetime(2025, 6, 15, 21, 0, tzinfo=timezone.utc),
                turn_count=5,
            ),
            Session(
                id="evening2",
                agent=AgentType.CLAUDE,
                started_at=datetime(2025, 6, 16, 21, 0, tzinfo=timezone.utc),
                turn_count=5,
            ),
        ]

        stats = aggregate_stats(sessions, 2025)

        assert stats.hours_distribution[9] == 1
        assert stats.hours_distribution[21] == 2
        assert stats.peak_hour == 21
