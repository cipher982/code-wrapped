"""Stats aggregation and analysis for Code Wrapped."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .parsers.base import AgentType, Session

# Enrichment imports - deferred to avoid circular imports
_enrichment_loaded = False
_enrichment_modules: dict = {}


@dataclass
class AgentStats:
    """Statistics for a single agent."""

    agent: AgentType
    session_count: int = 0
    turn_count: int = 0
    token_count: int = 0
    user_message_count: int = 0
    assistant_message_count: int = 0
    total_duration_minutes: float = 0.0

    # Distributions
    repos: dict[str, int] = field(default_factory=dict)
    tools_used: dict[str, int] = field(default_factory=dict)
    hours_distribution: dict[int, int] = field(default_factory=dict)
    daily_sessions: dict[str, int] = field(default_factory=dict)

    # Records
    longest_session_minutes: float = 0.0
    longest_session_id: str | None = None
    most_turns_session: int = 0
    most_turns_session_id: str | None = None

    @property
    def avg_turns_per_session(self) -> float:
        if self.session_count == 0:
            return 0.0
        return self.turn_count / self.session_count

    @property
    def avg_duration_minutes(self) -> float:
        if self.session_count == 0:
            return 0.0
        return self.total_duration_minutes / self.session_count


@dataclass
class WrappedStats:
    """Aggregated statistics for Code Wrapped."""

    year: int
    generated_at: datetime

    # Per-agent stats
    agent_stats: dict[AgentType, AgentStats] = field(default_factory=dict)

    # Aggregate stats
    total_sessions: int = 0
    total_turns: int = 0
    total_tokens: int = 0
    total_duration_minutes: float = 0.0

    # Global distributions
    all_repos: dict[str, int] = field(default_factory=dict)
    all_tools: dict[str, int] = field(default_factory=dict)
    hours_distribution: dict[int, int] = field(default_factory=dict)
    daily_sessions: dict[str, int] = field(default_factory=dict)

    # Streaks
    longest_streak_days: int = 0
    current_streak_days: int = 0
    active_days: int = 0

    # Records
    most_active_day: str | None = None
    most_active_day_sessions: int = 0
    peak_hour: int = 0

    # All sessions for detailed analysis
    sessions: list[Session] = field(default_factory=list)

    # Errors for "Error of the Year"
    all_errors: list[tuple[str, str]] = field(default_factory=list)  # (session_id, error)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "year": self.year,
            "generated_at": self.generated_at.isoformat(),
            "summary": {
                "total_sessions": self.total_sessions,
                "total_turns": self.total_turns,
                "total_tokens": self.total_tokens,
                "total_duration_hours": round(self.total_duration_minutes / 60, 1),
                "active_days": self.active_days,
                "longest_streak_days": self.longest_streak_days,
                "current_streak_days": self.current_streak_days,
            },
            "agents": {
                agent.value: {
                    "sessions": stats.session_count,
                    "turns": stats.turn_count,
                    "tokens": stats.token_count,
                    "avg_turns_per_session": round(stats.avg_turns_per_session, 1),
                    "avg_duration_minutes": round(stats.avg_duration_minutes, 1),
                    "top_repos": dict(
                        sorted(stats.repos.items(), key=lambda x: x[1], reverse=True)[:5]
                    ),
                    "top_tools": dict(
                        sorted(stats.tools_used.items(), key=lambda x: x[1], reverse=True)[:10]
                    ),
                }
                for agent, stats in self.agent_stats.items()
            },
            "distributions": {
                "by_hour": dict(sorted(self.hours_distribution.items())),
                "by_day": dict(sorted(self.daily_sessions.items())),
                "by_repo": dict(
                    sorted(self.all_repos.items(), key=lambda x: x[1], reverse=True)[:10]
                ),
                "by_tool": dict(
                    sorted(self.all_tools.items(), key=lambda x: x[1], reverse=True)[:15]
                ),
            },
            "records": {
                "most_active_day": self.most_active_day,
                "most_active_day_sessions": self.most_active_day_sessions,
                "peak_hour": self.peak_hour,
            },
        }

        # Add enrichment data if sessions available
        if self.sessions:
            result["enrichment"] = self._compute_enrichment()

        return result

    def _compute_enrichment(self) -> dict[str, Any]:
        """Compute enrichment data for JSON output."""
        # Lazy import to avoid circular dependencies
        from .enrichment import (
            compute_archetype_profile,
            compute_fingerprint,
            detect_awards,
            get_dominant_vibe,
            get_most_active_day_award,
            get_peak_hour_award,
            get_top_topics,
        )

        enrichment: dict[str, Any] = {}

        # Topics
        top_topics = get_top_topics(self.sessions, limit=5)
        if top_topics:
            enrichment["topics"] = [
                {"name": name, "count": count, "percentage": round(pct, 1)}
                for name, count, pct in top_topics
            ]

        # Vibe
        dominant_vibe = get_dominant_vibe(self.sessions)
        if dominant_vibe:
            name, emoji, pct = dominant_vibe
            enrichment["vibe"] = {
                "name": name,
                "emoji": emoji,
                "percentage": round(pct, 1),
            }

        # Archetype
        profile = compute_archetype_profile(self.sessions)
        if profile:
            enrichment["archetype"] = {
                "primary": {
                    "name": profile.primary.display_name,
                    "emoji": profile.primary.emoji,
                    "percentage": round(profile.primary.percentage, 1),
                    "description": profile.primary.description,
                },
                "all": [
                    {
                        "name": s.display_name,
                        "emoji": s.emoji,
                        "percentage": round(s.percentage, 1),
                    }
                    for s in profile.all_scores
                ],
            }

        # Fingerprint
        fingerprint = compute_fingerprint(self.sessions)
        if fingerprint:
            enrichment["fingerprint"] = {
                "personality": fingerprint.personality,
                "description": fingerprint.personality_description,
                "top_tools": [
                    {"name": t.name, "count": t.count, "percentage": round(t.percentage, 1)}
                    for t in fingerprint.top_tools[:10]
                ],
            }

        # Awards
        awards = detect_awards(self)
        active_day = get_most_active_day_award(self)
        if active_day:
            awards.append(active_day)
        peak_hour = get_peak_hour_award(self)
        if peak_hour:
            awards.append(peak_hour)

        if awards:
            enrichment["awards"] = [
                {
                    "id": a.id,
                    "name": a.name,
                    "emoji": a.emoji,
                    "description": a.description,
                    "detail": a.detail,
                }
                for a in awards
            ]

        return enrichment


def compute_streaks(daily_sessions: dict[str, int]) -> tuple[int, int, int]:
    """Compute streak statistics from daily session counts.

    Correctly handles gaps between active days.

    Returns:
        (longest_streak, current_streak, active_days)
    """
    if not daily_sessions:
        return 0, 0, 0

    from datetime import datetime, timedelta

    # Get all dates with sessions
    active_dates = sorted([d for d, count in daily_sessions.items() if count > 0])
    active_days = len(active_dates)

    if not active_dates:
        return 0, 0, 0

    # Parse dates
    date_objects = [datetime.strptime(d, "%Y-%m-%d").date() for d in active_dates]

    # Compute longest streak by checking consecutive days
    longest_streak = 1
    temp_streak = 1

    for i in range(1, len(date_objects)):
        if (date_objects[i] - date_objects[i - 1]).days == 1:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1

    # Current streak (from most recent active day backwards)
    current_streak = 1
    for i in range(len(date_objects) - 1, 0, -1):
        if (date_objects[i] - date_objects[i - 1]).days == 1:
            current_streak += 1
        else:
            break

    return longest_streak, current_streak, active_days


def aggregate_stats(sessions: list[Session], year: int) -> WrappedStats:
    """Aggregate statistics from all sessions.

    Args:
        sessions: List of Session objects from all agents
        year: The year being analyzed

    Returns:
        WrappedStats with all computed statistics
    """
    stats = WrappedStats(
        year=year,
        generated_at=datetime.now(),
        sessions=sessions,
    )

    # Initialize per-agent stats
    for agent in AgentType:
        stats.agent_stats[agent] = AgentStats(agent=agent)

    # Process each session
    for session in sessions:
        agent_stats = stats.agent_stats[session.agent]

        # Counts
        agent_stats.session_count += 1
        agent_stats.turn_count += session.turn_count
        agent_stats.user_message_count += session.user_message_count
        agent_stats.assistant_message_count += session.assistant_message_count
        agent_stats.total_duration_minutes += session.duration_minutes

        if session.token_count:
            agent_stats.token_count += session.token_count

        # Repo tracking
        if session.repo:
            agent_stats.repos[session.repo] = agent_stats.repos.get(session.repo, 0) + 1
            stats.all_repos[session.repo] = stats.all_repos.get(session.repo, 0) + 1

        # Tool tracking
        for tool, count in session.tools_used.items():
            agent_stats.tools_used[tool] = agent_stats.tools_used.get(tool, 0) + count
            stats.all_tools[tool] = stats.all_tools.get(tool, 0) + count

        # Hour distribution
        hour = session.hour_of_day
        agent_stats.hours_distribution[hour] = agent_stats.hours_distribution.get(hour, 0) + 1
        stats.hours_distribution[hour] = stats.hours_distribution.get(hour, 0) + 1

        # Daily sessions
        date = session.date_str
        agent_stats.daily_sessions[date] = agent_stats.daily_sessions.get(date, 0) + 1
        stats.daily_sessions[date] = stats.daily_sessions.get(date, 0) + 1

        # Records
        if session.duration_minutes > agent_stats.longest_session_minutes:
            agent_stats.longest_session_minutes = session.duration_minutes
            agent_stats.longest_session_id = session.id

        if session.turn_count > agent_stats.most_turns_session:
            agent_stats.most_turns_session = session.turn_count
            agent_stats.most_turns_session_id = session.id

        # Errors
        for error in session.errors:
            stats.all_errors.append((session.id, error))

    # Compute totals
    for agent_stats in stats.agent_stats.values():
        stats.total_sessions += agent_stats.session_count
        stats.total_turns += agent_stats.turn_count
        stats.total_tokens += agent_stats.token_count
        stats.total_duration_minutes += agent_stats.total_duration_minutes

    # Compute streaks
    stats.longest_streak_days, stats.current_streak_days, stats.active_days = compute_streaks(
        stats.daily_sessions
    )

    # Find most active day
    if stats.daily_sessions:
        most_active = max(stats.daily_sessions.items(), key=lambda x: x[1])
        stats.most_active_day = most_active[0]
        stats.most_active_day_sessions = most_active[1]

    # Find peak hour
    if stats.hours_distribution:
        stats.peak_hour = max(stats.hours_distribution.items(), key=lambda x: x[1])[0]

    return stats
